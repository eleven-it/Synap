"""Extractor CI — clientes con ventas en el período."""

from __future__ import annotations

from mtrix.extractors.base import ExportConfig, fetch_all
from core.mysql_pool import mysql_cursor


_SQL = """
SELECT
    IF(cliente.CUIT IS NOT NULL AND cliente.CUIT <> '' AND cliente.CUIT <> '0',
       REPLACE(cliente.CUIT,'-',''), '0') AS CNPJ_CLIENTE,
    cliente.Codigo AS COD_CLIENTE,
    cliente.nombre_cliente AS RAZAO_SOCIAL,
    IF(cliente.Calle IS NOT NULL, cliente.Calle, 'NA') AS ENDERECO,
    IF(distrito.NombreDistrito IS NOT NULL, distrito.NombreDistrito, 'NA') AS BAIRRO,
    IF(departamento.cod_postal IS NOT NULL AND TRIM(departamento.cod_postal) <> '',
       CAST(departamento.cod_postal AS CHAR(20)), '0') AS CEP,
    IF(departamento.NombreDepartamento IS NOT NULL, departamento.NombreDepartamento, 'NA') AS CIUDAD,
    IF(provincia.Provincia IS NOT NULL, provincia.Provincia, 'NA') AS ESTADO,
    'NA' AS NOME_RESPONSAVEL,
    IF(cliente.telefono IS NOT NULL AND cliente.telefono <> '',
       CAST(cliente.telefono AS CHAR(50)), '') AS TELEFONE,
    'RUTA' AS ROTA,
    IF(tipo_cliente.NombreTipoCliente IS NOT NULL, tipo_cliente.NombreTipoCliente, 'Tienda') AS TIPO_LOJ,
    FORMAT(ROUND(IFNULL(SUM(CASE
        WHEN cc.TipoComprobante LIKE 'F%%' AND cc.Anulado = 'No' THEN cc.ImporteVenta
        WHEN cc.TipoComprobante LIKE 'N%%' AND cc.Anulado = 'No' THEN -cc.ImporteVenta
        ELSE 0 END) * 100.0 / (
            SELECT SUM(CASE
                WHEN TipoComprobante LIKE 'F%%' AND Anulado = 'No' THEN ImporteVenta
                WHEN TipoComprobante LIKE 'N%%' AND Anulado = 'No' THEN -ImporteVenta
                ELSE 0 END)
            FROM cuentacliente
            WHERE TipoComprobante IN ('FA','FB','FC','NCA','NCB','NDA','NDB')
              AND Anulado = 'No'
              AND Fecha BETWEEN %s AND %s
        ), 0), 2), 2, 'de_DE') AS REPRESENTATIVIDADE
FROM cliente
LEFT JOIN distrito ON (cliente.IDDistrito = distrito.IDDistrito)
LEFT JOIN departamento ON (cliente.IDDepartamento = departamento.IDDepartamento)
LEFT JOIN provincia ON (cliente.CodProvincia = provincia.CodProvincia)
LEFT JOIN tipo_cliente ON (cliente.TipoCliente = tipo_cliente.IDTipoCliente)
LEFT JOIN cuentacliente cc ON (
    cliente.Codigo = cc.Codigo
    AND cc.TipoComprobante IN ('FA','FB','FC','NCA','NCB','NDA','NDB')
    AND cc.Anulado = 'No'
    AND cc.Fecha BETWEEN %s AND %s
)
WHERE 1=1
AND cc.Codigo IS NOT NULL
GROUP BY cliente.Codigo, cliente.CUIT, cliente.nombre_cliente, cliente.Calle,
         distrito.NombreDistrito, distrito.cod_postal, departamento.cod_postal,
         departamento.NombreDepartamento, provincia.Provincia, cliente.telefono,
         tipo_cliente.NombreTipoCliente
"""


def fetch_rows(conn, cfg: ExportConfig, *, limit=None, offset=0) -> list[dict]:
    sql = _SQL
    params = [cfg.fecha_desde, cfg.fecha_hasta, cfg.fecha_desde, cfg.fecha_hasta]
    if limit is not None:
        sql += " LIMIT %s OFFSET %s"
        params.extend([int(limit), int(offset)])
    with mysql_cursor(cfg.base_empresa, dict_cursor=True) as cursor:
        return fetch_all(cursor, sql, params)


def count_rows(conn, cfg: ExportConfig) -> int:
    rows = fetch_rows(conn, cfg)
    return len(rows)
