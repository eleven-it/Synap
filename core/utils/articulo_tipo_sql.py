# -*- coding: utf-8 -*-
"""Filtros SQL sobre ``articulo.tipo_art`` (AdministraNET).

Regla de producto: en reportes de artículos de venta y en la consulta de
inventario por etapa (``/stock/inventario/``, ``/mpr/inventario/``) se excluye
``articulo.tipo_art = 'Gasto'``. Valores nulos o renglones sin artículo
(LEFT JOIN) se conservan: no son Gasto.
"""
from __future__ import annotations

TIPO_ART_GASTO = "Gasto"


def sql_excluir_tipo_art_gasto(alias: str = "art") -> str:
    """Cláusula WHERE que excluye ``tipo_art = 'Gasto'`` con alias de ``articulo``.

    Conserva renglones sin match de artículo (LEFT JOIN) y ``tipo_art`` nulo.
    """
    a = (alias or "art").strip() or "art"
    return (
        f"({a}.IDArt IS NULL OR {a}.tipo_art IS NULL "
        f"OR {a}.tipo_art <> '{TIPO_ART_GASTO}')"
    )
