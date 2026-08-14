# -*- coding: utf-8 -*-
"""
Runner: Ventas BOM en docenas.

Packs facturados → explosión en_abm_formula → agregado por artículo componente.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

from reports.services.connection_pool import get_mysql_pool
from reports.services.ventas_bom_docenas_rules import (
    STOCK_TIPO_COMP,
    TIPOS_FAC,
    TIPOS_NC,
    VENTAS_BOM_DOCENAS_SLUG,
    docenas_desde_pares,
    explode_pack_qty_to_components,
    sql_in_literals,
    sql_signo_qty_expr,
)

logger = logging.getLogger(__name__)


def _as_int_list(raw) -> List[int]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    elif not isinstance(raw, (list, tuple, set)):
        raw = [raw]
    out: List[int] = []
    for item in raw:
        try:
            s = str(item).strip()
            if not s:
                continue
            out.append(int(float(s)))
        except (TypeError, ValueError):
            continue
    return out


def _resolve_base_empresa(user, filters: dict) -> Optional[str]:
    base = filters.get("base_empresa")
    if base:
        return base
    if user is not None and hasattr(user, "base_empresa") and user.base_empresa:
        return user.base_empresa
    return getattr(settings, "DEFAULT_BASE_EMPRESA", None)


def _resolve_period(filters: dict, resolve_period_dates) -> Tuple[Optional[str], Optional[str]]:
    # Compatibilidad: UI moderna usa fechas de facturación; legacy usa fecha_inicio/fin.
    patched = dict(filters)
    if patched.get("fecha_inicio_facturacion") and not patched.get("fecha_inicio"):
        patched["fecha_inicio"] = patched.get("fecha_inicio_facturacion")
    if patched.get("fecha_fin_facturacion") and not patched.get("fecha_fin"):
        patched["fecha_fin"] = patched.get("fecha_fin_facturacion")
    if patched.get("fecha_inicio") and not patched.get("fecha_inicio_facturacion"):
        patched["fecha_inicio_facturacion"] = patched.get("fecha_inicio")
    if patched.get("fecha_fin") and not patched.get("fecha_fin_facturacion"):
        patched["fecha_fin_facturacion"] = patched.get("fecha_fin")
    # Preferir resolve_period_dates del runner (acepta fecha_inicio/_fin).
    return resolve_period_dates(patched)


def _fetch_pack_qty_rows(cursor, where_clause: str, params: list) -> List[Dict[str, Any]]:
    tipo_comp = sql_in_literals(STOCK_TIPO_COMP)
    signo = sql_signo_qty_expr()
    sql = f"""
        SELECT
            art.IDArt AS id_art_pack,
            art.id_en_abm AS id_en_abm,
            COALESCE(art.CodigoArticuloT, CAST(art.CodigoArticulo AS CHAR), '') AS codigo_pack,
            COALESCE(art.NombreArticulo, '') AS nombre_pack,
            SUM({signo}) AS qty_pack
        FROM stock st
        INNER JOIN cuentacliente cc
            ON cc.CodigoMovimiento = st.CodigoMovimiento
        INNER JOIN articulo art
            ON art.IDArt = st.IDArt
        WHERE {where_clause}
          AND st.Anulado = 'No'
          AND COALESCE(st.TipoComp, '') IN ({tipo_comp})
          AND COALESCE(st.visualiza_ensamble, 'No') = 'No'
          AND art.id_en_abm IS NOT NULL
          AND art.id_en_abm <> 0
        GROUP BY art.IDArt, art.id_en_abm, art.CodigoArticuloT, art.CodigoArticulo, art.NombreArticulo
        HAVING ABS(SUM({signo})) > 0.000001
    """
    cursor.execute(sql, params)
    columns = [d[0] for d in cursor.description] if cursor.description else []
    rows = []
    for row in cursor.fetchall() or []:
        rows.append(dict(zip(columns, row)))
    return rows


def _fetch_bom_by_en_abm(cursor, ids_en_abm: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    if not ids_en_abm:
        return {}
    placeholders = ",".join(["%s"] * len(ids_en_abm))
    sql = f"""
        SELECT
            f.id_en_abm,
            f.id_articulo,
            COALESCE(f.cantidad_articulo, 0) AS cantidad_articulo
        FROM en_abm_formula f
        WHERE f.id_en_abm IN ({placeholders})
          AND COALESCE(f.anulado, 'No') <> 'Si'
          AND f.id_articulo IS NOT NULL
          AND f.id_articulo <> 0
          AND COALESCE(f.cantidad_articulo, 0) <> 0
    """
    cursor.execute(sql, ids_en_abm)
    out: Dict[int, List[Dict[str, Any]]] = {}
    for row in cursor.fetchall() or []:
        try:
            id_en = int(float(row[0]))
            id_art = int(float(row[1]))
            cant = float(row[2] or 0)
        except (TypeError, ValueError):
            continue
        out.setdefault(id_en, []).append(
            {"id_articulo": id_art, "cantidad_articulo": cant}
        )
    return out


def _fetch_articulos_meta(cursor, ids_art: List[int]) -> Dict[int, Dict[str, Any]]:
    if not ids_art:
        return {}
    placeholders = ",".join(["%s"] * len(ids_art))
    sql = f"""
        SELECT
            art.IDArt AS id_art,
            COALESCE(art.CodigoArticuloT, CAST(art.CodigoArticulo AS CHAR), '') AS codigo_articulo,
            COALESCE(art.NombreArticulo, '') AS nombre_articulo,
            art.CodigoMarca AS codigo_marca,
            COALESCE(m.NombreMarca, 'Sin marca') AS nombre_marca
        FROM articulo art
        LEFT JOIN marca m ON m.CodMarca = art.CodigoMarca
        WHERE art.IDArt IN ({placeholders})
    """
    cursor.execute(sql, ids_art)
    meta: Dict[int, Dict[str, Any]] = {}
    for row in cursor.fetchall() or []:
        try:
            id_art = int(float(row[0]))
        except (TypeError, ValueError):
            continue
        try:
            codigo_marca = int(float(row[3])) if row[3] is not None else None
        except (TypeError, ValueError):
            codigo_marca = None
        meta[id_art] = {
            "id_art": id_art,
            "codigo_articulo": str(row[1] or ""),
            "nombre_articulo": str(row[2] or ""),
            "codigo_marca": codigo_marca,
            "nombre_marca": str(row[4] or "Sin marca"),
        }
    return meta


def aggregate_bom_from_packs(
    pack_rows: List[Dict[str, Any]],
    bom_by_en_abm: Dict[int, List[Dict[str, Any]]],
) -> Tuple[Dict[int, float], int]:
    """
    Retorna (pares_por_componente, packs_sin_bom_omitidos).
    """
    pares: Dict[int, float] = {}
    omitidos = 0
    for row in pack_rows:
        try:
            id_en = int(float(row.get("id_en_abm") or 0))
            qty = float(row.get("qty_pack") or 0)
        except (TypeError, ValueError):
            continue
        bom = bom_by_en_abm.get(id_en) if id_en else None
        if not bom:
            omitidos += 1
            continue
        exploded = explode_pack_qty_to_components(qty, bom)
        for id_comp, qty_pares in exploded.items():
            pares[id_comp] = pares.get(id_comp, 0.0) + qty_pares
    return pares, omitidos


def build_result_rows(
    pares_por_comp: Dict[int, float],
    meta: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for id_art, pares in pares_por_comp.items():
        if abs(pares) < 1e-9:
            continue
        info = meta.get(id_art) or {
            "id_art": id_art,
            "codigo_articulo": str(id_art),
            "nombre_articulo": f"Artículo {id_art}",
            "codigo_marca": None,
            "nombre_marca": "Sin marca",
        }
        rows.append(
            {
                "id_art": info["id_art"],
                "codigo_articulo": info["codigo_articulo"],
                "nombre_articulo": info["nombre_articulo"],
                "codigo_marca": info.get("codigo_marca"),
                "nombre_marca": info.get("nombre_marca") or "Sin marca",
                "pares": round(float(pares), 4),
                "docenas": docenas_desde_pares(pares),
            }
        )
    rows.sort(key=lambda r: (-abs(r["docenas"]), r["codigo_articulo"] or "", r["nombre_articulo"] or ""))
    return rows


def run_ventas_bom_docenas(report, payload: Dict, user=None, resolve_period_dates=None):
    """
    Ejecuta el informe. `resolve_period_dates` inyectable (firma de QueryRunnerService).
    Retorna QueryResult.
    """
    from datetime import date
    from calendar import monthrange

    from reports.services.query_runner import QueryResult

    filters = dict(payload.get("filters") or {})
    if payload.get("base_empresa") and not filters.get("base_empresa"):
        filters["base_empresa"] = payload["base_empresa"]

    def _default_resolve(f: dict):
        fi = f.get("fecha_inicio") or None
        ff = f.get("fecha_fin") or None
        if fi and ff:
            return fi, ff
        today = date.today()
        if f.get("dia_actual"):
            s = today.strftime("%Y-%m-%d")
            return s, s
        if f.get("año_actual"):
            return date(today.year, 1, 1).strftime("%Y-%m-%d"), date(today.year, 12, 31).strftime("%Y-%m-%d")
        last = monthrange(today.year, today.month)[1]
        return (
            date(today.year, today.month, 1).strftime("%Y-%m-%d"),
            date(today.year, today.month, last).strftime("%Y-%m-%d"),
        )

    resolve = resolve_period_dates or _default_resolve
    fecha_inicio, fecha_fin = _resolve_period(filters, resolve)

    meta = {
        "slug": getattr(report, "slug", VENTAS_BOM_DOCENAS_SLUG),
        "name": getattr(report, "name", "Ventas BOM en docenas"),
        "category": getattr(report, "category", "operational"),
        "version": getattr(report, "version", "1.0.0"),
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
    }

    if not fecha_inicio or not fecha_fin:
        return QueryResult(
            meta=meta,
            data=[],
            totals={"pares": 0.0, "docenas": 0.0, "articulos_bom": 0},
            notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
        )

    base_empresa = _resolve_base_empresa(user, filters)
    if not base_empresa:
        return QueryResult(
            meta=meta,
            data=[],
            totals={"pares": 0.0, "docenas": 0.0, "articulos_bom": 0},
            notes=["No se pudo determinar la base de datos de la empresa."],
        )

    tipos = sql_in_literals(TIPOS_FAC + TIPOS_NC)
    where = [
        "cc.Fecha >= %s",
        "cc.Fecha <= %s",
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
        f"cc.TipoComprobante IN ({tipos})",
    ]
    params: list = [fecha_inicio, fecha_fin]

    puntos_venta = _as_int_list(filters.get("punto_venta") or filters.get("puntos_venta"))
    if puntos_venta:
        ph = ",".join(["%s"] * len(puntos_venta))
        where.append(f"cc.id_pv IN ({ph})")
        params.extend(puntos_venta)

    sucursales = _as_int_list(filters.get("sucursales"))
    if sucursales:
        ph = ",".join(["%s"] * len(sucursales))
        where.append(f"cc.CodSucursal IN ({ph})")
        params.extend(sucursales)

    clientes_excluidos = _as_int_list(filters.get("clientes_excluidos"))
    if clientes_excluidos:
        ph = ",".join(["%s"] * len(clientes_excluidos))
        where.append(f"cc.Codigo NOT IN ({ph})")
        params.extend(clientes_excluidos)

    clientes_incluir = _as_int_list(filters.get("clientes_incluir") or filters.get("clientes_incluidos"))
    if clientes_incluir:
        ph = ",".join(["%s"] * len(clientes_incluir))
        where.append(f"cc.Codigo IN ({ph})")
        params.extend(clientes_incluir)

    marcas_incluidos = _as_int_list(filters.get("marcas_incluidos"))
    if marcas_incluidos:
        ph = ",".join(["%s"] * len(marcas_incluidos))
        where.append(f"art.CodigoMarca IN ({ph})")
        params.extend(marcas_incluidos)

    marcas_excluidos = _as_int_list(filters.get("marcas_excluidos"))
    if marcas_excluidos:
        ph = ",".join(["%s"] * len(marcas_excluidos))
        where.append(f"(art.CodigoMarca IS NULL OR art.CodigoMarca NOT IN ({ph}))")
        params.extend(marcas_excluidos)

    rubros_incluidos = _as_int_list(filters.get("rubros_incluidos"))
    if rubros_incluidos:
        ph = ",".join(["%s"] * len(rubros_incluidos))
        where.append(f"art.CodigoRubro IN ({ph})")
        params.extend(rubros_incluidos)

    rubros_excluidos = _as_int_list(filters.get("rubros_excluidos"))
    if rubros_excluidos:
        ph = ",".join(["%s"] * len(rubros_excluidos))
        where.append(f"(art.CodigoRubro IS NULL OR art.CodigoRubro NOT IN ({ph}))")
        params.extend(rubros_excluidos)

    subrubros_incluidos = _as_int_list(filters.get("subrubros_incluidos"))
    if subrubros_incluidos:
        ph = ",".join(["%s"] * len(subrubros_incluidos))
        where.append(f"art.CodigoSubRubro IN ({ph})")
        params.extend(subrubros_incluidos)

    subrubros_excluidos = _as_int_list(filters.get("subrubros_excluidos"))
    if subrubros_excluidos:
        ph = ",".join(["%s"] * len(subrubros_excluidos))
        where.append(f"(art.CodigoSubRubro IS NULL OR art.CodigoSubRubro NOT IN ({ph}))")
        params.extend(subrubros_excluidos)

    where_clause = " AND ".join(where)
    notes: List[str] = []
    try:
        from datetime import datetime as _dt

        fi_fmt = _dt.strptime(fecha_inicio, "%Y-%m-%d").strftime("%d/%m/%Y")
        ff_fmt = _dt.strptime(fecha_fin, "%Y-%m-%d").strftime("%d/%m/%Y")
        notes.append(f"Período: {fi_fmt} — {ff_fmt}")
    except Exception:
        notes.append(f"Período: {fecha_inicio} — {fecha_fin}")

    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            pack_rows = _fetch_pack_qty_rows(cursor, where_clause, params)
            ids_en = []
            for r in pack_rows:
                try:
                    ids_en.append(int(float(r.get("id_en_abm") or 0)))
                except (TypeError, ValueError):
                    continue
            ids_en = sorted({i for i in ids_en if i > 0})
            bom_map = _fetch_bom_by_en_abm(cursor, ids_en)
            pares, omitidos = aggregate_bom_from_packs(pack_rows, bom_map)
            meta_art = _fetch_articulos_meta(cursor, sorted(pares.keys()))
            data = build_result_rows(pares, meta_art)
    except Exception as exc:
        logger.exception("Error ejecutando ventas-bom-docenas: %s", exc)
        return QueryResult(
            meta=meta,
            data=[],
            totals={"pares": 0.0, "docenas": 0.0, "articulos_bom": 0},
            notes=notes + [f"Error al consultar MySQL: {exc}"],
        )

    if omitidos:
        notes.append(
            f"Se omitieron {omitidos} pack(s) sin filas vigentes en en_abm_formula."
        )

    total_pares = round(sum(r["pares"] for r in data), 4)
    total_docenas = docenas_desde_pares(total_pares)
    totals = {
        "pares": total_pares,
        "docenas": total_docenas,
        "articulos_bom": len(data),
    }
    meta["articulos_bom"] = len(data)
    meta["packs_consultados"] = len(pack_rows)

    return QueryResult(meta=meta, data=data, totals=totals, notes=notes)
