"""Búsqueda de proveedores AdministraNET para el buscador Mtrix."""

from __future__ import annotations

from typing import Any

from core.mysql_pool import mysql_cursor
from core.services.administranet_compras import buscar_proveedores
from core.utils.administranet_types import str_or_default, to_int_or_none
from mtrix.extractors.base import parse_proveedores


def _fila_publica(row: dict[str, Any]) -> dict[str, Any]:
    codigo = to_int_or_none(row.get("Codigo") or row.get("codigo"))
    return {
        "codigo": codigo,
        "nombre": str_or_default(row.get("Nombre") or row.get("nombre"), ""),
        "cuit": str_or_default(row.get("CUIT") or row.get("cuit"), ""),
    }


def buscar_proveedores_mtrix(base_empresa: str, q: str, *, limite: int = 15) -> list[dict[str, Any]]:
    filas = buscar_proveedores(base_empresa, q, limite=limite)
    return [_fila_publica(r) for r in filas if to_int_or_none(r.get("Codigo")) is not None]


def obtener_proveedores_por_codigos(base_empresa: str, codigos: list[str]) -> list[dict[str, Any]]:
    ints: list[int] = []
    for codigo in codigos:
        numero = to_int_or_none(codigo)
        if numero is not None and numero not in ints:
            ints.append(numero)
    if not ints:
        return []
    placeholders = ", ".join(["%s"] * len(ints))
    sql = f"""
SELECT p.Codigo, COALESCE(p.Nombre, '') AS Nombre, COALESCE(p.CUIT, '') AS CUIT
FROM proveedor p
WHERE p.Codigo IN ({placeholders})
ORDER BY p.Nombre
"""
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        cursor.execute(sql, ints)
        rows = cursor.fetchall() or []
    return [_fila_publica(dict(r)) for r in rows]


def proveedores_seleccionados_config(base_empresa: str, texto: str) -> list[dict[str, Any]]:
    parsed = parse_proveedores(texto)
    if parsed == ["TODOS"]:
        return []
    return obtener_proveedores_por_codigos(base_empresa, parsed)
