# -*- coding: utf-8 -*-
"""
Reglas configurables para ingresos de terceros no modelados como Compra/Remito Entrada.

Override en Django settings: ``REPORTS_COMPRAS_TERCEROS_REGLAS`` (lista de dicts).
Documentación: docs/reports/COMPRAS_TERCEROS_DETALLE_MAPPING.md

Las reglas son por **proveedor** o **texto en detalle** (+ depósito / TipoComp opcional),
no por listas fijas de IDs de movimiento (codigo_movimiento no es estable).
"""
from __future__ import annotations

from typing import Any, Dict, List

from django.conf import settings

TIPO_COMP_MOV_INTERNO_ENTRADA = "Mov. Interno Entrada"

# Defaults validados contra Excel Compras Ago–Oct 2026 (BestSox).
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
        "label": "MYS UNDERWEAR (proveedor 640)",
        "match": {"codigo_proveedor": 640},
        "deposito_id": 6,
    },
    {
        "id": "jimmy_buchwald",
        "label": "JIMMY / BUCHWALD (proveedor 879)",
        "match": {"codigo_proveedor": 879},
        "deposito_id": 6,
    },
]


def get_compras_terceros_reglas() -> List[Dict[str, Any]]:
    custom = getattr(settings, "REPORTS_COMPRAS_TERCEROS_REGLAS", None)
    if isinstance(custom, list) and custom:
        return list(custom)
    return list(_DEFAULT_REGLAS)
