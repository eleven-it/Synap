# -*- coding: utf-8 -*-
"""
Reglas configurables para ingresos de terceros no modelados como Compra/Remito Entrada.

Override en Django settings: ``REPORTS_COMPRAS_TERCEROS_REGLAS`` (lista de dicts).
Documentación: docs/reports/COMPRAS_TERCEROS_DETALLE_MAPPING.md
"""
from __future__ import annotations

from typing import Any, Dict, List

from django.conf import settings

TIPO_COMP_MOV_INTERNO_ENTRADA = "Mov. Interno Entrada"

_DEFAULT_REGLAS: List[Dict[str, Any]] = [
    {
        "id": "selene_import",
        "label": "Selene import (detalle)",
        "match": {"detalle_contains": "INGRESO EXPORTACION SELENE"},
        "deposito_id": 6,
        "require_tipo_comp": TIPO_COMP_MOV_INTERNO_ENTRADA,
    },
    {
        "id": "mys_underwear",
        "label": "MYS UNDERWEAR (detalle movimiento)",
        "match": {"detalle_contains": "MYS UNDERWEAR"},
        "deposito_id": 6,
    },
    {
        "id": "jimmy_buchwald",
        "label": "JIMMY / BUCHWALD (detalle movimiento)",
        "match": {"detalle_contains": "INGRESO DE JIMMY"},
        "deposito_id": 6,
    },
]


def get_compras_terceros_reglas() -> List[Dict[str, Any]]:
    custom = getattr(settings, "REPORTS_COMPRAS_TERCEROS_REGLAS", None)
    if isinstance(custom, list) and custom:
        return list(custom)
    return list(_DEFAULT_REGLAS)
