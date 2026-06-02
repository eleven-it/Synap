"""
Agregados del panel «Resumen ejecutivo (ventas)»: facturación en ``cuentacliente``
y rentabilidad por renglón en ``stock`` (PrecioNetoxR / PrecioCostoxR, paridad informe
rentabilidad AdministraNET), con desglose por rubro/subrubro.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reports.services.margen_costo_linea import (
    margen_costo_criterio_meta,
    signed_costo_neto_linea_sql,
)

logger = logging.getLogger(__name__)

_TIPOS_FA_FM = ("FA", "FB", "FC", "FE", "FM")
_TIPOS_NC = ("NCA", "NCB", "NCC", "NCE", "NCM")
_TIPOS_TODOS = _TIPOS_FA_FM + _TIPOS_NC

_STOCK_TIPO_COMP = (
    "Venta",
    "Venta TPV",
    "Devol - Cliente",
    "ND Anul NC",
)

_TOP_RANKING_LIMIT = 10
_TOP_PRODUCTOS_LIMIT = _TOP_RANKING_LIMIT

_SIN_CLASIFICAR = "Sin clasificar"


def _signed_precio_netoxr_sql() -> str:
    """Importe neto por renglón con signo FA / NC (paridad Top 10 / unidades)."""
    return """CASE
        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
            THEN COALESCE(st.PrecioNetoxR, 0)
        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
            THEN -COALESCE(st.PrecioNetoxR, 0)
        ELSE 0
    END"""


def _net_line_sql(alias: str = "cc") -> str:
    return f"""CASE
        WHEN {alias}.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
            THEN COALESCE({alias}.SubtotalDesc, 0)
        WHEN {alias}.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
            THEN -COALESCE({alias}.SubtotalDesc, 0)
        ELSE 0
    END"""


def _base_cc_where(alias: str = "cc") -> Tuple[str, List[Any]]:
    """Condiciones comunes sobre cuentacliente (sin filtro de fecha)."""
    ph = ",".join(["%s"] * len(_TIPOS_TODOS))
    w = (
        f"{alias}.Anulado = 'No' AND {alias}.CodigoMovimiento <> 0 "
        f"AND {alias}.TipoComprobante IN ({ph})"
    )
    return w, list(_TIPOS_TODOS)


def resolve_executive_scope(
    mayorista_sucursales: Sequence[int],
    minorista_sucursales: Sequence[int],
    sucursales_filtro: Optional[Sequence[int]] = None,
) -> Tuple[List[int], List[int], List[int]]:
    """
    Devuelve (mayorista_en_alcance, minorista_en_alcance, consolidado_en_alcance).

    Solo entran sucursales clasificadas (mayorista ∪ minorista). Si hay filtro UI,
    se intersecta con ese conjunto.
    """
    may_set = {int(x) for x in mayorista_sucursales}
    min_set = {int(x) for x in minorista_sucursales}
    classified = may_set | min_set
    if not classified:
        return [], [], []
    if sucursales_filtro:
        filt = classified & {int(x) for x in sucursales_filtro}
    else:
        filt = classified
    may_scope = sorted(filt & may_set)
    min_scope = sorted(filt & min_set)
    consolidado_scope = sorted(filt)
    return may_scope, min_scope, consolidado_scope


def _cc_scope_sql(scope_sucursales: Sequence[int]) -> Tuple[str, List[Any]]:
    """Limita comprobantes a ``cuentacliente.CodSucursal`` dentro del alcance."""
    if not scope_sucursales:
        return " AND 1=0 ", []
    ids = [int(x) for x in scope_sucursales]
    ph = ",".join(["%s"] * len(ids))
    return f" AND cc.CodSucursal IN ({ph}) ", ids


def _ventas_netas_dia(cursor, dia: date, scope_sucursales: Sequence[int]) -> float:
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    sql = f"""
        SELECT SUM({_net_line_sql('cc')}) AS v
        FROM cuentacliente cc
        WHERE cc.Fecha = %s AND {base_w}{suc_sql}
    """
    params: List[Any] = [dia] + base_p + suc_p
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _tickets_dia(cursor, dia: date, scope_sucursales: Sequence[int]) -> int:
    ph = ",".join(["%s"] * len(_TIPOS_FA_FM))
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    sql = f"""
        SELECT COUNT(*) AS c
        FROM cuentacliente cc
        WHERE cc.Fecha = %s AND {base_w}{suc_sql}
        AND cc.TipoComprobante IN ({ph})
    """
    params: List[Any] = [dia] + base_p + suc_p + list(_TIPOS_FA_FM)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _unidades_dia(cursor, dia: date, scope_sucursales: Sequence[int]) -> float:
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    ph_tc = ",".join(["%s"] * len(_STOCK_TIPO_COMP))
    sql = f"""
        SELECT SUM(
            CASE
                WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                    THEN COALESCE(st.Cantidad, 0)
                WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                    THEN -COALESCE(st.Cantidad, 0)
                ELSE 0
            END
        ) AS u
        FROM stock st
        INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
        WHERE cc.Fecha = %s
          AND {base_w}{suc_sql}
          AND st.Anulado = 'No'
          AND st.TipoComp IN ({ph_tc})
    """
    params = [dia] + base_p + suc_p + list(_STOCK_TIPO_COMP)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return float(row[0] or 0) if row else 0.0


def _serie_horaria(cursor, dia: date, scope_sucursales: Sequence[int]) -> List[Dict[str, Any]]:
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    sql = f"""
        SELECT HOUR(cc.FechaControl) AS hora, SUM({_net_line_sql('cc')}) AS ventas_netas
        FROM cuentacliente cc
        WHERE cc.Fecha = %s AND {base_w}{suc_sql}
        GROUP BY HOUR(cc.FechaControl)
        ORDER BY hora
    """
    params = [dia] + base_p + suc_p
    cursor.execute(sql, params)
    by_h = {int(r[0]): float(r[1] or 0) for r in cursor.fetchall() if r[0] is not None}
    out = []
    for h in range(24):
        out.append({"hora": h, "ventas_netas": round(by_h.get(h, 0.0), 2)})
    return out


def _serie_7_dias(cursor, fecha_fin: date, scope_sucursales: Sequence[int]) -> List[Dict[str, Any]]:
    fecha_ini = fecha_fin - timedelta(days=6)
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    sql = f"""
        SELECT cc.Fecha AS dia, SUM({_net_line_sql('cc')}) AS ventas_netas
        FROM cuentacliente cc
        WHERE cc.Fecha >= %s AND cc.Fecha <= %s AND {base_w}{suc_sql}
        GROUP BY cc.Fecha
        ORDER BY cc.Fecha
    """
    params = [fecha_ini, fecha_fin] + base_p + suc_p
    cursor.execute(sql, params)
    raw = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
    out = []
    d = fecha_ini
    while d <= fecha_fin:
        out.append({"fecha": d.isoformat(), "ventas_netas": round(raw.get(d, 0.0), 2)})
        d += timedelta(days=1)
    return out


def _top_productos_ventas_dia(
    cursor,
    dia: date,
    *,
    scope_sucursales: Sequence[int],
    orden_rank: str = "importe_neto",
    limit: int = _TOP_PRODUCTOS_LIMIT,
) -> List[Dict[str, Any]]:
    """
    Top artículos del día (renglón ``stock`` + ``cuentacliente``).
    Orden: ``importe_neto`` (suma PrecioNetoxR con signo FA/NC) o ``unidades``.
    Paridad de filtros con ``_unidades_dia``.
    """
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    ph_tc = ",".join(["%s"] * len(_STOCK_TIPO_COMP))
    qty_expr = """
        SUM(CASE
            WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                THEN COALESCE(st.Cantidad, 0)
            WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                THEN -COALESCE(st.Cantidad, 0)
            ELSE 0
        END)
    """
    neto_signed = _signed_precio_netoxr_sql()
    imp_expr = f"SUM({neto_signed})"
    lim = max(1, min(int(limit), 50))
    orden_rank = (orden_rank or "importe_neto").strip().lower()
    if orden_rank not in ("unidades", "importe_neto"):
        orden_rank = "importe_neto"
    order_sql = (
        "z.unidades DESC, z.importe_neto DESC"
        if orden_rank == "unidades"
        else "z.importe_neto DESC, z.unidades DESC"
    )
    sql = f"""
        SELECT z.id_art, z.codigo_articulo, z.descripcion, z.unidades, z.importe_neto
        FROM (
            SELECT
                st.IDArt AS id_art,
                COALESCE(MAX(a.CodigoArticulo), '') AS codigo_articulo,
                COALESCE(MAX(a.NombreArticulo), '-') AS descripcion,
                {qty_expr} AS unidades,
                {imp_expr} AS importe_neto
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo a ON a.IDArt = st.IDArt
            WHERE cc.Fecha = %s
              AND {base_w}{suc_sql}
              AND st.Anulado = 'No'
              AND st.TipoComp IN ({ph_tc})
              AND st.IDArt IS NOT NULL AND st.IDArt <> 0
            GROUP BY st.IDArt
        ) z
        WHERE (ABS(z.importe_neto) > 0.000001 OR ABS(z.unidades) > 0.000001)
        ORDER BY {order_sql}
        LIMIT {lim}
    """
    params: List[Any] = [dia] + base_p + suc_p + list(_STOCK_TIPO_COMP)
    cursor.execute(sql, params)
    desc = cursor.description
    if not desc or not isinstance(desc, (list, tuple)):
        return []
    cols = [d[0] for d in desc]
    out: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        d = dict(zip(cols, row))
        id_art = d.get("id_art")
        try:
            id_art_i = int(id_art) if id_art is not None else 0
        except (TypeError, ValueError):
            id_art_i = 0
        cod = d.get("codigo_articulo")
        cod_s = str(cod).strip() if cod is not None else ""
        des = (d.get("descripcion") or "-").strip() if d.get("descripcion") is not None else "-"
        if len(des) > 200:
            des = des[:197] + "..."
        out.append(
            {
                "id_art": id_art_i,
                "codigo_articulo": cod_s,
                "descripcion": des,
                "unidades": round(float(d.get("unidades") or 0), 4),
                "importe_neto": round(float(d.get("importe_neto") or 0), 2),
            }
        )
    return out


def _margen_bruto_totales_dia(
    cursor,
    dia: date,
    scope_sucursales: Sequence[int],
) -> Dict[str, Any]:
    """
    Totales de rentabilidad por renglón ``stock`` (misma ventana que unidades del día).
    """
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    ph_tc = ",".join(["%s"] * len(_STOCK_TIPO_COMP))
    neto = _signed_precio_netoxr_sql()
    costo = signed_costo_neto_linea_sql()
    sql = f"""
        SELECT
            SUM({neto}) AS venta_neta_lineas,
            SUM({costo}) AS costo_neto_lineas
        FROM stock st
        INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
        WHERE cc.Fecha = %s
          AND {base_w}{suc_sql}
          AND st.Anulado = 'No'
          AND st.TipoComp IN ({ph_tc})
    """
    params: List[Any] = [dia] + base_p + suc_p + list(_STOCK_TIPO_COMP)
    cursor.execute(sql, params)
    row = cursor.fetchone()
    v_lineas = float(row[0] or 0) if row else 0.0
    c_lineas = float(row[1] or 0) if row else 0.0
    margen = v_lineas - c_lineas
    pct: Optional[float]
    if abs(v_lineas) < 1e-9:
        pct = None
    else:
        pct = round(margen / v_lineas * 100.0, 2)
    return {
        "venta_neta_lineas": round(v_lineas, 2),
        "costo_neto_lineas": round(c_lineas, 2),
        "margen_absoluto": round(margen, 2),
        "pct_sobre_venta_lineas": pct,
    }


def _margen_por_rubro_dia(
    cursor,
    dia: date,
    scope_sucursales: Sequence[int],
) -> List[Dict[str, Any]]:
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    ph_tc = ",".join(["%s"] * len(_STOCK_TIPO_COMP))
    neto = _signed_precio_netoxr_sql()
    costo = signed_costo_neto_linea_sql()
    sql = f"""
        SELECT
            z.codigo_rubro,
            MAX(z.nombre_rubro) AS nombre_rubro,
            SUM(z.venta_neta) AS venta_neta,
            SUM(z.costo_neto) AS costo_neto
        FROM (
            SELECT
                COALESCE(a.CodigoRubro, -1) AS codigo_rubro,
                CASE
                    WHEN COALESCE(a.CodigoRubro, -1) = -1 THEN %s
                    ELSE COALESCE(r.NombreRubro, %s)
                END AS nombre_rubro,
                {neto} AS venta_neta,
                {costo} AS costo_neto
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo a ON a.IDArt = st.IDArt
            LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
            WHERE cc.Fecha = %s
              AND {base_w}{suc_sql}
              AND st.Anulado = 'No'
              AND st.TipoComp IN ({ph_tc})
        ) z
        GROUP BY z.codigo_rubro
        HAVING ABS(SUM(z.venta_neta)) > 0.000001 OR ABS(SUM(z.costo_neto)) > 0.000001
        ORDER BY SUM(z.venta_neta) DESC, MAX(z.nombre_rubro) ASC
        LIMIT %s
    """
    params: List[Any] = [_SIN_CLASIFICAR, _SIN_CLASIFICAR, dia] + base_p + suc_p + list(_STOCK_TIPO_COMP) + [_TOP_RANKING_LIMIT]
    cursor.execute(sql, params)
    desc = cursor.description
    if not desc or not isinstance(desc, (list, tuple)):
        return []
    cols = [d[0] for d in desc]
    out: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        d = dict(zip(cols, row))
        try:
            cr = int(d.get("codigo_rubro"))
        except (TypeError, ValueError):
            cr = -1
        vn = float(d.get("venta_neta") or 0)
        cn = float(d.get("costo_neto") or 0)
        ma = vn - cn
        pct: Optional[float] = None if abs(vn) < 1e-9 else round(ma / vn * 100.0, 2)
        nombre = str(d.get("nombre_rubro") or _SIN_CLASIFICAR).strip() or _SIN_CLASIFICAR
        out.append(
            {
                "codigo_rubro": cr,
                "nombre_rubro": nombre,
                "venta_neta": round(vn, 2),
                "costo_neto": round(cn, 2),
                "margen_absoluto": round(ma, 2),
                "pct_sobre_venta": pct,
            }
        )
    return out


def _margen_por_subrubro_dia(
    cursor,
    dia: date,
    scope_sucursales: Sequence[int],
) -> List[Dict[str, Any]]:
    base_w, base_p = _base_cc_where("cc")
    suc_sql, suc_p = _cc_scope_sql(scope_sucursales)
    ph_tc = ",".join(["%s"] * len(_STOCK_TIPO_COMP))
    neto = _signed_precio_netoxr_sql()
    costo = signed_costo_neto_linea_sql()
    sql = f"""
        SELECT
            z.id_subrubro,
            MAX(z.codigo_rubro) AS codigo_rubro,
            MAX(z.nombre_rubro) AS nombre_rubro,
            MAX(z.nombre_subrubro) AS nombre_subrubro,
            SUM(z.venta_neta) AS venta_neta,
            SUM(z.costo_neto) AS costo_neto
        FROM (
            SELECT
                COALESCE(sr.IDSubRubro, -1) AS id_subrubro,
                COALESCE(a.CodigoRubro, -1) AS codigo_rubro,
                CASE
                    WHEN COALESCE(a.CodigoRubro, -1) = -1 THEN %s
                    ELSE COALESCE(r.NombreRubro, %s)
                END AS nombre_rubro,
                CASE
                    WHEN COALESCE(sr.IDSubRubro, -1) = -1 THEN %s
                    ELSE COALESCE(sr.NombreSubRubro, %s)
                END AS nombre_subrubro,
                {neto} AS venta_neta,
                {costo} AS costo_neto
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo a ON a.IDArt = st.IDArt
            LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
            LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
            WHERE cc.Fecha = %s
              AND {base_w}{suc_sql}
              AND st.Anulado = 'No'
              AND st.TipoComp IN ({ph_tc})
        ) z
        GROUP BY z.id_subrubro
        HAVING ABS(SUM(z.venta_neta)) > 0.000001 OR ABS(SUM(z.costo_neto)) > 0.000001
        ORDER BY SUM(z.venta_neta) DESC, MAX(z.nombre_subrubro) ASC
        LIMIT %s
    """
    params: List[Any] = [
        _SIN_CLASIFICAR,
        _SIN_CLASIFICAR,
        _SIN_CLASIFICAR,
        _SIN_CLASIFICAR,
        dia,
    ] + base_p + suc_p + list(_STOCK_TIPO_COMP) + [_TOP_RANKING_LIMIT]
    cursor.execute(sql, params)
    desc = cursor.description
    if not desc or not isinstance(desc, (list, tuple)):
        return []
    cols = [d[0] for d in desc]
    out: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        d = dict(zip(cols, row))
        try:
            isr = int(d.get("id_subrubro"))
        except (TypeError, ValueError):
            isr = -1
        try:
            cr = int(d.get("codigo_rubro"))
        except (TypeError, ValueError):
            cr = -1
        vn = float(d.get("venta_neta") or 0)
        cn = float(d.get("costo_neto") or 0)
        ma = vn - cn
        pct: Optional[float] = None if abs(vn) < 1e-9 else round(ma / vn * 100.0, 2)
        nr = str(d.get("nombre_rubro") or _SIN_CLASIFICAR).strip() or _SIN_CLASIFICAR
        ns = str(d.get("nombre_subrubro") or _SIN_CLASIFICAR).strip() or _SIN_CLASIFICAR
        out.append(
            {
                "id_subrubro": isr,
                "codigo_rubro": cr,
                "nombre_rubro": nr,
                "nombre_subrubro": ns,
                "venta_neta": round(vn, 2),
                "costo_neto": round(cn, 2),
                "margen_absoluto": round(ma, 2),
                "pct_sobre_venta": pct,
            }
        )
    return out


def _split_canal(
    cursor,
    dia: date,
    may_scope: Sequence[int],
    min_scope: Sequence[int],
    consolidado_scope: Sequence[int],
) -> Dict[str, float]:
    """Ventas del día por canal (solo sucursales clasificadas en alcance)."""
    m_may = _ventas_netas_dia(cursor, dia, may_scope)
    m_min = _ventas_netas_dia(cursor, dia, min_scope)
    consolidado = _ventas_netas_dia(cursor, dia, consolidado_scope)
    return {
        "mayorista": round(m_may, 2),
        "minorista": round(m_min, 2),
        "consolidado": round(consolidado, 2),
    }


def _pct_change(actual: float, anterior: float) -> Optional[float]:
    if anterior == 0:
        return None
    return round((actual - anterior) / anterior * 100.0, 2)


def _normalizar_top_productos_orden(raw: Optional[str]) -> str:
    s = (raw or "").strip().lower()
    if s in ("unidades", "u", "cantidad", "qty"):
        return "unidades"
    return "importe_neto"


def fetch_sucursales_activas(cursor) -> List[Dict[str, Any]]:
    """Sucursales activas en AdministraNET (modal de clasificación)."""
    try:
        cursor.execute(
            """
            SELECT id_sucursal, nombre_sucursal
            FROM sucursales
            WHERE anulado = 'No' OR anulado IS NULL
            ORDER BY nombre_sucursal
            """
        )
        desc = cursor.description
        if not desc or not isinstance(desc, (list, tuple)):
            return []
        cols = [d[0] for d in desc]
    except Exception:
        logger.exception("fetch_sucursales_activas: error al listar sucursales")
        return []
    out: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        r = dict(zip(cols, row))
        try:
            sid = int(r.get("id_sucursal"))
        except (TypeError, ValueError):
            continue
        nombre = str(r.get("nombre_sucursal") or "-").strip()
        out.append({"id_sucursal": sid, "nombre_sucursal": nombre})
    return out


# Alias usado por Command Center y código legacy.
fetch_sucursales_ejecutivo = fetch_sucursales_activas


def fetch_sucursales_clasificadas(
    cursor, classified_ids: Sequence[int]
) -> List[Dict[str, Any]]:
    """Nombres de sucursales clasificadas (filtro multiselección del panel)."""
    if not classified_ids:
        return []
    ids = sorted({int(x) for x in classified_ids})
    ph = ",".join(["%s"] * len(ids))
    try:
        cursor.execute(
            f"""
            SELECT id_sucursal, nombre_sucursal
            FROM sucursales
            WHERE id_sucursal IN ({ph})
              AND (anulado = 'No' OR anulado IS NULL)
            ORDER BY nombre_sucursal
            """,
            ids,
        )
        desc = cursor.description
        if not desc:
            return []
        cols = [d[0] for d in desc]
    except Exception:
        logger.exception("fetch_sucursales_clasificadas: error al listar")
        return []
    out: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        r = dict(zip(cols, row))
        try:
            sid = int(r.get("id_sucursal"))
        except (TypeError, ValueError):
            continue
        nombre = str(r.get("nombre_sucursal") or "-").strip()
        out.append({"id_sucursal": sid, "nombre_sucursal": nombre})
    return out


def run_executive_summary(
    cursor,
    fecha_referencia: date,
    mayorista_sucursales: Sequence[int],
    minorista_sucursales: Sequence[int],
    *,
    sucursales_filtro: Optional[Sequence[int]] = None,
    top_productos_orden: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Calcula payload del panel ejecutivo. Solo incluye sucursales clasificadas
    (mayorista o minorista). Las no clasificadas no entran en ningún agregado.
    """
    orden_tp = _normalizar_top_productos_orden(top_productos_orden)
    may_scope, min_scope, consolidado_scope = resolve_executive_scope(
        mayorista_sucursales,
        minorista_sucursales,
        sucursales_filtro,
    )
    hoy = fecha_referencia
    ayer = hoy - timedelta(days=1)
    semana_pasada = hoy - timedelta(days=7)

    v_hoy = _ventas_netas_dia(cursor, hoy, consolidado_scope)
    v_ayer = _ventas_netas_dia(cursor, ayer, consolidado_scope)
    v_sem = _ventas_netas_dia(cursor, semana_pasada, consolidado_scope)

    tickets = _tickets_dia(cursor, hoy, consolidado_scope)
    ticket_prom = (v_hoy / tickets) if tickets else None

    unidades = _unidades_dia(cursor, hoy, consolidado_scope)

    split = _split_canal(cursor, hoy, may_scope, min_scope, consolidado_scope)
    gap_vs_ayer = round(v_hoy - v_ayer, 2)

    margen_bruto = _margen_bruto_totales_dia(cursor, hoy, consolidado_scope)
    margen_por_rubro = _margen_por_rubro_dia(cursor, hoy, consolidado_scope)
    margen_por_subrubro = _margen_por_subrubro_dia(cursor, hoy, consolidado_scope)
    criterio_costo = margen_costo_criterio_meta()

    classified_all = sorted(
        {int(x) for x in mayorista_sucursales} | {int(x) for x in minorista_sucursales}
    )

    return {
        "fecha_referencia": hoy.isoformat(),
        "kpis": {
            "ventas_netas_dia": round(v_hoy, 2),
            "gap_vs_ayer_monto": gap_vs_ayer,
            "pct_vs_ayer": _pct_change(v_hoy, v_ayer),
            "pct_vs_misma_semana_anterior": _pct_change(v_hoy, v_sem),
            "tickets": tickets,
            "ticket_promedio": round(ticket_prom, 2) if ticket_prom is not None else None,
            "unidades_vendidas": round(unidades, 4),
            "ventas_ayer_monto": round(v_ayer, 2),
            "ventas_misma_semana_anterior_monto": round(v_sem, 2),
        },
        "margen_bruto": margen_bruto,
        "margen_por_rubro": margen_por_rubro,
        "margen_por_subrubro": margen_por_subrubro,
        "split_mayorista_minorista": split,
        "serie_horaria": _serie_horaria(cursor, hoy, consolidado_scope),
        "serie_7_dias": _serie_7_dias(cursor, hoy, consolidado_scope),
        "top_productos": _top_productos_ventas_dia(
            cursor,
            hoy,
            scope_sucursales=consolidado_scope,
            orden_rank=orden_tp,
        ),
        "sucursales_disponibles": fetch_sucursales_clasificadas(cursor, classified_all),
        "meta": {
            "definicion": "executive-sales-v3-sucursal",
            "hora_eje": "FechaControl",
            "dia_contable": "Fecha",
            "top_productos_criterio": "importe_neto_linea",
            "margen_costo_criterio": criterio_costo,
            "margen_venta_criterio": "precio_netoxr_linea",
            "nota_margen_costo_historico": (
                "Mayo 2026: breve desvío con escala Display/Bulto (revertido). "
                "Criterio vigente: suma firmada de PrecioCostoxR por renglón, "
                "paridad informe rentabilidad AdministraNET (venta_rentabilidad_resumen)."
            ),
            "sucursales_filtro": list(sucursales_filtro) if sucursales_filtro else [],
            "sucursales_clasificadas_total": len(classified_all),
            "sin_sucursales_clasificadas": len(classified_all) == 0,
            "top_productos_orden": orden_tp,
        },
    }
