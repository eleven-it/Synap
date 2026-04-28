"""
Catálogos y lectura cliente rápido (paridad ``relay-cliente-rapido.php`` — acciones de lectura).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none

from ecom.services.cliente_geo_relay import list_provincias


def tipo_cliente_dict(base_empresa: str) -> Dict[int, str]:
    sql = """
        SELECT tc.IDTipoCliente AS id, tc.NombreTipoCliente AS nombre
        FROM tipo_cliente AS tc
        WHERE tc.Anulado = 'No'
        ORDER BY tc.NombreTipoCliente ASC
    """
    return _id_nombre_map(base_empresa, sql, [])


def tipo_iva_dict(base_empresa: str) -> Dict[int, str]:
    sql = """
        SELECT c.IDIva AS id, c.Abreviado AS nombre
        FROM contribuyentes AS c
        ORDER BY c.IDIva ASC
    """
    return _id_nombre_map(base_empresa, sql, [])


def inicio_payload(base_empresa: str) -> Dict[str, Any]:
    return {
        "tipoCliente": tipo_cliente_dict(base_empresa),
        "ivaCliente": tipo_iva_dict(base_empresa),
        "provincia": list_provincias(base_empresa, None),
    }


def obtiene_cliente_fila(base_empresa: str, codigo: int) -> Optional[Dict[str, Any]]:
    """Paridad ``obtiene_cliente`` (PHP vacío): una fila ``cliente`` por código."""
    cod = to_int_or_none(codigo)
    if cod is None:
        return None
    sql = """
        SELECT *
        FROM cliente
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [cod])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        row = cursor.fetchone()
        if not row:
            return None
        item = dict(zip(cols, row))
        return _json_safe(item)


def _id_nombre_map(base_empresa: str, sql: str, params: List[Any]) -> Dict[int, str]:
    pool = get_mysql_pool()
    out: Dict[int, str] = {}
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            i, nombre = row[0], row[1]
            n = to_int_or_none(i)
            if n is not None and nombre is not None:
                out[n] = str(nombre)
    return out


def _json_safe(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat() if hasattr(v, "isoformat") else str(v)
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item
