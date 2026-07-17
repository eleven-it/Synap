"""
Motor de aprobación comercial de pedidos (separado de ``autorizacion_sistema`` crédito).

Reglas OR: monto, descuento pie/renglón, crédito no autorizado, cliente nuevo.
Routing: supervisores activos del vendedor → gerentes de esos supervisores.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.mysql_pool import get_mysql_pool, mysql_cursor
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none

from ecom.services.alcance_comercial import alcance_viajantes_comercial
from ecom.services.ecom_config_mysql import (
    aprobacion_pedidos_activa,
    umbrales_aprobacion_pedidos,
)
from ecom.services.jerarquia_comercial import (
    _gerente_de_supervisor,
    _supervisores_de_vendedor,
)
from ecom.services.pedido_permisos import puede_ver_todos_pedidos

logger = logging.getLogger(__name__)

ESTADO_NEUTRO = "-"
ESTADO_PENDIENTE = "pendiente"
ESTADO_APROBADO = "aprobado"
ESTADO_RECHAZADO = "rechazado"

ACCION_SOLICITUD = "solicitud"
ACCION_ESCALADO = "escalado"
ACCION_APROBADO = "aprobado"
ACCION_RECHAZADO = "rechazado"

_REGLA_MONTO = "monto"
_REGLA_DESC_PIE = "desc_pie"
_REGLA_DESC_RENGLON = "desc_renglon"
_REGLA_CREDITO = "credito_no_autorizado"
_REGLA_CLIENTE_NUEVO = "cliente_nuevo"


def _ahora() -> datetime:
    return datetime.now()


def _cod_aprobador_desde_ctx(ctx: Dict[str, Any]) -> Optional[int]:
    return to_int_or_none(
        ctx.get("id_vendedor_usr")
        or ctx.get("CodViajante")
        or ctx.get("cod_viajante")
    )


def _id_aprobador_desde_ctx(ctx: Dict[str, Any]) -> Optional[int]:
    user = ctx.get("user") if isinstance(ctx.get("user"), dict) else {}
    return to_int_or_none(ctx.get("id_usuario") or user.get("id_usuario"))


def _tiene_permiso_aprobar(sess_user: Dict[str, Any]) -> bool:
    if puede_ver_todos_pedidos(sess_user):
        return True
    permisos = sess_user.get("synap_permisos") or sess_user.get("permisos") or []
    if isinstance(permisos, str):
        permisos = [p.strip() for p in permisos.split(",") if p.strip()]
    codigos = {str(p).strip() for p in permisos if p}
    return (
        "ecom.pedidos.aprobar" in codigos
        or "ecom.*" in codigos
        or "*" in codigos
    )


def _max_desc_renglon(items: Sequence[Any], desc_cliente: Any) -> Decimal:
    max_desc = to_decimal_or_none(desc_cliente) or Decimal("0")
    for it in items:
        pct = to_decimal_or_none(getattr(it, "porcentaje_descuento", None))
        if pct is not None and pct > max_desc:
            max_desc = pct
    return max_desc


def _es_cliente_nuevo(cursor, id_cliente: int, cod_mov_actual: Optional[int] = None) -> bool:
    """Cliente sin PED previos confirmados (excluye el movimiento en curso)."""
    sql = """
        SELECT 1 FROM comp_ped
        WHERE TipoComprobante = 'PED'
          AND Codigo = %s
          AND COALESCE(Anulado, 'No') = 'No'
    """
    params: List[Any] = [id_cliente]
    if cod_mov_actual is not None:
        sql += " AND CodigoMovimiento <> %s"
        params.append(cod_mov_actual)
    sql += " LIMIT 1"
    cursor.execute(sql, params)
    return cursor.fetchone() is None


def evaluar_reglas(
    base_empresa: str,
    cart: Any,
    cli: Dict[str, Any],
    *,
    autorizacion_sistema: str,
    cursor=None,
    cod_mov_excluir: Optional[int] = None,
) -> Tuple[bool, List[str]]:
    """
    Evalúa reglas comerciales (OR). Devuelve (requiere_aprobación, reglas_disparadas).
    """
    if not aprobacion_pedidos_activa(base_empresa):
        return False, []

    umbrales = umbrales_aprobacion_pedidos(base_empresa)
    reglas: List[str] = []

    total = to_decimal_or_none(getattr(cart, "total", None)) or Decimal("0")
    umbral_monto = umbrales.get("monto")
    if umbral_monto is not None and total > umbral_monto:
        reglas.append(_REGLA_MONTO)

    desc_pie = to_decimal_or_none(getattr(cart, "descuento_pie_pct", None)) or Decimal("0")
    umbral_pie = umbrales.get("desc_pie")
    if umbral_pie is not None and desc_pie > umbral_pie:
        reglas.append(_REGLA_DESC_PIE)

    raw_items = getattr(cart, "items", None)
    if raw_items is None:
        items: List[Any] = []
    elif hasattr(raw_items, "all"):
        items = list(raw_items.all())
    else:
        items = list(raw_items or [])
    max_renglon = _max_desc_renglon(items, cli.get("descRenglon"))
    umbral_renglon = umbrales.get("desc_renglon")
    if umbral_renglon is not None and max_renglon > umbral_renglon:
        reglas.append(_REGLA_DESC_RENGLON)

    if (autorizacion_sistema or "").strip() == "No Autorizado":
        reglas.append(_REGLA_CREDITO)

    id_cliente = to_int_or_none(getattr(cart, "idcliente", None) or cli.get("Codigo"))
    if id_cliente is not None and cursor is not None:
        if _es_cliente_nuevo(cursor, id_cliente, cod_mov_excluir):
            reglas.append(_REGLA_CLIENTE_NUEVO)

    return bool(reglas), reglas


def _regla_disparo_txt(reglas: Sequence[str]) -> str:
    if not reglas:
        return "-"
    return ",".join(reglas[:5])


def _insertar_evento(
    cursor,
    *,
    cod_mov: int,
    accion: str,
    regla_disparo: str,
    cod_solicita: Optional[int],
    cod_resuelve: Optional[int],
    motivo: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO ecom_aprobacion_evento
            (codigo_movimiento, accion, regla_disparo, cod_solicita, cod_resuelve, motivo, creado_en)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            cod_mov,
            str_or_default(accion, "-"),
            str_or_default(regla_disparo, "-"),
            cod_solicita,
            cod_resuelve,
            str_or_default(motivo, "-"),
            _ahora(),
        ),
    )


def aplicar_estado_inicial_checkout(
    cursor,
    base_empresa: str,
    *,
    cod_mov: int,
    cod_viajante: Optional[int],
    requiere: bool,
    reglas: Sequence[str],
) -> str:
    """
    Tras alta PED: setea ``estado_aprobacion_comercial`` y evento solicitud si aplica.
    """
    if not aprobacion_pedidos_activa(base_empresa):
        return ESTADO_NEUTRO

    estado = ESTADO_PENDIENTE if requiere else ESTADO_NEUTRO
    cursor.execute(
        """
        UPDATE comp_ped
        SET estado_aprobacion_comercial = %s
        WHERE CodigoMovimiento = %s AND TipoComprobante = 'PED'
        """,
        (estado, cod_mov),
    )
    if requiere:
        _insertar_evento(
            cursor,
            cod_mov=cod_mov,
            accion=ACCION_SOLICITUD,
            regla_disparo=_regla_disparo_txt(reglas),
            cod_solicita=to_int_or_none(cod_viajante),
            cod_resuelve=None,
            motivo="Solicitud de aprobación comercial",
        )
    return estado


def _fetch_ped_aprobacion(base_empresa: str, cod_mov: int) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT
            cp.CodigoMovimiento,
            cp.CodViajante,
            TRIM(COALESCE(cp.estado_aprobacion_comercial, '-')) AS estado_aprobacion_comercial,
            cp.Anulado
        FROM comp_ped cp
        WHERE cp.CodigoMovimiento = %s AND cp.TipoComprobante = 'PED'
        LIMIT 1
    """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, (cod_mov,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as exc:
        logger.warning("_fetch_ped_aprobacion (%s, %s): %s", base_empresa, cod_mov, exc)
        return None


def _ultimo_evento_escalado(cursor, cod_mov: int) -> bool:
    cursor.execute(
        """
        SELECT accion FROM ecom_aprobacion_evento
        WHERE codigo_movimiento = %s
        ORDER BY id DESC LIMIT 1
        """,
        (cod_mov,),
    )
    row = cursor.fetchone()
    if not row:
        return False
    accion = row.get("accion") if isinstance(row, dict) else row[0]
    return str(accion or "").strip().lower() == ACCION_ESCALADO


def _routing_aprobadores(cursor, cod_vendedor: int) -> Tuple[List[int], List[int]]:
    """Devuelve la unión de supervisores y gerentes activos habilitados a aprobar."""
    supervisores = _supervisores_de_vendedor(cursor, cod_vendedor)
    gerentes = sorted(
        {
            gerente
            for supervisor in supervisores
            if (gerente := _gerente_de_supervisor(cursor, supervisor)) is not None
        }
    )
    return supervisores, gerentes


def _routing_aprobadores_por_usuario(cursor, cod_vendedor: int) -> Tuple[List[int], List[int]]:
    """Identidades de aprobadores; evita confundir usuarios con vía placeholder."""
    cursor.execute(
        """SELECT DISTINCT sv.id_usuario_supervisor
           FROM ecom_org_supervisor_vendedor sv
           WHERE sv.cod_vendedor = %s AND sv.activo = 'Si'
             AND sv.id_usuario_supervisor IS NOT NULL""",
        (cod_vendedor,),
    )
    supervisores = [
        to_int_or_none(row.get("id_usuario_supervisor") if isinstance(row, dict) else row[0])
        for row in cursor.fetchall() or []
    ]
    supervisores = [uid for uid in supervisores if uid is not None]
    if not supervisores:
        return [], []
    ph = ",".join(["%s"] * len(supervisores))
    cursor.execute(
        f"""SELECT DISTINCT id_usuario_gerente
            FROM ecom_org_gerente_supervisor
            WHERE id_usuario_supervisor IN ({ph}) AND activo = 'Si'
              AND id_usuario_gerente IS NOT NULL""",
        tuple(supervisores),
    )
    gerentes = [
        to_int_or_none(row.get("id_usuario_gerente") if isinstance(row, dict) else row[0])
        for row in cursor.fetchall() or []
    ]
    return sorted(set(supervisores)), sorted({uid for uid in gerentes if uid is not None})


def _codigos_routing(valor: Any) -> List[int]:
    """Normaliza el contrato previo escalar para callers y mocks existentes."""
    if valor is None:
        return []
    valores = valor if isinstance(valor, (list, tuple, set)) else [valor]
    return [codigo for item in valores if (codigo := to_int_or_none(item)) is not None]


def _aprobador_autorizado_para_nivel(
    aprobador: int,
    *,
    cod_vendedor: int,
    supervisor: Sequence[int],
    gerente: Sequence[int],
    escalado: bool,
    ver_todos: bool,
) -> bool:
    if ver_todos:
        return True
    supervisores = _codigos_routing(supervisor)
    gerentes = _codigos_routing(gerente)
    if not escalado:
        if aprobador in supervisores:
            return True
        if aprobador in gerentes:
            return True
        return False
    if aprobador in gerentes:
        return True
    return False


def pedido_en_alcance_aprobador(
    base_empresa: str,
    sess_user: Dict[str, Any],
    cod_viajante_ped: int,
) -> bool:
    if puede_ver_todos_pedidos(sess_user):
        return True
    alcance = alcance_viajantes_comercial(base_empresa, sess_user)
    cv = to_int_or_none(cod_viajante_ped)
    return cv is not None and cv in alcance


def puede_aprobar_pedido(
    base_empresa: str,
    sess_user: Dict[str, Any],
    ped: Dict[str, Any],
) -> bool:
    """Indica si el usuario puede resolver la cola comercial de este pedido."""
    if not aprobacion_pedidos_activa(base_empresa):
        return False
    if not _tiene_permiso_aprobar(sess_user):
        return False
    estado = str(ped.get("estado_aprobacion_comercial") or ESTADO_NEUTRO).strip().lower()
    if estado != ESTADO_PENDIENTE:
        return False
    cv_ped = to_int_or_none(ped.get("CodViajante"))
    if cv_ped is None:
        return False
    if not pedido_en_alcance_aprobador(base_empresa, sess_user, cv_ped):
        return False

    aprobador = _cod_aprobador_desde_ctx(sess_user)
    id_aprobador = _id_aprobador_desde_ctx(sess_user)
    if aprobador is None and id_aprobador is None:
        return False
    if puede_ver_todos_pedidos(sess_user):
        return True

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                if id_aprobador is not None:
                    sup_ids, ger_ids = _routing_aprobadores_por_usuario(cursor, cv_ped)
                    escalado = _ultimo_evento_escalado(cursor, to_int_or_none(ped.get("CodigoMovimiento")) or 0)
                    return id_aprobador in (ger_ids if escalado else sup_ids + ger_ids)
                sup, ger = _routing_aprobadores(cursor, cv_ped)
                escalado = _ultimo_evento_escalado(cursor, to_int_or_none(ped.get("CodigoMovimiento")) or 0)
                return _aprobador_autorizado_para_nivel(
                    aprobador,
                    cod_vendedor=cv_ped,
                    supervisor=sup,
                    gerente=ger,
                    escalado=escalado,
                    ver_todos=False,
                )
            finally:
                cursor.close()
    except Exception as exc:
        logger.warning("puede_aprobar_pedido: %s", exc)
        return False


def resolver(
    base_empresa: str,
    cod_mov: int,
    accion: str,
    aprobador_cod: int,
    motivo: str,
    *,
    sess_user: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Aprueba o rechaza un pedido en cola comercial.

    ``accion``: ``aprobar`` | ``rechazar``
    """
    if not aprobacion_pedidos_activa(base_empresa):
        return False, "La aprobación comercial no está activa.", None

    acc = (accion or "").strip().lower()
    if acc not in ("aprobar", "rechazar"):
        return False, "Acción inválida. Use aprobar o rechazar.", None

    aprobador = to_int_or_none(aprobador_cod)
    if aprobador is None:
        return False, "Aprobador inválido.", None

    if sess_user and not _tiene_permiso_aprobar(sess_user):
        return False, "Sin permiso para aprobar pedidos.", None

    ped = _fetch_ped_aprobacion(base_empresa, cod_mov)
    if not ped:
        return False, "Pedido no encontrado.", None
    if (ped.get("Anulado") or "").strip().lower() in ("si", "sí"):
        return False, "El pedido está anulado.", None

    estado = str(ped.get("estado_aprobacion_comercial") or ESTADO_NEUTRO).strip().lower()
    if estado != ESTADO_PENDIENTE:
        return False, "El pedido no está pendiente de aprobación comercial.", None

    cv_ped = to_int_or_none(ped.get("CodViajante")) or 0
    if sess_user and not pedido_en_alcance_aprobador(base_empresa, sess_user, cv_ped):
        return False, "Pedido fuera de su alcance comercial.", None

    ver_todos = bool(sess_user and puede_ver_todos_pedidos(sess_user))
    motivo_txt = str_or_default(motivo, "-")

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                conn.autocommit(False)
                sup, ger = _routing_aprobadores(cursor, cv_ped)
                sup = _codigos_routing(sup)
                ger = _codigos_routing(ger)
                escalado = _ultimo_evento_escalado(cursor, cod_mov)

                if sess_user and not ver_todos:
                    id_aprobador = _id_aprobador_desde_ctx(sess_user)
                    if id_aprobador is not None:
                        sup_ids, ger_ids = _routing_aprobadores_por_usuario(cursor, cv_ped)
                        permitido = id_aprobador in (ger_ids if escalado else sup_ids + ger_ids)
                    else:
                        permitido = _aprobador_autorizado_para_nivel(
                            aprobador,
                            cod_vendedor=cv_ped,
                            supervisor=sup,
                            gerente=ger,
                            escalado=escalado,
                            ver_todos=False,
                        )
                    if not permitido:
                        return False, "No corresponde aprobar este pedido en su nivel jerárquico.", None

                ahora = _ahora()
                if acc == "rechazar":
                    cursor.execute(
                        """
                        UPDATE comp_ped
                        SET estado_aprobacion_comercial = %s,
                            aprobador_codviajante = %s,
                            aprobacion_fecha = %s,
                            aprobacion_motivo = %s
                        WHERE CodigoMovimiento = %s AND TipoComprobante = 'PED'
                        """,
                        (ESTADO_RECHAZADO, aprobador, ahora, motivo_txt, cod_mov),
                    )
                    _insertar_evento(
                        cursor,
                        cod_mov=cod_mov,
                        accion=ACCION_RECHAZADO,
                        regla_disparo="-",
                        cod_solicita=cv_ped,
                        cod_resuelve=aprobador,
                        motivo=motivo_txt,
                    )
                    conn.commit()
                    return True, "Pedido rechazado.", {"estado_aprobacion_comercial": ESTADO_RECHAZADO}

                # aprobar
                if not escalado and ger and sup and aprobador in sup:
                    _insertar_evento(
                        cursor,
                        cod_mov=cod_mov,
                        accion=ACCION_ESCALADO,
                        regla_disparo="-",
                        cod_solicita=cv_ped,
                        cod_resuelve=aprobador,
                        motivo="Escalado a gerente",
                    )
                    conn.commit()
                    return True, "Aprobado por supervisor; pendiente de gerente.", {
                        "estado_aprobacion_comercial": ESTADO_PENDIENTE,
                        "escalado": True,
                    }

                cursor.execute(
                    """
                    UPDATE comp_ped
                    SET estado_aprobacion_comercial = %s,
                        aprobador_codviajante = %s,
                        aprobacion_fecha = %s,
                        aprobacion_motivo = %s
                    WHERE CodigoMovimiento = %s AND TipoComprobante = 'PED'
                    """,
                    (ESTADO_APROBADO, aprobador, ahora, motivo_txt, cod_mov),
                )
                _insertar_evento(
                    cursor,
                    cod_mov=cod_mov,
                    accion=ACCION_APROBADO,
                    regla_disparo="-",
                    cod_solicita=cv_ped,
                    cod_resuelve=aprobador,
                    motivo=motivo_txt,
                )
                conn.commit()
                return True, "Pedido aprobado.", {"estado_aprobacion_comercial": ESTADO_APROBADO}
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
                try:
                    conn.autocommit(True)
                except Exception:
                    pass
    except Exception as exc:
        logger.exception("resolver aprobación cod_mov=%s: %s", cod_mov, exc)
        return False, "No se pudo resolver la aprobación.", None


def listar_pendientes_comerciales(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    dias: int = 60,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Pedidos con aprobación comercial pendiente visibles para el aprobador."""
    if not aprobacion_pedidos_activa(base_empresa):
        return []

    alcance = alcance_viajantes_comercial(base_empresa, sess_user)
    if not alcance and not puede_ver_todos_pedidos(sess_user):
        return []

    where = [
        "cp.TipoComprobante = 'PED'",
        "cp.estado_aprobacion_comercial = %s",
        "COALESCE(cp.Anulado, 'No') = 'No'",
        "cp.Fecha >= DATE_SUB(CURDATE(), INTERVAL %s DAY)",
    ]
    params: List[Any] = [ESTADO_PENDIENTE, max(1, min(int(dias), 365))]

    if not puede_ver_todos_pedidos(sess_user):
        if len(alcance) == 1:
            where.append("cp.CodViajante = %s")
            params.append(alcance[0])
        else:
            ph = ",".join(["%s"] * len(alcance))
            where.append(f"cp.CodViajante IN ({ph})")
            params.extend(alcance)

    params.append(max(1, min(int(limit), 500)))
    sql = f"""
        SELECT
            cp.CodigoMovimiento,
            cp.NroComprobante,
            cp.CodViajante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            TRIM(COALESCE(cp.estado_aprobacion_comercial, '-')) AS estado_aprobacion_comercial,
            cp.ImporteVenta,
            COALESCE(c.nombre_cliente, '') AS nombre_cliente
        FROM comp_ped cp
        LEFT JOIN cliente c ON c.Codigo = cp.Codigo
        WHERE {' AND '.join(where)}
        ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
        LIMIT %s
    """
    out: List[Dict[str, Any]] = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall() or []:
                ped = dict(row)
                ped["puede_aprobar"] = puede_aprobar_pedido(base_empresa, sess_user, ped)
                if ped["puede_aprobar"]:
                    out.append(ped)
    except Exception as exc:
        logger.warning("listar_pendientes_comerciales: %s", exc)
    return out
