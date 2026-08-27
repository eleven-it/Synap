"""Extractor FV — pares únicos cliente-vendedor. Jerarquía plana V.3.5."""

from __future__ import annotations

from mtrix.extractors.base import ExportConfig, fetch_all
from core.mysql_pool import mysql_cursor


_SQL = """
SELECT DISTINCT
    IF(cliente.CUIT IS NOT NULL AND cliente.CUIT <> '' AND cliente.CUIT <> '0',
       REPLACE(cliente.CUIT,'-',''), '0') AS CNPJ_CLIENTE,
    cliente.Codigo AS COD_CLIENTE,
    cliente.nombre_cliente AS RAZAO_SOCIAL,
    CAST(cuentacliente.CodViajante AS CHAR(20)) AS COD_VENDEDOR,
    IF(viajantes.Nombre IS NOT NULL AND viajantes.Nombre <> '',
       viajantes.Nombre, cuentacliente.CodViajante) AS NOME_VENDEDOR,
    '1' AS COD_SUPERVISOR,
    'SUPERVISOR' AS NOME_SUPERVISOR,
    '1' AS COD_GERENTE,
    'GERENTE GENERAL' AS NOME_GERENTE
FROM cuentacliente
INNER JOIN cliente ON (cliente.Codigo = cuentacliente.Codigo)
LEFT JOIN viajantes ON (viajantes.CodViajante = cuentacliente.CodViajante)
WHERE cuentacliente.Anulado = 'No'
  AND cuentacliente.TipoComprobante <> 'REC'
  AND cuentacliente.Fecha BETWEEN %s AND %s
  AND cuentacliente.CodViajante IS NOT NULL
GROUP BY cliente.CUIT, cliente.Codigo, cliente.nombre_cliente,
         cuentacliente.CodViajante, viajantes.Nombre
"""


def fetch_rows(conn, cfg: ExportConfig, *, limit=None, offset=0) -> list[dict]:
    sql = _SQL
    params: list = [cfg.fecha_desde, cfg.fecha_hasta]
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([int(limit), int(offset)])
    with mysql_cursor(cfg.base_empresa, dict_cursor=True) as cursor:
        return fetch_all(cursor, sql, params)


def count_rows(conn, cfg: ExportConfig) -> int:
    return len(fetch_rows(conn, cfg))
