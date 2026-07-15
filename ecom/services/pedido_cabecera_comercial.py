"""
Cabecera comercial de pedidos e-commerce (fechas, condición, lista).

Resolver único consumido por checkout simple y pedido masivo. Paridad AdministraNET:
vencimiento = fecha_pedido + cond_venta.Dias; permisos supervisor sobre lista/condición.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import MySQLdb

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_date_or_none, to_int_or_none

from ecom.services.vendedor_operativo import _si_no_supervisor


@dataclass
class PedidoCabeceraComercial:
    fecha_pedido: date
    fecha_entrega: Optional[date]
    vencimiento: date
    id_condventa: Optional[int]
    cond_venta: str
    lista_id: int
    editable_por_rol: bool = False


def es_supervisor_desde_ctx(ctx: Dict[str, Any]) -> bool:
    """Supervisor de venta (paridad ``vendedor_operativo`` / ``control.php``)."""
    return _si_no_supervisor(
        ctx.get("supervisor_venta") or ctx.get("permiso_supervisor_venta_web")
    )


def puede_editar_cabecera_comercial(ctx: Dict[str, Any]) -> bool:
    """Solo supervisor puede editar lista, condición y override de vencimiento."""
    return es_supervisor_desde_ctx(ctx)


def _as_date(value: Any) -> Optional[date]:
    """Normaliza ``date`` / ISO string a ``datetime.date``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    iso = to_date_or_none(value)
    if iso is None:
        return None
    try:
        return date.fromisoformat(iso)
    except ValueError:
        return None


def calcular_vencimiento(fecha_pedido: date, dias: int) -> date:
    """Vencimiento = fecha pedido + días corridos (paridad AdministraNET)."""
    return fecha_pedido + timedelta(days=int(dias or 0))


def _calcular_fecha_entrega_legacy(
    fecha_base: date,
    dias_entrega: int,
    dias_no_laborables: Optional[List[int]] = None,
) -> date:
    """Suma días de entrega evitando un día no laborable (ISO weekday 1=lun..7=dom)."""
    base = fecha_base + timedelta(days=int(dias_entrega or 0))
    no_lab = {int(d) for d in (dias_no_laborables or [])}
    if base.isoweekday() in no_lab:
        base = base + timedelta(days=1)
    return base


def dias_condicion(base_empresa: str, id_condventa: Optional[int]) -> int:
    """Días de la condición de venta (``cond_venta.Dias``)."""
    cv = to_int_or_none(id_condventa)
    if cv is None:
        return 0
    row = _fetch_condicion(base_empresa, cv)
    return to_int_or_none(row.get("Dias")) if row else 0


def _fetch_condicion(base_empresa: str, codigo: int) -> Optional[Dict[str, Any]]:
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(
            """
            SELECT Codigo, COALESCE(Descripcion, '') AS Descripcion, Dias
            FROM cond_venta
            WHERE Codigo = %s
            LIMIT 1
            """,
            [int(codigo)],
        )
        return cur.fetchone()


def cargar_defaults_cliente(base_empresa: str, id_cliente: int) -> Dict[str, Any]:
    """Lista, condición y descuentos del cliente legacy."""
    pool = get_mysql_pool()
    sql = """
        SELECT
            cliente.Codigo AS Codigo,
            cliente.id_cv AS id_cv,
            SUBSTRING(cliente.ListaPrecio, 6) AS codListaPrecio,
            cond_venta.Descripcion AS condVenta,
            cond_venta.Dias AS dias_condicion
        FROM cliente
        LEFT JOIN cond_venta ON cond_venta.Codigo = cliente.id_cv
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    with pool.get_connection(base_empresa) as conn:
        cur = conn.cursor(MySQLdb.cursors.DictCursor)
        cur.execute(sql, [int(id_cliente)])
        row = cur.fetchone()
    if not row:
        return {
            "id_cv": None,
            "lista_id": 1,
            "cond_venta": "",
            "dias_condicion": 0,
        }
    lista_id = to_int_or_none(row.get("codListaPrecio")) or 1
    if lista_id < 1 or lista_id > 6:
        lista_id = max(1, min(lista_id, 5))
    return {
        "id_cv": to_int_or_none(row.get("id_cv")),
        "lista_id": lista_id,
        "cond_venta": str_or_default(row.get("condVenta"), ""),
        "dias_condicion": to_int_or_none(row.get("dias_condicion")) or 0,
    }


def resolver_cabecera_comercial(
    base_empresa: str,
    id_cliente: int,
    *,
    es_supervisor: bool,
    fecha_pedido: Optional[date] = None,
    fecha_entrega: Optional[date] = None,
    vencimiento: Optional[date] = None,
    id_condventa: Optional[int] = None,
    lista_id: Optional[int] = None,
    dias_entrega: int = 0,
    dias_no_laborables: Optional[List[int]] = None,
    tipo_comprobante: str = "PED",
) -> Tuple[Optional[PedidoCabeceraComercial], Optional[str]]:
    """
    Resuelve cabecera comercial validada.

    Vendedor: ignora overrides de lista/condición/vencimiento.
    Supervisor: acepta overrides con validación ``vencimiento >= fecha_pedido``.
    """
    defaults = cargar_defaults_cliente(base_empresa, id_cliente)
    hoy = date.today()
    fp = _as_date(fecha_pedido) or hoy

    id_cv_ef = defaults["id_cv"]
    lista_ef = int(defaults["lista_id"] or 1)
    editable = False

    if es_supervisor:
        if id_condventa is not None:
            id_cv_nuevo = to_int_or_none(id_condventa)
            if id_cv_nuevo is not None:
                row_cv = _fetch_condicion(base_empresa, id_cv_nuevo)
                if not row_cv:
                    return None, "La condición de venta seleccionada no es válida."
                id_cv_ef = id_cv_nuevo
                editable = True
        if lista_id is not None:
            lista_nueva = to_int_or_none(lista_id)
            if lista_nueva is not None and 1 <= lista_nueva <= 5:
                lista_ef = lista_nueva
                editable = True

    dias = dias_condicion(base_empresa, id_cv_ef)
    if dias == 0 and defaults.get("dias_condicion"):
        dias = int(defaults["dias_condicion"])

    venc_auto = calcular_vencimiento(fp, dias)
    venc_ef = venc_auto
    if es_supervisor and vencimiento is not None:
        venc_ov = _as_date(vencimiento)
        if venc_ov is not None:
            if venc_ov < fp:
                return None, "El vencimiento no puede ser anterior a la fecha del pedido."
            venc_ef = venc_ov
            if venc_ov != venc_auto:
                editable = True

    cond_txt = defaults["cond_venta"]
    if id_cv_ef is not None:
        row_cv = _fetch_condicion(base_empresa, int(id_cv_ef))
        if row_cv:
            cond_txt = str_or_default(row_cv.get("Descripcion"), cond_txt)

    fe_ent: Optional[date] = None
    tipo = (tipo_comprobante or "PED").upper()
    if tipo == "PED":
        if fecha_entrega is not None:
            fe = _as_date(fecha_entrega)
            if fe is None:
                return None, "La fecha de entrega no es válida."
            if fe < fp:
                return None, "La fecha de entrega no puede ser anterior a la fecha del pedido."
            fe_ent = fe
        elif int(dias_entrega or 0) > 0:
            fe_ent = _calcular_fecha_entrega_legacy(fp, dias_entrega, dias_no_laborables)

    return (
        PedidoCabeceraComercial(
            fecha_pedido=fp,
            fecha_entrega=fe_ent,
            vencimiento=venc_ef,
            id_condventa=id_cv_ef,
            cond_venta=cond_txt,
            lista_id=lista_ef,
            editable_por_rol=editable,
        ),
        None,
    )


def cabecera_defaults_json(
    base_empresa: str,
    id_cliente: int,
    *,
    es_supervisor: bool,
    dias_entrega: int = 0,
    dias_no_laborables: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """Payload JSON para hidratar UI (fechas ISO + flags de permiso)."""
    cab, err = resolver_cabecera_comercial(
        base_empresa,
        id_cliente,
        es_supervisor=es_supervisor,
        dias_entrega=dias_entrega,
        dias_no_laborables=dias_no_laborables,
    )
    if not cab:
        return {"error": err or "No se pudo resolver la cabecera."}
    return {
        "fecha_pedido": cab.fecha_pedido.isoformat(),
        "fecha_entrega": cab.fecha_entrega.isoformat() if cab.fecha_entrega else None,
        "vencimiento": cab.vencimiento.isoformat(),
        "id_condventa": cab.id_condventa,
        "cond_venta": cab.cond_venta,
        "lista_id": cab.lista_id,
        "dias_condicion": dias_condicion(base_empresa, cab.id_condventa),
        "puede_editar": es_supervisor,
        "es_supervisor": es_supervisor,
    }


def parsear_cabecera_desde_body(
    body: Dict[str, Any],
) -> Dict[str, Any]:
    """Normaliza campos cabecera del body API (fechas ISO)."""
    cab = body.get("cabecera") if isinstance(body.get("cabecera"), dict) else body
    return {
        "fecha_pedido": to_date_or_none(cab.get("fecha_pedido")),
        "fecha_entrega": to_date_or_none(cab.get("fecha_entrega")),
        "vencimiento": to_date_or_none(cab.get("vencimiento")),
        "id_condventa": to_int_or_none(cab.get("id_condventa")),
        "lista_id": to_int_or_none(cab.get("lista_id")),
    }
