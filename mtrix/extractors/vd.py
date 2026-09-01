"""Extractor VD — ventas; pvnf solo aquí. Agrupación en el serializer."""

from __future__ import annotations

from mtrix.extractors.base import (
    ExportConfig,
    fetch_all,
    normalizar_codigos_prov,
    sql_filtro_proveedor,
)
from core.mysql_pool import mysql_cursor


def _sql(
    cfg: ExportConfig,
    codigo_prov: str = "TODOS",
    codigos_prov: list[str] | None = None,
) -> tuple[str, list]:
    sql = """
SELECT
    IF(cliente.CUIT IS NOT NULL AND cliente.CUIT <> '' AND cliente.CUIT <> '0',
       REPLACE(cliente.CUIT,'-',''), '0') AS COD_CLIENTE,
    cliente.nombre_cliente AS RAZAO_SOCIAL,
    DATE_FORMAT(cuentacliente.Fecha, '%%Y%%m%%d') AS DATA,
    CAST(cuentacliente.NroComprobante AS CHAR(50)) AS NOTA_FISCAL,
    articulo.IDArt AS ID_ART,
    IF(articulo.codartprov IS NOT NULL AND articulo.codartprov <> '',
       CAST(articulo.codartprov AS CHAR(255)), '') AS CODIGO_INTERNO,
    IF(articulo.NroCodBarraF IS NOT NULL AND articulo.NroCodBarraF <> '',
       CAST(articulo.NroCodBarraF AS CHAR(255)), '0') AS EAN,
    stock.Cantidad AS QTDE,
    stock.PrecioVentaxU AS PRECO,
    CAST(cuentacliente.CodViajante AS CHAR(20)) AS VENDEDOR,
    cuentacliente.TipoComprobante AS TIPO_COMP,
    IF(departamento.cod_postal IS NOT NULL AND TRIM(departamento.cod_postal) <> ''
       AND TRIM(departamento.cod_postal) <> '0'
       AND CHAR_LENGTH(TRIM(departamento.cod_postal)) >= 4,
       CAST(departamento.cod_postal AS CHAR(20)), '9400') AS CEP
FROM cuentacliente
RIGHT JOIN stock ON (stock.CodigoMovimiento = cuentacliente.CodigoMovimiento)
LEFT JOIN articulo ON (articulo.IDArt = stock.IDArt)
LEFT JOIN cliente ON (cliente.Codigo = cuentacliente.Codigo)
LEFT JOIN departamento ON (cliente.IDDepartamento = departamento.IDDepartamento)
LEFT JOIN distrito ON (cliente.IDDistrito = distrito.IDDistrito)
LEFT JOIN punto_venta ON (punto_venta.id_punto_venta = cuentacliente.id_pv)
WHERE cuentacliente.Anulado = 'No'
  AND cuentacliente.TipoComprobante <> 'REC'
  AND cuentacliente.Fecha BETWEEN %s AND %s
"""
    params: list = [cfg.fecha_desde, cfg.fecha_hasta]
    filtro, extra = sql_filtro_proveedor(
        normalizar_codigos_prov(codigo_prov=codigo_prov, codigos_prov=codigos_prov)
    )
    if filtro:
        sql += f" AND {filtro}"
        params.extend(extra)
    if not cfg.pvnf:
        sql += " AND punto_venta.cont = 'Si'"
    sql += " ORDER BY cuentacliente.NroComprobante, stock.id_stock"
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
    sql, params = _sql(cfg, codigo_prov=codigo_prov, codigos_prov=codigos_prov)
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([int(limit), int(offset)])
    with mysql_cursor(cfg.base_empresa, dict_cursor=True) as cursor:
        return fetch_all(cursor, sql, params)


def count_rows(
    conn,
    cfg: ExportConfig,
    *,
    codigo_prov: str = "TODOS",
    codigos_prov: list[str] | None = None,
) -> int:
    return len(fetch_rows(conn, cfg, codigo_prov=codigo_prov, codigos_prov=codigos_prov))
