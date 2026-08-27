"""Extractor PD — productos por proveedor."""

from __future__ import annotations

from mtrix.extractors.base import ExportConfig, fetch_all
from core.mysql_pool import mysql_cursor


def _sql(codigo_prov: str) -> tuple[str, list]:
    sql = """
SELECT
    IF(articulo.codartprov IS NOT NULL AND articulo.codartprov <> '',
       CAST(articulo.codartprov AS CHAR(255)), '') AS CODIGO_PRODUTO,
    articulo.NombreArticulo AS DESCRICAO,
    marca.NombreMarca AS DIVISAO_MARCA,
    rubro.NombreRubro AS DIVISAO_RUBRO,
    IF(articulo.NroCodBarraF IS NOT NULL AND articulo.NroCodBarraF <> '',
       CAST(articulo.NroCodBarraF AS CHAR(255)), '0') AS EAN,
    '0' AS TIPO_EMBALAGEM,
    '1' AS TIPO_COD_BARRAS,
    IF(articulo.discontinuo IS NOT NULL, articulo.discontinuo, 'No') AS DISCONTINUO
FROM articulo
LEFT JOIN marca ON (articulo.CodigoMarca = marca.CodMarca)
LEFT JOIN rubro ON (articulo.CodigoRubro = rubro.CodigoRubro)
"""
    params: list = []
    if codigo_prov and codigo_prov != "TODOS":
        sql += " WHERE articulo.CodigoProveedor = %s"
        params.append(int(codigo_prov))
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
