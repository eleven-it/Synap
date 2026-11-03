# -*- coding: utf-8 -*-
"""
Reglas configurables para ingresos de terceros no modelados como Compra/Remito Entrada.

Se pueden sobreescribir en Django settings con ``REPORTS_COMPRAS_TERCEROS_REGLAS`` (lista de dicts).
Documentación: docs/reports/COMPRAS_TERCEROS_DETALLE_MAPPING.md
"""
from __future__ import annotations

from typing import Any, Dict, List

from django.conf import settings

# Defaults validados contra Excel Compras Ago–Oct 2026 (BestSox).
_DEFAULT_REGLAS: List[Dict[str, Any]] = [
    {
        "id": "selene_import",
        "label": "Selene import (detalle)",
        "match": {"detalle_contains": "INGRESO EXPORTACION SELENE"},
        "deposito_id": 6,
        "tipo_movimiento": "Mov. Interno Entrada",
    },
    {
        "id": "mys_underwear",
        "label": "MYS UNDERWEAR (proveedor 640)",
        "match": {"codigo_proveedor": 640},
        "movimiento_ids": [17219, 17221, 17222, 18677],
        "deposito_id": 6,
    },
    {
        "id": "jimmy_buchwald",
        "label": "JIMMY / BUCHWALD (proveedor 879)",
        "match": {"codigo_proveedor": 879},
        "movimiento_ids": [
            19420,
            19645,
            20085,
            20086,
            21060,
            21061,
            21062,
            21063,
            21064,
            21548,
        ],
        "deposito_id": 6,
    },
]

# Ajustes / internos identificados por detalle (sin proveedor en cabecera).
_DEFAULT_DETALLE_KEYWORDS: List[Dict[str, Any]] = [
    {"keyword": "INGRESO EXPORTACION SELENE", "deposito_id": 6},
]


def get_compras_terceros_reglas() -> List[Dict[str, Any]]:
    custom = getattr(settings, "REPORTS_COMPRAS_TERCEROS_REGLAS", None)
    if isinstance(custom, list) and custom:
        return list(custom)
    return list(_DEFAULT_REGLAS)


def get_compras_detalle_keywords() -> List[Dict[str, Any]]:
    custom = getattr(settings, "REPORTS_COMPRAS_DETALLE_KEYWORDS", None)
    if isinstance(custom, list) and custom:
        return list(custom)
    return list(_DEFAULT_DETALLE_KEYWORDS)
