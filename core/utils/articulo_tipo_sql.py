# -*- coding: utf-8 -*-
"""Filtros SQL sobre ``articulo.tipo_art`` (AdministraNET).

Reglas de producto:
- Inventario y la mayoría de reportes de venta: excluyen ``tipo_art = 'Gasto'``
  (nulos / sin artículo en LEFT JOIN se conservan).
- Ventas marcas mensual / licenciatarios (motor VMM): solo ``tipo_art = 'Articulo'``
  (descarta ``Gasto`` y ``Servicio``, p. ej. «Saldo inicial»).
"""
from __future__ import annotations

TIPO_ART_GASTO = "Gasto"
TIPO_ART_SERVICIO = "Servicio"
TIPO_ART_ARTICULO = "Articulo"


def sql_excluir_tipo_art_gasto(alias: str = "art") -> str:
    """Cláusula WHERE que excluye ``tipo_art = 'Gasto'`` con alias de ``articulo``.

    Conserva renglones sin match de artículo (LEFT JOIN) y ``tipo_art`` nulo.
    """
    a = (alias or "art").strip() or "art"
    return (
        f"({a}.IDArt IS NULL OR {a}.tipo_art IS NULL "
        f"OR {a}.tipo_art <> '{TIPO_ART_GASTO}')"
    )


def sql_solo_tipo_art_articulo(alias: str = "art") -> str:
    """Cláusula WHERE: únicamente ``tipo_art = 'Articulo'``.

    Excluye ``Gasto``, ``Servicio`` y nulos / sin match de artículo.
    """
    a = (alias or "art").strip() or "art"
    return f"{a}.tipo_art = '{TIPO_ART_ARTICULO}'"
