"""
Maestros de catálogo ecommerce (paridad relay-marca / relay-laboratorio / relay-proveedor).

MySQL legacy vía ``core.mysql_pool``; mismos criterios que ``catalogo_rubro`` (artículos ``ecommerce = 'Si'``).
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool

from ecom.services.catalogo_rubro import _titulo_estilo_php


def list_marcas_catalogo_ecommerce(base_empresa: str) -> List[Dict[str, Any]]:
    """
    Marcas con al menos un artículo ecommerce activo y marca no anulada con flag ecommerce.
    """
    sql = """
        SELECT
            marca.CodMarca AS id,
            marca.NombreMarca AS name
        FROM articulo
        INNER JOIN marca ON marca.CodMarca = articulo.CodigoMarca
        WHERE articulo.ecommerce = 'Si'
          AND marca.anulado = 'No'
          AND marca.ecommerce = 'Si'
        GROUP BY marca.CodMarca, marca.NombreMarca
        ORDER BY marca.NombreMarca ASC
    """
    return _fetch_id_name_rows(base_empresa, sql, [])


def list_laboratorios_catalogo_ecommerce(base_empresa: str) -> List[Dict[str, Any]]:
    """Laboratorios con al menos un artículo ecommerce y laboratorio no anulado."""
    sql = """
        SELECT
            laboratorio.CodLaboratorio AS id,
            laboratorio.NombreLaboratorio AS name
        FROM articulo
        INNER JOIN laboratorio ON laboratorio.CodLaboratorio = articulo.CodLaboratorio
        WHERE articulo.ecommerce = 'Si'
          AND laboratorio.anulado = 'No'
        GROUP BY laboratorio.CodLaboratorio, laboratorio.NombreLaboratorio
        ORDER BY laboratorio.NombreLaboratorio ASC
    """
    return _fetch_id_name_rows(base_empresa, sql, [])


def list_proveedores_catalogo_ecommerce(base_empresa: str) -> List[Dict[str, Any]]:
    """
    Proveedores con al menos un artículo ecommerce.
    Excluye ``Codigo = 1`` (convención AdministraNET “ninguno” / placeholder).
    """
    sql = """
        SELECT
            proveedor.Codigo AS id,
            proveedor.Nombre AS name
        FROM articulo
        INNER JOIN proveedor ON proveedor.Codigo = articulo.CodigoProveedor
        WHERE articulo.ecommerce = 'Si'
          AND proveedor.Codigo <> 1
        GROUP BY proveedor.Codigo, proveedor.Nombre
        ORDER BY proveedor.Nombre ASC
    """
    return _fetch_id_name_rows(base_empresa, sql, [])


def _fetch_id_name_rows(base_empresa: str, sql: str, params: list) -> List[Dict[str, Any]]:
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            nm = item.get("name") or ""
            item["name"] = _titulo_estilo_php(str(nm))
            out.append(item)
    return out
