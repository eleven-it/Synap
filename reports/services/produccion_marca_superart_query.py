# -*- coding: utf-8 -*-
"""Consultas read-only Producción por marca (MPR + fasón)."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from reports.services.bestsox_query_dates import parse_filter_date

from mpr.reportes_transicion_lote_sql import normalizar_meses_yyyy_mm
from mpr.services import TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, mysql_cursor
from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.compras_terceros_config import TIPO_COMP_MOV_INTERNO_ENTRADA
from reports.services.compras_terceros_sql import sql_marca_join, _marca_filter_sql

logger = logging.getLogger(__name__)

FASON_DEPOSITO_SEMI = 3


def fetch_produccion_mpr_filas(
    cursor,
    meses_yyyy_mm: Sequence[str],
    *,
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    meses = normalizar_meses_yyyy_mm(meses_yyyy_mm)
    if not meses:
        return []
    ph_meses = ",".join(["%s"] * len(meses))
    params: List[Any] = [TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, *meses]
    marca_sql = _marca_filter_sql(marcas_ids, marcas_excluidos_ids, params)
    gasto_sql = sql_excluir_tipo_art_gasto("a")
    cursor.execute(
        f"""
        SELECT t.id_articulo,
               COALESCE(a.id_manual, '') AS id_manual,
               COALESCE(a.CodigoMarca, 0) AS codigo_marca,
               COALESCE(m.NombreMarca, '') AS nombre_marca,
               COALESCE(a.IDArt, t.id_articulo) AS codigo_articulo,
               COALESCE(a.NombreArticulo, '') AS nombre_articulo,
               DATE_FORMAT(t.creado_en, '%%Y-%%m') AS ym,
               COALESCE(SUM(t.cantidad), 0) AS cantidad,
               'produccion' AS fuente
        FROM mpr_transicion_lote t
        INNER JOIN articulo a ON a.IDArt = t.id_articulo
        {sql_marca_join()}
        WHERE t.tipo_origen = %s
          AND t.tipo_destino = %s
          AND DATE_FORMAT(t.creado_en, '%%Y-%%m') IN ({ph_meses})
          AND {gasto_sql}
          {marca_sql}
        GROUP BY t.id_articulo, COALESCE(a.id_manual, ''), ym,
                 COALESCE(a.CodigoMarca, 0), COALESCE(m.NombreMarca, ''),
                 COALESCE(a.NombreArticulo, '')
        """,
        params,
    )
    return _rows_as_dicts(cursor)


def fetch_produccion_fason_filas(
    cursor,
    *,
    desde: date,
    hasta: date,
    marcas_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    params: List[Any] = [
        TIPO_COMP_MOV_INTERNO_ENTRADA,
        FASON_DEPOSITO_SEMI,
        desde.isoformat(),
        hasta.isoformat(),
    ]
    marca_sql = _marca_filter_sql(marcas_ids, marcas_excluidos_ids, params)
    gasto_sql = sql_excluir_tipo_art_gasto("a")
    cursor.execute(
        f"""
        SELECT s.IDArt AS id_articulo,
               COALESCE(a.id_manual, '') AS id_manual,
               COALESCE(a.CodigoMarca, 0) AS codigo_marca,
               COALESCE(m.NombreMarca, '') AS nombre_marca,
               COALESCE(a.IDArt, s.IDArt) AS codigo_articulo,
               COALESCE(a.NombreArticulo, '') AS nombre_articulo,
               DATE_FORMAT(ms.Fecha, '%%Y-%%m') AS ym,
               COALESCE(SUM(s.Cantidad), 0) AS cantidad,
               'fason' AS fuente
        FROM stock s
        INNER JOIN movimiento_stock ms ON ms.codigo_movimiento = s.CodigoMovimiento
        INNER JOIN articulo a ON a.IDArt = s.IDArt
        {sql_marca_join()}
        WHERE s.TipoComp = %s
          AND s.CodDeposito = %s
          AND IFNULL(s.Anulado, 'No') = 'No'
          AND IFNULL(ms.anulado, 'No') = 'No'
          AND ms.Fecha >= %s AND ms.Fecha < DATE_ADD(%s, INTERVAL 1 DAY)
          AND (
                UPPER(COALESCE(ms.detalle, '')) LIKE '%%TEJEDURIA S%%'
             OR UPPER(COALESCE(ms.detalle, '')) LIKE '%%TEJEDURIA M%%'
             OR UPPER(COALESCE(ms.detalle, '')) LIKE '%%TEJEDURÍA S%%'
             OR UPPER(COALESCE(ms.detalle, '')) LIKE '%%TEJEDURÍA M%%'
             OR UPPER(COALESCE(ms.detalle, '')) LIKE '%%FABRICA S Y M%%'
          )
          AND {gasto_sql}
          {marca_sql}
        GROUP BY s.IDArt, COALESCE(a.id_manual, ''), ym,
                 COALESCE(a.CodigoMarca, 0), COALESCE(m.NombreMarca, ''),
                 COALESCE(a.NombreArticulo, '')
        """,
        params,
    )
    return _rows_as_dicts(cursor)


def _rows_as_dicts(cursor) -> List[Dict[str, Any]]:
    rows = cursor.fetchall() or []
    if rows and not isinstance(rows[0], dict):
        cols = [d[0] for d in cursor.description] if cursor.description else []
        return [dict(zip(cols, r)) for r in rows]
    return list(rows)


def consultar_produccion_marca_superart(
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
    meses_norm = normalizar_meses_yyyy_mm(meses)
    desde = parse_filter_date(desde_iso)
    hasta = parse_filter_date(hasta_iso)
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        mpr = fetch_produccion_mpr_filas(
            cursor,
            meses_norm,
            marcas_ids=marcas_incluidos,
            marcas_excluidos_ids=marcas_excluidos,
        )
        fason: List[Dict[str, Any]] = []
        if desde and hasta:
            fason = fetch_produccion_fason_filas(
                cursor,
                desde=desde,
                hasta=hasta,
                marcas_ids=marcas_incluidos,
                marcas_excluidos_ids=marcas_excluidos,
            )
    return mpr + fason
