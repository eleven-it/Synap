"""Extractor ES — stock por proveedor."""

from __future__ import annotations

from mtrix.extractors.base import ExportConfig, fetch_all
from core.mysql_pool import mysql_cursor


def _sql(codigo_prov: str) -> tuple[str, list]:
    sql = """
SELECT
    stock_deposito.id_articulo,
    SUM(stock_deposito.saldo) AS QTDE_TOTAL,
    MAX(IF(articulo.NroCodBarraF IS NOT NULL AND articulo.NroCodBarraF <> '',
           CAST(articulo.NroCodBarraF AS CHAR(255)), '0')) AS EAN
FROM stock_deposito
LEFT JOIN articulo ON (articulo.IDArt = stock_deposito.id_articulo)
WHERE stock_deposito.saldo >= 0
"""
    params: list = []
    if codigo_prov and codigo_prov != "TODOS":
        sql += " AND articulo.CodigoProveedor = %s"
        params.append(int(codigo_prov))
    sql += " GROUP BY stock_deposito.id_articulo"
    return sql, params


def fetch_rows(conn, cfg: ExportConfig, *, codigo_prov: str = "TODOS", limit=None, offset=0) -> list[dict]:
    sql, params = _sql(codigo_prov)
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([int(limit), int(offset)])
    with mysql_cursor(cfg.base_empresa, dict_cursor=True) as cursor:
        return fetch_all(cursor, sql, params)


def count_rows(conn, cfg: ExportConfig, *, codigo_prov: str = "TODOS") -> int:
    return len(fetch_rows(conn, cfg, codigo_prov=codigo_prov))
