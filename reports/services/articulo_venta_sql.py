# -*- coding: utf-8 -*-
"""Reexporta el filtro ``tipo_art <> Gasto`` (canónico en ``core.utils``)."""
from __future__ import annotations

from core.utils.articulo_tipo_sql import TIPO_ART_GASTO, sql_excluir_tipo_art_gasto

__all__ = ["TIPO_ART_GASTO", "sql_excluir_tipo_art_gasto"]
