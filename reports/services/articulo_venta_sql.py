# -*- coding: utf-8 -*-
"""Reexporta filtros ``tipo_art`` (canónico en ``core.utils``)."""
from __future__ import annotations

from core.utils.articulo_tipo_sql import (
    TIPO_ART_ARTICULO,
    TIPO_ART_GASTO,
    TIPO_ART_SERVICIO,
    sql_excluir_tipo_art_gasto,
    sql_solo_tipo_art_articulo,
)

__all__ = [
    "TIPO_ART_ARTICULO",
    "TIPO_ART_GASTO",
    "TIPO_ART_SERVICIO",
    "sql_excluir_tipo_art_gasto",
    "sql_solo_tipo_art_articulo",
]
