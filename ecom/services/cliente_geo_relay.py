"""
Catálogo geográfico y zonas (paridad funciones en ``relay-cliente-domicilio.php`` / ``relay-cliente-rapido.php``).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none


def list_provincias(base_empresa: str, id_pais: Optional[int] = None) -> Dict[int, str]:
    where = "p.Anulado = 'No'"
    params: List[Any] = []
    if id_pais is not None:
        where += " AND p.id_pais = %s"
        params.append(id_pais)
    sql = f"""
        SELECT p.CodProvincia AS codigo, p.Provincia AS provincia
        FROM provincia AS p
        WHERE {where}
        ORDER BY p.Provincia ASC
    """
    return _map_codigo_nombre(base_empresa, sql, params)


def list_departamentos(base_empresa: str, id_provincia: Optional[int] = None) -> Dict[int, str]:
    where = "dp.Anulado = 'No'"
    params: List[Any] = []
    if id_provincia is not None:
        where += " AND dp.CodProvincia = %s"
        params.append(id_provincia)
    sql = f"""
        SELECT dp.IDDepartamento AS codigo, dp.NombreDepartamento AS depto
        FROM departamento AS dp
        WHERE {where}
        ORDER BY dp.NombreDepartamento ASC
    """
    return _map_codigo_nombre(base_empresa, sql, params)


def list_distritos(base_empresa: str, id_departamento: Optional[int] = None) -> Dict[int, str]:
    where = "d.Anulado = 'No'"
    params: List[Any] = []
    if id_departamento is not None:
        where += " AND d.IDDepartamento = %s"
        params.append(id_departamento)
    sql = f"""
        SELECT d.IDDistrito AS codigo, d.NombreDistrito AS distrito
        FROM distrito AS d
        WHERE {where}
        ORDER BY d.NombreDistrito ASC
    """
    return _map_codigo_nombre(base_empresa, sql, params)


def list_zonas_erp(base_empresa: str, cod_provincia: Optional[int] = None) -> Dict[int, str]:
    where = "z.anulado = 'No'"
    params: List[Any] = []
    if cod_provincia is not None:
        where += " AND z.codprovincia = %s"
        params.append(cod_provincia)
    sql = f"""
        SELECT z.id_zona AS codigo, z.nombre_zona AS zona
        FROM erp_zona AS z
        WHERE {where}
        ORDER BY z.id_zona ASC
    """
    return _map_codigo_nombre(base_empresa, sql, params)


def _map_codigo_nombre(base_empresa: str, sql: str, params: List[Any]) -> Dict[int, str]:
    pool = get_mysql_pool()
    out: Dict[int, str] = {}
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            cod, nombre = row[0], row[1]
            n = to_int_or_none(cod)
            if n is not None and nombre is not None:
                out[n] = str(nombre)
    return out
