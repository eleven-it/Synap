# -*- coding: utf-8 -*-
"""Consultas read-only Compras terminados por marca."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.administranet_types import to_date_or_none

from mpr.reportes_transicion_lote_sql import normalizar_meses_yyyy_mm
from mpr.services import mysql_cursor
from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.articulo_pack_unidades import (
    docenas_desde_prendas,
    prendas_desde_packs,
    unidades_por_pack_compras,
)
from reports.services.compras_terceros_sql import (
    fetch_all_compras_reglas_extra_filas,
    sql_exclude_stock_matching_terceros_reglas,
    sql_marca_join,
    _finished_product_sql,
    _marca_filter_sql,
)

logger = logging.getLogger(__name__)

ARTICULO_MERCADERIAS_GENERICO = 1805


def fetch_compras_standard_filas(
    cursor,
    *,
    desde: date,
    hasta: date,
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    hasta_excl = hasta + timedelta(days=1)
    params: List[Any] = [desde.isoformat(), hasta_excl.isoformat(), ARTICULO_MERCADERIAS_GENERICO]
    marca_sql = _marca_filter_sql(marcas_ids, marcas_excluidos_ids, params)
    gasto_sql = sql_excluir_tipo_art_gasto("a")
    finished_sql = _finished_product_sql("a")
    exclude_reglas_sql = sql_exclude_stock_matching_terceros_reglas(params)
    cursor.execute(
        f"""
        SELECT s.id_stock,
               s.IDArt AS id_articulo,
               COALESCE(a.id_manual, '') AS id_manual,
               COALESCE(a.CodigoMarca, 0) AS codigo_marca,
               COALESCE(m.NombreMarca, '') AS nombre_marca,
               COALESCE(a.IDArt, s.IDArt) AS codigo_articulo,
               COALESCE(a.NombreArticulo, '') AS nombre_articulo,
               COALESCE(um.nombre_unimed, '') AS nombre_unimed,
               DATE_FORMAT(cp.Fecha, '%%Y-%%m') AS ym,
               COALESCE(s.Cantidad, 0) AS packs
        FROM stock s
        INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = s.CodigoMovimiento
        INNER JOIN articulo a ON a.IDArt = s.IDArt
        {sql_marca_join()}
        LEFT JOIN unidmed um ON um.id_unimed = a.id_unimed
        WHERE IFNULL(s.Anulado, 'No') = 'No'
          AND IFNULL(cp.Anulado, 'No') = 'No'
          AND cp.Fecha >= %s AND cp.Fecha < %s
          AND s.Tipo = 'Proveedor'
          AND (
                (s.TipoComp = 'Compra' AND cp.TipoComprobante IN ('FA','FC','FM'))
             OR (s.TipoComp = 'Remito Entrada' AND cp.TipoComprobante = 'REM')
          )
          AND NOT (a.IDArt = %s AND ABS(COALESCE(s.Cantidad, 0) - 1) < 0.0001
                   AND cp.TipoComprobante IN ('FA','FC','FM'))
          AND {finished_sql}
          AND {gasto_sql}
          {exclude_reglas_sql}
          {marca_sql}
        """,
        params,
    )
    return _rows_as_dicts(cursor)


def _expand_stock_lines(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        packs = float(row.get("packs") or 0)
        if abs(packs) < 1e-9:
            continue
        upp = unidades_por_pack_compras(
            row.get("nombre_unimed"),
            nombre_articulo=row.get("nombre_articulo"),
            id_manual=row.get("id_manual"),
        )
        prendas = prendas_desde_packs(packs, upp)
        out.append(
            {
                **row,
                "cantidad": packs,
                "packs": packs,
                "prendas": prendas,
                "docenas": docenas_desde_prendas(prendas),
            }
        )
    return out


def _dedupe_compras_filas(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Una sola línea por id_stock (primera fuente gana; estándar va antes que reglas extra)."""
    seen: Dict[Any, Dict[str, Any]] = {}
    orden: List[Any] = []
    for row in filas or []:
        sid = row.get("id_stock")
        key = sid if sid is not None else (
            row.get("regla_id"),
            row.get("id_articulo"),
            row.get("ym"),
            row.get("packs"),
        )
        if key in seen:
            continue
        seen[key] = row
        orden.append(key)
    return [seen[k] for k in orden]


def _aggregate_compras_por_articulo_mes(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for row in filas or []:
        key = (
            row.get("id_articulo"),
            str(row.get("ym") or ""),
            row.get("id_manual"),
            row.get("codigo_marca"),
            row.get("nombre_marca"),
            row.get("nombre_articulo"),
            row.get("nombre_unimed"),
        )
        if key not in buckets:
            buckets[key] = {**row, "packs": 0.0, "prendas": 0.0, "docenas": 0.0, "cantidad": 0.0}
            buckets[key].pop("id_stock", None)
        acc = buckets[key]
        for field in ("packs", "prendas", "docenas", "cantidad"):
            acc[field] = round(float(acc.get(field) or 0) + float(row.get(field) or 0), 4)
    return list(buckets.values())


def _rows_as_dicts(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall() or []
    if rows and not isinstance(rows[0], dict):
        cols = [d[0] for d in cursor.description] if cursor.description else []
        return [dict(zip(cols, r)) for r in rows]
    return list(rows)


def consultar_compras_marca_superart(
    base_empresa: str,
    *,
    meses: Sequence[str],
    marcas_incluidos: Optional[Sequence[int]] = None,
    marcas_excluidos: Optional[Sequence[int]] = None,
    desde_iso: Optional[str] = None,
    hasta_iso: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not (base_empresa or "").strip():
        return []
    desde = to_date_or_none(desde_iso)
    hasta = to_date_or_none(hasta_iso)
    if not desde or not hasta:
        return []
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        std = fetch_compras_standard_filas(
            cursor,
            desde=desde,
            hasta=hasta,
            marcas_ids=marcas_incluidos,
            marcas_excluidos_ids=marcas_excluidos,
        )
        extra = fetch_all_compras_reglas_extra_filas(
            cursor,
            desde=desde,
            hasta=hasta,
            marcas_ids=marcas_incluidos,
            marcas_excluidos_ids=marcas_excluidos,
        )
    expanded = _expand_stock_lines(_dedupe_compras_filas(std + extra))
    combined = _aggregate_compras_por_articulo_mes(expanded)
    meses_set = set(normalizar_meses_yyyy_mm(meses))
    if meses_set:
        combined = [r for r in combined if str(r.get("ym") or "") in meses_set]
    return combined
