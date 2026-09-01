"""Extractor ES — stock. Un archivo por corrida; filtro IN si hay lista."""

from __future__ import annotations

from mtrix.extractors.base import (
    ExportConfig,
    conservar_si_ean_o_venta,
    fetch_all,
    ids_articulos_con_venta,
    normalizar_codigos_prov,
    sql_filtro_proveedor,
)
from core.mysql_pool import mysql_cursor


def _sql(codigo_prov: str = "TODOS", codigos_prov: list[str] | None = None) -> tuple[str, list]:
    sql = """
SELECT
    stock_deposito.id_articulo,
    SUM(stock_deposito.saldo) AS QTDE_TOTAL,
    stock_deposito.id_articulo AS ID_ART,
    MAX(IF(articulo.codartprov IS NOT NULL AND articulo.codartprov <> '',
           CAST(articulo.codartprov AS CHAR(255)), '')) AS CODIGO_INTERNO,
    MAX(IF(articulo.NroCodBarraF IS NOT NULL AND articulo.NroCodBarraF <> '',
           CAST(articulo.NroCodBarraF AS CHAR(255)), '0')) AS EAN
FROM stock_deposito
LEFT JOIN articulo ON (articulo.IDArt = stock_deposito.id_articulo)
WHERE stock_deposito.saldo >= 0
"""
    filtro, params = sql_filtro_proveedor(
        normalizar_codigos_prov(codigo_prov=codigo_prov, codigos_prov=codigos_prov)
    )
    if filtro:
        sql += f" AND {filtro}"
    sql += " GROUP BY stock_deposito.id_articulo"
    return sql, params


def fetch_rows(
    conn,
    cfg: ExportConfig,
    *,
    codigo_prov: str = "TODOS",
    codigos_prov: list[str] | None = None,
    limit=None,
    offset=0,
) -> list[dict]:
    sql, params = _sql(codigo_prov=codigo_prov, codigos_prov=codigos_prov)
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([int(limit), int(offset)])
    with mysql_cursor(cfg.base_empresa, dict_cursor=True) as cursor:
        rows = fetch_all(cursor, sql, params)
    vendidos = ids_articulos_con_venta(cfg, codigo_prov=codigo_prov, codigos_prov=codigos_prov)
    return [r for r in rows if conservar_si_ean_o_venta(r, vendidos)]


def count_rows(
    conn,
    cfg: ExportConfig,
    *,
    codigo_prov: str = "TODOS",
    codigos_prov: list[str] | None = None,
) -> int:
    return len(fetch_rows(conn, cfg, codigo_prov=codigo_prov, codigos_prov=codigos_prov))
