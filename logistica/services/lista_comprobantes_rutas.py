"""
Listado de comprobantes en rutas — dominio Logística Synap (MySQL AdministraNET).

Consumido por el informe Reports ``comprobantes-rutas`` y por el módulo **Logística → Entregas**.
Lógica alineada al legado PHP (relay-logistica-comprobantes / listadoComprobantes).
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from core.utils.administranet_types import str_or_default, to_int_or_none

logger = logging.getLogger(__name__)

# Motivos de no entrega (paridad legado mayoristapp) — respaldo si no existe `logi_motivo_no_entrega`
MOTIVOS_NO_ENTREGA: Tuple[str, ...] = (
    "No se encuentra en domicilio",
    "Error de facturación",
    "Error de mercadería",
    "Mercadería defectuosa",
)

_LOGI_MOTIVO_TABLE = "logi_motivo_no_entrega"


def _tabla_motivos_no_entrega_existe(cursor) -> bool:
    try:
        cursor.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
            """,
            (_LOGI_MOTIVO_TABLE,),
        )
        row = cursor.fetchone()
        return bool(row and row[0])
    except Exception:
        return False


def listar_motivos_no_entrega_catalogo(conn) -> List[Dict[str, Any]]:
    """
    Filas del catálogo MySQL (activo=Si) o lista fija MOTIVOS_NO_ENTREGA como dicts.
    Cada dict: id (opcional), descripcion, requiere_detalle (bool), visible_portal (bool).
    """
    cursor = conn.cursor()
    try:
        if not _tabla_motivos_no_entrega_existe(cursor):
            return [
                {
                    "id": None,
                    "descripcion": d,
                    "requiere_detalle": False,
                    "visible_portal": False,
                }
                for d in MOTIVOS_NO_ENTREGA
            ]
        cursor.execute(
            f"""
            SELECT id, descripcion, requiere_detalle, visible_portal
            FROM {_LOGI_MOTIVO_TABLE}
            WHERE activo = 'Si'
            ORDER BY orden ASC, id ASC
            """
        )
        out: List[Dict[str, Any]] = []
        for r in cursor.fetchall():
            rid, desc, req_det, vis_p = r[0], r[1], r[2], r[3]
            ds = str_or_default(desc, "").strip()
            if not ds:
                continue
            out.append(
                {
                    "id": to_int_or_none(rid),
                    "descripcion": ds,
                    "requiere_detalle": str_or_default(req_det, "").strip() == "Si",
                    "visible_portal": str_or_default(vis_p, "").strip() == "Si",
                }
            )
        return out if out else [
            {
                "id": None,
                "descripcion": d,
                "requiere_detalle": False,
                "visible_portal": False,
            }
            for d in MOTIVOS_NO_ENTREGA
        ]
    finally:
        cursor.close()


def listar_motivos_no_entrega_descripciones(conn) -> List[str]:
    """Solo textos de motivo (compatibilidad API ``motivos``)."""
    return [m["descripcion"] for m in listar_motivos_no_entrega_catalogo(conn)]


def motivo_no_entrega_es_valido(conn, motivo: str) -> bool:
    m = str_or_default(motivo, "").strip()
    if not m:
        return False
    return m in set(listar_motivos_no_entrega_descripciones(conn))


def motivo_requiere_detalle(conn, motivo: str) -> bool:
    """True si el catálogo marca ``requiere_detalle`` para esa descripción."""
    m = str_or_default(motivo, "").strip()
    for row in listar_motivos_no_entrega_catalogo(conn):
        if row.get("descripcion") == m:
            return bool(row.get("requiere_detalle"))
    return False


def detalle_no_entrega_cumple(conn, motivo: str, detalle: str) -> bool:
    """Si el motivo exige detalle, ``detalle`` no puede quedar vacío (tras normalización)."""
    if not motivo_requiere_detalle(conn, motivo):
        return True
    d = str_or_default(detalle, "").strip()
    return d not in ("", "-")


def _permiso_supervisor_venta(cursor, id_usuario: int) -> Optional[str]:
    """Lee permiso_supervisor_venta de usuarios. None si no hay fila."""
    cursor.execute(
        "SELECT permiso_supervisor_venta FROM usuarios WHERE id_usuario = %s LIMIT 1",
        (id_usuario,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    val = row[0]
    if val is None:
        return None
    return str(val).strip()


def debe_restringir_por_chofer(permiso_supervisor_venta: Optional[str]) -> bool:
    """
    Paridad PHP: si session supervisor_venta == 'No' se filtra por chofer.
    En Synap usamos columna permiso_supervisor_venta == 'No'.
    """
    return (permiso_supervisor_venta or "").strip() == "No"


def usuario_puede_filtrar_por_chofer_en_catalogo(conn, id_usuario: int) -> bool:
    """Supervisor de ventas puede filtrar el listado por id de chofer; si no, solo aplica la regla por usuario."""
    c = conn.cursor()
    try:
        perm = _permiso_supervisor_venta(c, id_usuario)
        return not debe_restringir_por_chofer(perm)
    finally:
        c.close()


def usuario_tiene_vinculo_chofer_abm(conn, id_usuario: int) -> bool:
    """Hay al menos un registro activo en ``logi_abm_chofer`` para este ``id_usuario``."""
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT 1 FROM logi_abm_chofer
            WHERE anulado = 'No' AND id_usuario = %s
            LIMIT 1
            """,
            (id_usuario,),
        )
        return c.fetchone() is not None
    finally:
        c.close()


def ids_chofer_vinculados_a_usuario(conn, id_usuario: int) -> List[int]:
    """``logi_abm_chofer.id_usuario`` → choferes del operador (puede haber más de uno en legado)."""
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT id_chofer FROM logi_abm_chofer
            WHERE anulado = 'No' AND id_usuario = %s
            ORDER BY id_chofer ASC
            """,
            (id_usuario,),
        )
        out: List[int] = []
        for row in c.fetchall() or []:
            cid = to_int_or_none(row[0])
            if cid is not None:
                out.append(cid)
        return list(dict.fromkeys(out))
    finally:
        c.close()


def listar_rutas_catalogo_entregas(
    conn,
    ids_chofer: List[int],
    *,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Rutas asignadas a los choferes indicados (``logi_ruta_chofer``) que aún tienen al menos un
    remito en el listado operativo con ``entregado = 'No'`` (mismo criterio de joins que el listado).

    No se filtra ``logi_hoja_ruta.anulado`` aquí: el SQL principal del listado tampoco lo hace; exigirlo
    en el catálogo dejaba el combo de rutas vacío cuando la hoja figuraba como anulada pero el remito
    seguía apareciendo en pantalla.

    Sin choferes → lista vacía.
    """
    if not ids_chofer:
        return []
    lim = max(1, min(int(limit), 2000))
    placeholders = ",".join(["%s"] * len(ids_chofer))
    params: List[Any] = list(ids_chofer)
    params.append(lim)
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"""
            SELECT DISTINCT
                h.id_ruta AS id,
                CONCAT(
                    CAST(h.id_ruta AS CHAR),
                    ' — ',
                    COALESCE(NULLIF(TRIM(h.desc_ruta), ''), '(sin descripción)'),
                    ' · ',
                    DATE_FORMAT(h.fecha_salida, '%%d/%%m/%%Y %%H:%%i')
                ) AS text
            FROM logi_hoja_ruta AS h
            INNER JOIN logi_ruta_chofer AS rc
                ON rc.id_ruta = h.id_ruta AND rc.id_chofer IN ({placeholders})
            WHERE EXISTS (
                SELECT 1
                FROM rem_fact AS rf
                INNER JOIN comp_ped AS remito ON remito.CodigoMovimiento = rf.CodigoMovimientoR
                INNER JOIN rem_ped AS rp
                    ON rp.codmov_remito = remito.CodigoMovimiento AND rp.Anulado = 'No'
                INNER JOIN cuentacliente AS factura ON factura.CodigoMovimiento = rf.CodigoMovimientoF
                INNER JOIN cliente_datos_adicionales AS cda
                    ON cda.CodigoMovimiento = factura.CodigoMovimiento
                WHERE rf.Anulado = 'No'
                  AND remito.Anulado = 'No'
                  AND remito.entregado = 'No'
                  AND cda.id_ruta = h.id_ruta
              )
            ORDER BY h.fecha_salida DESC, h.id_ruta DESC
            LIMIT %s
            """,
            tuple(params),
        )
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []
        out: List[Dict[str, Any]] = []
        for row in rows:
            d = _row_to_dict(cols, row)
            rid = to_int_or_none(d.get("id"))
            out.append({"id": rid, "text": str_or_default(d.get("text"), "").strip() or str(rid)})
        return out
    finally:
        cursor.close()


def listar_choferes_catalogo_entregas(conn) -> List[Dict[str, Any]]:
    """Opciones para combo de chofer (ABM activo)."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id_chofer AS id, nombre_chofer AS text
            FROM logi_abm_chofer
            WHERE anulado = 'No'
            ORDER BY nombre_chofer ASC
            """
        )
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description] if cursor.description else []
        out: List[Dict[str, Any]] = []
        for row in rows:
            d = _row_to_dict(cols, row)
            rid = to_int_or_none(d.get("id"))
            txt = str_or_default(d.get("text"), "").strip()
            out.append({"id": rid, "text": txt or str(rid)})
        return out
    finally:
        cursor.close()


def _usuario_tiene_vinculo_chofer_abm_cursor(cursor, id_usuario: int) -> bool:
    """Misma semántica que ``usuario_tiene_vinculo_chofer_abm`` reutilizando un cursor abierto."""
    cursor.execute(
        """
        SELECT 1 FROM logi_abm_chofer
        WHERE anulado = 'No' AND id_usuario = %s
        LIMIT 1
        """,
        (id_usuario,),
    )
    return cursor.fetchone() is not None


def _restriccion_chofer_efectiva(
    filters: Dict[str, Any],
    cursor,
    id_usuario_sesion: Optional[int],
) -> bool:
    """
    - Pantalla **Entregas** (``logistica_contexto_entregas``): si el usuario tiene chofer en
      ``logi_abm_chofer``, el listado se acota siempre a esas asignaciones (no hace falta elegir chofer).
    - modo ``mi_ruta``: filtrar por chofer del usuario.
    - modo ``hoy`` u omitido (informe / otros): supervisor de ventas ve todo el período salvo reglas legacy.
    """
    if id_usuario_sesion is None:
        return False
    if filters.get("logistica_contexto_entregas") and _usuario_tiene_vinculo_chofer_abm_cursor(
        cursor, id_usuario_sesion
    ):
        return True
    modo = str_or_default(filters.get("logistica_modo"), "").strip().lower()
    if modo == "mi_ruta":
        return True
    perm = _permiso_supervisor_venta(cursor, id_usuario_sesion)
    return debe_restringir_por_chofer(perm)


def _fmt_fecha_argentina(d: Any) -> Optional[str]:
    """``dd/mm/aaaa`` desde ``date`` / ``datetime`` o None."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.strftime("%d/%m/%Y")
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return None


def _fmt_fecha_hora_argentina(dt: Any) -> Optional[str]:
    """``dd/mm/aaaa HH:MM`` desde ``datetime`` o None."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y %H:%M")
    return None


def _fmt_hora_mysql(t: Any) -> Optional[str]:
    """``HH:MM`` desde ``time``, ``timedelta`` o string legado."""
    if t is None:
        return None
    if isinstance(t, time):
        return t.strftime("%H:%M")
    if isinstance(t, datetime):
        return t.strftime("%H:%M")
    s = str_or_default(t, "").strip()
    if not s or s.startswith("00:00:00") and len(s) <= 8:
        return None
    if len(s) >= 5 and s[2] == ":":
        return s[:5]
    return s or None


def _parse_legacy_fecha_control_a_fecha_hora_ui(fc: Any) -> Optional[str]:
    """
    Normaliza ``comp_ped.fecha_control`` (VARCHAR legado) a ``dd/mm/aaaa HH:MM``.
    Paridad aproximada con STR_TO_DATE + DATE_FORMAT en MySQL (sin ``%`` en SQL).
    """
    s = str_or_default(fc, "").strip()
    if not s or s in ("0000-00-00 00:00:00", "0000-00-00"):
        return None
    s = re.sub(r"(\d{4})/\s+", r"\1 ", s)
    s = s.replace("/", "-")
    s = re.sub(r"\s+", " ", s).strip()
    for fmt in (
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s[:32], fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return None


def _parse_fecha_hora_entrega_ui(v: Any) -> Optional[str]:
    """``comp_ped.fecha_hora_entrega`` (VARCHAR/DATETIME) → ``dd/mm/aaaa HH:MM``."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.strftime("%d/%m/%Y %H:%M")
    s = str_or_default(v, "").strip()
    if not s or "0000-00-00" in s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            dt = datetime.strptime(s[:32], fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue
    return None


def _enriquecer_respuesta_detalle_remito(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construye columnas ``*B`` / ``*_fmt`` del modal de detalle sin DATE_FORMAT en SQL
    (evita conflicto de ``%`` con MySQLdb al enlazar ``%s``).
    """
    out = dict(row)

    out["FechaRemitoB"] = _fmt_fecha_argentina(out.get("fechaRemito"))
    out["FechaPedidoB"] = _fmt_fecha_argentina(out.get("fechaPedido"))
    out["FechaFacturaB"] = _fmt_fecha_argentina(out.get("fechaFactura"))

    out["fechaHoraRemitoB"] = _parse_legacy_fecha_control_a_fecha_hora_ui(out.get("fecha_control_remito_raw"))
    out["fechaHoraPedidoB"] = _parse_legacy_fecha_control_a_fecha_hora_ui(out.get("fecha_control_pedido_raw"))
    out["fechaHoraFacturaB"] = _fmt_fecha_hora_argentina(out.get("fecha_control_factura_raw"))

    out["fechaHoraEntregaB"] = _parse_fecha_hora_entrega_ui(out.get("fecha_hora_entrega_raw"))

    out["fecha_salida_ruta_fmt"] = _fmt_fecha_hora_argentina(out.get("fecha_salida_ruta_raw"))

    hd = _fmt_hora_mysql(out.get("hora_desde_ruta_raw"))
    hh = _fmt_hora_mysql(out.get("hora_hasta_ruta_raw"))
    if (hd in (None, "00:00") and hh in (None, "00:00")) or (hd == "00:00" and hh == "00:00"):
        out["ventana_horaria_ruta"] = None
    elif hd and hh:
        out["ventana_horaria_ruta"] = f"{hd} – {hh}"
    elif hd or hh:
        out["ventana_horaria_ruta"] = hd or hh
    else:
        out["ventana_horaria_ruta"] = None

    for k in (
        "fecha_control_remito_raw",
        "fecha_control_pedido_raw",
        "fecha_control_factura_raw",
        "fecha_hora_entrega_raw",
        "fecha_salida_ruta_raw",
        "hora_desde_ruta_raw",
        "hora_hasta_ruta_raw",
        "fechaPedido",
        "fechaFactura",
    ):
        out.pop(k, None)

    return out


def _row_to_dict(columns: List[str], row: tuple) -> Dict[str, Any]:
    d = dict(zip(columns, row))
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, bytes):
            try:
                out[k] = v.decode("latin1", errors="replace")
            except Exception:
                out[k] = str(v)
        else:
            out[k] = v
    return out


def _estado_entrega_label(entregado: Any, _id_usuario_no_entrega: Any = None) -> str:
    """Dos estados visibles: Entregado / No entregado (detalle puede usar _id_usuario_no_entrega; la etiqueta no)."""
    ent = (entregado or "").strip()
    if ent == "Si":
        return "Entregado"
    if ent == "No":
        return "No entregado"
    return str_or_default(ent, "-")


def estado_entrega_label(entregado: Any, id_usuario_no_entrega: Any = None) -> str:
    """Versión pública (informes, portal_compat)."""
    return _estado_entrega_label(entregado, id_usuario_no_entrega)


def _estados_entrega_filtro_efectivos(filters: Dict[str, Any]) -> Optional[str]:
    """
    None = sin filtro por estado (ninguno o ambos elegidos en UI).
    'Si' / 'No' = un solo estado.
    """
    raw = filters.get("logistica_estado_entrega")
    vals: List[str] = []
    if isinstance(raw, (list, tuple)):
        for x in raw:
            s = str_or_default(x, "").strip()
            if s in ("Si", "No"):
                vals.append(s)
    else:
        s = str_or_default(raw, "").strip()
        if s in ("Si", "No"):
            vals.append(s)
    vals = list(dict.fromkeys(vals))
    if len(vals) != 1:
        return None
    return vals[0]


def _codigos_cliente_filtro(filters: Dict[str, Any]) -> List[str]:
    """Códigos de cliente elegidos en el filtro (tags); puede ser uno o varios."""
    raw = filters.get("logistica_id_cliente")
    out: List[str] = []
    if isinstance(raw, (list, tuple)):
        for x in raw:
            s = str_or_default(x, "").strip()
            if s:
                out.append(s)
    else:
        s = str_or_default(raw, "").strip()
        if s:
            out.append(s)
    return list(dict.fromkeys(out))


def build_listado_sql_and_params(
    filters: Dict[str, Any],
    id_usuario_sesion: Optional[int],
    restriccion_chofer: bool,
) -> Tuple[str, List[Any]]:
    """
    Arma SQL listado y parámetros (solo %s, sin concatenación de entrada usuario en SQL crudo).
    """
    extra_where: List[str] = []
    params: List[Any] = []

    fecha_ini = filters.get("fecha_inicio") or filters.get("logistica_fecha_desde")
    fecha_fin = filters.get("fecha_fin") or filters.get("logistica_fecha_hasta")

    if fecha_ini and fecha_fin:
        extra_where.append("remito.Fecha BETWEEN %s AND %s")
        params.extend([fecha_ini, fecha_fin])

    estado_eff = _estados_entrega_filtro_efectivos(filters)
    if estado_eff == "Si":
        extra_where.append("remito.entregado = 'Si'")
    elif estado_eff == "No":
        extra_where.append("remito.entregado = 'No'")

    codigos_cli = _codigos_cliente_filtro(filters)
    if len(codigos_cli) == 1:
        extra_where.append("cliente.Codigo = %s")
        params.append(codigos_cli[0])
    elif len(codigos_cli) > 1:
        placeholders = ",".join(["%s"] * len(codigos_cli))
        extra_where.append(f"cliente.Codigo IN ({placeholders})")
        params.extend(codigos_cli)

    id_ruta_f = to_int_or_none(filters.get("logistica_id_ruta"))
    if id_ruta_f is not None:
        extra_where.append("hoja_ruta.id_ruta = %s")
        params.append(id_ruta_f)

    if filters.get("logistica_aplicar_filtro_chofer_id"):
        id_ch = to_int_or_none(filters.get("logistica_id_chofer"))
        if id_ch is not None:
            extra_where.append(
                "EXISTS (SELECT 1 FROM logi_ruta_chofer AS rc_fc "
                "WHERE rc_fc.id_ruta = hoja_ruta.id_ruta AND rc_fc.id_chofer = %s)"
            )
            params.append(id_ch)

    if restriccion_chofer and id_usuario_sesion is not None:
        extra_where.append(
            "EXISTS ("
            "SELECT 1 FROM logi_ruta_chofer AS rc_fil "
            "INNER JOIN logi_abm_chofer AS ch_fil ON ch_fil.id_chofer = rc_fil.id_chofer "
            "WHERE rc_fil.id_ruta = hoja_ruta.id_ruta AND ch_fil.id_usuario = %s"
            ")"
        )
        params.append(id_usuario_sesion)

    filtros_sql = ""
    if extra_where:
        filtros_sql = " AND " + " AND ".join(extra_where)

    sql = f"""
        SELECT
            DATE_FORMAT(remito.Fecha,'%%d/%%m/%%Y') AS fecha_remito,
            DATE_FORMAT(factura.Fecha,'%%d/%%m/%%Y') AS fecha_factura,
            DATE_FORMAT(factura.Fecha,'%%Y-%%m') AS mes_factura_ym,
            remito.NroComprobante AS nro_remito,
            remito.CodigoMovimiento AS cod_mov_remito,
            pedido.NroComprobante AS nro_pedido,
            pedido.CodigoMovimiento AS cod_mov_pedido,
            factura.NroComprobante AS nro_factura,
            remito.entregado AS entregado,
            remito.id_usuario_no_entrega AS id_usuario_no_entrega,
            remito.motivo_no_entrega AS motivo_no_entrega,
            DATE_FORMAT(remito.fecha_hora_entrega,'%%d/%%m/%%Y %%H:%%i') AS fecha_hora_entrega_fmt,
            CONCAT(cliente.nombre_cliente,' (',cliente.Codigo,')') AS cliente,
            NULLIF(TRIM(COALESCE(cliente.nombre_cliente, '')), '') AS nombre_cliente,
            COALESCE(
                NULLIF(TRIM(COALESCE(cd_fact.domicilio_ecom, '')), ''),
                NULLIF(TRIM(COALESCE(cd_ped.domicilio_ecom, '')), ''),
                NULLIF(TRIM(COALESCE(cd_rem.domicilio_ecom, '')), ''),
                NULLIF(
                    TRIM(
                        CONCAT_WS(
                            ' ',
                            NULLIF(TRIM(COALESCE(cd_fact.Calle, '')), ''),
                            NULLIF(TRIM(COALESCE(cd_fact.NroCalle, '')), ''),
                            NULLIF(TRIM(COALESCE(cd_fact.Dpto, '')), '')
                        )
                    ),
                    ''
                ),
                NULLIF(
                    TRIM(
                        CONCAT_WS(
                            ' ',
                            NULLIF(TRIM(COALESCE(cd_ped.Calle, '')), ''),
                            NULLIF(TRIM(COALESCE(cd_ped.NroCalle, '')), ''),
                            NULLIF(TRIM(COALESCE(cd_ped.Dpto, '')), '')
                        )
                    ),
                    ''
                ),
                NULLIF(
                    TRIM(
                        CONCAT_WS(
                            ' ',
                            NULLIF(TRIM(COALESCE(cd_rem.Calle, '')), ''),
                            NULLIF(TRIM(COALESCE(cd_rem.NroCalle, '')), ''),
                            NULLIF(TRIM(COALESCE(cd_rem.Dpto, '')), '')
                        )
                    ),
                    ''
                ),
                NULLIF(TRIM(COALESCE(pedido.tpv_domicilio_ocasional, '')), ''),
                NULLIF(TRIM(COALESCE(remito.tpv_domicilio_ocasional, '')), '')
            ) AS direccion_entrega,
            choferes_ruta.nombres_choferes AS nombre_chofer,
            CONCAT(COALESCE(usuario_entrega.apellido_usuario,''), ' ', COALESCE(usuario_entrega.nombre_usuario,'')) AS nombre_usuario_entrega,
            hoja_ruta.desc_ruta AS desc_ruta,
            hoja_ruta.estado_ruta AS estado_ruta,
            fact_ruta.orden_ruta AS orden_ruta,
            DATE_FORMAT(hoja_ruta.fecha_salida,'%%d/%%m/%%Y %%H:%%i') AS fecha_salida_ruta_fmt,
            CASE
                WHEN (
                    (hoja_ruta.hora_desde IS NULL OR TIME(hoja_ruta.hora_desde) = '00:00:00')
                    AND (hoja_ruta.hora_hasta IS NULL OR TIME(hoja_ruta.hora_hasta) = '00:00:00')
                ) THEN NULL
                ELSE CONCAT(
                    TIME_FORMAT(COALESCE(hoja_ruta.hora_desde, '00:00:00'), '%%H:%%i'),
                    ' – ',
                    TIME_FORMAT(COALESCE(hoja_ruta.hora_hasta, '00:00:00'), '%%H:%%i')
                )
            END AS ventana_horaria_ruta,
            (remito.SubTotalDesc + remito.IVA1 + remito.IVA2) AS total_remito
        FROM rem_fact
        LEFT JOIN comp_ped AS remito ON remito.CodigoMovimiento = rem_fact.CodigoMovimientoR
        LEFT JOIN cuentacliente AS factura ON factura.CodigoMovimiento = rem_fact.CodigoMovimientoF
        LEFT JOIN cliente_datos_adicionales AS fact_ruta ON fact_ruta.CodigoMovimiento = factura.CodigoMovimiento
        LEFT JOIN cliente_domicilio AS cd_fact
            ON cd_fact.id_cliente_domicilio = fact_ruta.id_cliente_domicilio
            AND (cd_fact.anulado IS NULL OR cd_fact.anulado = 'No')
        LEFT JOIN logi_hoja_ruta AS hoja_ruta ON hoja_ruta.id_ruta = fact_ruta.id_ruta
        LEFT JOIN (
            SELECT
                rc.id_ruta,
                GROUP_CONCAT(DISTINCT ch.nombre_chofer ORDER BY ch.nombre_chofer SEPARATOR ', ') AS nombres_choferes
            FROM logi_ruta_chofer AS rc
            INNER JOIN logi_abm_chofer AS ch ON ch.id_chofer = rc.id_chofer
            GROUP BY rc.id_ruta
        ) AS choferes_ruta ON choferes_ruta.id_ruta = hoja_ruta.id_ruta
        LEFT JOIN cliente ON cliente.Codigo = remito.Codigo
        LEFT JOIN usuarios AS usuario_entrega ON usuario_entrega.id_usuario = remito.id_usuario_no_entrega
        LEFT JOIN rem_ped ON rem_ped.codmov_remito = remito.CodigoMovimiento
        LEFT JOIN comp_ped AS pedido ON pedido.CodigoMovimiento = rem_ped.codmov_pedido
        LEFT JOIN cliente_datos_adicionales AS ped_da ON ped_da.CodigoMovimiento = pedido.CodigoMovimiento
        LEFT JOIN cliente_domicilio AS cd_ped
            ON cd_ped.id_cliente_domicilio = ped_da.id_cliente_domicilio
            AND (cd_ped.anulado IS NULL OR cd_ped.anulado = 'No')
        LEFT JOIN cliente_datos_adicionales AS rem_da ON rem_da.CodigoMovimiento = remito.CodigoMovimiento
        LEFT JOIN cliente_domicilio AS cd_rem
            ON cd_rem.id_cliente_domicilio = rem_da.id_cliente_domicilio
            AND (cd_rem.anulado IS NULL OR cd_rem.anulado = 'No')
        WHERE rem_ped.Anulado = 'No'
          AND remito.Anulado = 'No'
          {filtros_sql}
        ORDER BY
            COALESCE(DATE(hoja_ruta.fecha_salida), '1970-01-01') DESC,
            COALESCE(hoja_ruta.id_ruta, 0) DESC,
            COALESCE(fact_ruta.orden_ruta, 999999999) ASC,
            remito.Fecha DESC,
            remito.CodigoMovimiento DESC,
            remito.NroComprobante DESC
        LIMIT 2000
    """
    return sql, params


def ejecutar_listado(
    conn,
    filters: Dict[str, Any],
    id_usuario_sesion: Optional[int],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    cursor = conn.cursor()
    try:
        restriccion = _restriccion_chofer_efectiva(filters, cursor, id_usuario_sesion)

        sql, params = build_listado_sql_and_params(filters, id_usuario_sesion, restriccion)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        columns = [d[0] for d in cursor.description] if cursor.description else []
        data: List[Dict[str, Any]] = []
        for row in rows:
            raw = _row_to_dict(columns, row)
            raw["estado_entrega"] = _estado_entrega_label(
                raw.get("entregado"), raw.get("id_usuario_no_entrega")
            )
            # Columnas visibles amigables (cod_* quedan para acciones futuras / export)
            data.append(raw)
        notes: List[str] = []
        if restriccion:
            modo_l = str_or_default(filters.get("logistica_modo"), "").strip().lower()
            if modo_l == "mi_ruta":
                notes.append(
                    "Vista «Mi ruta»: solo comprobantes vinculados a su usuario como chofer."
                )
            elif filters.get("logistica_contexto_entregas") and id_usuario_sesion is not None:
                if _usuario_tiene_vinculo_chofer_abm_cursor(cursor, id_usuario_sesion):
                    notes.append(
                        "Rutas y comprobantes acotados a sus choferes en logística (vínculo usuario en ABM chofer)."
                    )
                else:
                    notes.append("Listado restringido por usuario (no supervisor de ventas).")
            else:
                notes.append("Listado restringido por usuario (no supervisor de ventas).")
        return data, notes
    finally:
        cursor.close()


def autocomplete_clientes(conn, q: str, limit: int = 100) -> List[Dict[str, str]]:
    q = (q or "").strip()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT cliente.Codigo AS id, cliente.nombre_cliente AS text
            FROM cliente
            WHERE cliente.Estado = 'Activo'
              AND cliente.nombre_cliente LIKE %s
            ORDER BY cliente.nombre_cliente ASC
            LIMIT %s
            """,
            (f"%{q}%", limit),
        )
        out = [{"id": str(r[0]), "text": str(r[1] or "")} for r in cursor.fetchall()]
        return out
    finally:
        cursor.close()


# Sin DATE_FORMAT/STR_TO_DATE con ``%`` en el literal: MySQLdb hace ``query % args`` y rompe el SQL.
# Las columnas ``*B`` / textos de fecha-hora se arman en ``_enriquecer_respuesta_detalle_remito``.
SQL_DETALLE_REMITO = """
    SELECT
        remito.Fecha AS fechaRemito,
        pedido.Fecha AS fechaPedido,
        factura.Fecha AS fechaFactura,
        remito.fecha_control AS fecha_control_remito_raw,
        pedido.fecha_control AS fecha_control_pedido_raw,
        factura.FechaControl AS fecha_control_factura_raw,
        remito.NroComprobante AS nroRemito,
        remito.CodigoMovimiento AS codMovRemito,
        pedido.NroComprobante AS nroPedido,
        pedido.CodigoMovimiento AS codMovPedido,
        factura.NroComprobante AS nroFactura,
        factura.CodigoMovimiento AS codMovFactura,
        remito.entregado,
        remito.id_usuario_no_entrega,
        remito.motivo_no_entrega,
        remito.detalle_no_entrega,
        remito.fecha_hora_entrega AS fecha_hora_entrega_raw,
        CONCAT(cliente.nombre_cliente,' (',cliente.Codigo,')') AS cliente,
        choferes_ruta.nombres_choferes AS nombre_chofer,
        CONCAT(COALESCE(usuario_entrega.apellido_usuario,''), ' ', COALESCE(usuario_entrega.nombre_usuario,'')) AS nombreUsuarioNoEntrega,
        hoja_ruta.desc_ruta,
        hoja_ruta.estado_ruta,
        factura_ruta.orden_ruta AS orden_ruta,
        hoja_ruta.fecha_salida AS fecha_salida_ruta_raw,
        hoja_ruta.hora_desde AS hora_desde_ruta_raw,
        hoja_ruta.hora_hasta AS hora_hasta_ruta_raw,
        (remito.SubTotalDesc + remito.IVA1 + remito.IVA2) AS totalRemito,
        (pedido.SubTotalDesc + pedido.IVA1 + pedido.IVA2) AS totalPedido,
        (factura.SubTotalDesc + factura.IVA1 + factura.IVA2) AS totalFactura
    FROM rem_fact
    LEFT JOIN comp_ped AS remito ON remito.CodigoMovimiento = rem_fact.CodigoMovimientoR
    LEFT JOIN rem_ped ON rem_ped.codmov_remito = remito.CodigoMovimiento
    LEFT JOIN comp_ped AS pedido ON pedido.CodigoMovimiento = rem_ped.codmov_pedido
    LEFT JOIN cuentacliente AS factura ON factura.CodigoMovimiento = rem_fact.CodigoMovimientoF
    LEFT JOIN cliente_datos_adicionales AS factura_ruta ON factura_ruta.CodigoMovimiento = factura.CodigoMovimiento
    LEFT JOIN logi_hoja_ruta AS hoja_ruta ON hoja_ruta.id_ruta = factura_ruta.id_ruta
    LEFT JOIN (
        SELECT
            rc.id_ruta,
            GROUP_CONCAT(DISTINCT ch.nombre_chofer ORDER BY ch.nombre_chofer SEPARATOR ', ') AS nombres_choferes
        FROM logi_ruta_chofer AS rc
        INNER JOIN logi_abm_chofer AS ch ON ch.id_chofer = rc.id_chofer
        GROUP BY rc.id_ruta
    ) AS choferes_ruta ON choferes_ruta.id_ruta = hoja_ruta.id_ruta
    LEFT JOIN cliente ON cliente.Codigo = remito.Codigo
    LEFT JOIN usuarios AS usuario_entrega ON usuario_entrega.id_usuario = remito.id_usuario_no_entrega
    WHERE rem_fact.Anulado = 'No'
      AND remito.Anulado = 'No'
      AND remito.CodigoMovimiento = %s
    LIMIT 1
"""


def obtener_detalle_remito(conn, cod_mov_remito: int) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    try:
        cursor.execute(SQL_DETALLE_REMITO, (cod_mov_remito,))
        row = cursor.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cursor.description]
        raw = _row_to_dict(cols, row)
        return _enriquecer_respuesta_detalle_remito(raw)
    finally:
        cursor.close()


def guardar_entrega(
    conn,
    *,
    cod_mov_remito: int,
    cod_mov_pedido: int,
    entregado: str,
    id_usuario_sesion: int,
    motivo_no_entrega: str,
    detalle_no_entrega: str,
) -> None:
    """UPDATE comp_ped remito + pedido en transacción (paridad PHP)."""
    entregado = str_or_default(entregado, "")
    if entregado not in ("Si", "No"):
        raise ValueError("Estado de entrega inválido.")

    cursor = conn.cursor()
    try:
        conn.autocommit(False)
        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")

        if entregado == "Si":
            sql_r = (
                "UPDATE comp_ped SET fecha_hora_entrega = %s, entregado = 'Si', "
                "id_usuario_no_entrega = NULL, motivo_no_entrega = NULL, "
                "detalle_no_entrega = NULL "
                "WHERE CodigoMovimiento = %s"
            )
            cursor.execute(sql_r, (now, cod_mov_remito))
            cursor.execute(sql_r, (now, cod_mov_pedido))
        else:
            motivo = str_or_default(motivo_no_entrega, "-")
            detalle = str_or_default(detalle_no_entrega, "-")
            sql_n = (
                "UPDATE comp_ped SET id_usuario_no_entrega = %s, motivo_no_entrega = %s, "
                "detalle_no_entrega = %s WHERE CodigoMovimiento = %s"
            )
            cursor.execute(
                sql_n,
                (id_usuario_sesion, motivo, detalle, cod_mov_remito),
            )
            cursor.execute(
                sql_n,
                (id_usuario_sesion, motivo, detalle, cod_mov_pedido),
            )

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.autocommit(True)
        except Exception:
            pass
        cursor.close()


def resolve_id_usuario_from_user(user: Any) -> Optional[int]:
    if user is None:
        return None
    uid = getattr(user, "id_usuario", None)
    if uid is not None:
        return to_int_or_none(uid)
    return None


def resolve_base_empresa(filters: Dict[str, Any], user: Any) -> Optional[str]:
    base = filters.get("base_empresa")
    if base:
        return str(base).strip() or None
    if hasattr(user, "base_empresa"):
        be = getattr(user, "base_empresa", None)
        if be:
            return str(be).strip()
    return getattr(settings, "DEFAULT_BASE_EMPRESA", None)
