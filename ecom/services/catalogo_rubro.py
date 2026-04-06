"""
Catálogo rubros / subrubros (paridad mayoristapp relay-rubro.php).

MySQL: mismo patrón que reports — ``core.mysql_pool.get_mysql_pool()`` +
``get_connection(base_empresa)`` + ``cursor.execute(sql, params)``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool

logger = logging.getLogger(__name__)


def _titulo_estilo_php(name: str) -> str:
    """Aproximación a mb_convert_case(..., MB_CASE_TITLE) para etiquetas."""
    if not name:
        return name
    return str(name).strip().title()


def list_rubros_por_categoria(base_empresa: str, id_categoria: int) -> List[Dict[str, Any]]:
    """
    Rubros con artículos ecommerce en la categoría.
    Primera fila sintética ``- todos -`` como el PHP.
    """
    sql = """
        SELECT
            rubro.CodigoRubro AS id,
            rubro.NombreRubro AS name
        FROM articulo
        LEFT JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
        WHERE articulo.ecommerce = 'Si'
          AND rubro.id_categoria = %s
          AND rubro.ecommerce = 'Si'
          AND rubro.anulado = 'No'
        GROUP BY rubro.CodigoRubro, rubro.NombreRubro
        ORDER BY rubro.NombreRubro ASC
    """
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = [{"id": "", "name": "- todos -"}]
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [id_categoria])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            rid = item.get("id")
            item["id"] = "" if rid is None else rid
            nm = item.get("name") or ""
            item["name"] = _titulo_estilo_php(str(nm))
            out.append(item)
    return out


def list_subrubros_por_rubro(base_empresa: str, codigo_rubro: int) -> List[Dict[str, Any]]:
    """Subrubros con artículos para el código de rubro dado (paridad idrubro PHP)."""
    sql = """
        SELECT
            subrubro.IDSubRubro AS id,
            subrubro.NombreSubRubro AS name
        FROM articulo
        LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubRubro
        WHERE subrubro.CodigoRubro = %s
          AND subrubro.anulado = 'No'
        GROUP BY subrubro.IDSubRubro, subrubro.NombreSubRubro
        ORDER BY subrubro.NombreSubRubro ASC
    """
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [codigo_rubro])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            nm = item.get("name") or ""
            item["name"] = _titulo_estilo_php(str(nm))
            out.append(item)
    return out


def list_subrubros_maestro_por_rubro(base_empresa: str, codigo_rubro: int) -> List[Dict[str, Any]]:
    """
    Subrubros del maestro ``subrubro`` (paridad relay-tipo-cliente.php sin ``tipoCliente``).
    """
    sql = """
        SELECT IDSubRubro AS id, NombreSubRubro AS name
        FROM subrubro
        WHERE CodigoRubro = %s
          AND anulado = 'No'
        ORDER BY NombreSubRubro ASC
    """
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [codigo_rubro])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            nm = item.get("name") or ""
            item["name"] = _titulo_estilo_php(str(nm))
            out.append(item)
    return out


def list_subrubros_por_rubro_y_tipo_cliente(
    base_empresa: str, codigo_rubro: int, id_tipo_cliente: int
) -> List[Dict[str, Any]]:
    """
    Subrubros restringidos por ``articulo_tipo_cliente`` (relay-tipo-cliente.php con tipoCliente).
    """
    sql = """
        SELECT
            subrubro.IDSubRubro AS id,
            subrubro.NombreSubRubro AS name
        FROM articulo_tipo_cliente AS atc
        LEFT JOIN articulo ON articulo.IDArt = atc.id_articulo
        LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubRubro
        WHERE subrubro.CodigoRubro = %s
          AND atc.id_tipo_cliente = %s
        GROUP BY subrubro.IDSubRubro, subrubro.NombreSubRubro
        ORDER BY subrubro.NombreSubRubro ASC
    """
    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [codigo_rubro, id_tipo_cliente])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            item = dict(zip(cols, row))
            nm = item.get("name") or ""
            item["name"] = _titulo_estilo_php(str(nm))
            out.append(item)
    return out
