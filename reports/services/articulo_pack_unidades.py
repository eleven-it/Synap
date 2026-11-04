# -*- coding: utf-8 -*-
"""Conversión pack → prendas/pares y docenas para informes BestSox (solo lectura)."""
from __future__ import annotations

import re
from typing import Any, Optional

from core.utils.administranet_types import str_or_default

# Compras / consignación terminados: unidades por pack según U.M. (notas Excel Compras).
UNIDADES_POR_PACK_COMPRAS_UM = {
    "P1": 1.0,
    "P2": 2.0,
    "P3": 3.0,
    "P6": 6.0,
}

_PACK_SUFFIX_RE = re.compile(r"(\d+)\s*[UP]\s*$", re.IGNORECASE)


def unidades_por_pack_compras(
    nombre_unimed: Any = "",
    *,
    nombre_articulo: Any = "",
    id_manual: Any = "",
) -> float:
    """
    Unidades (prendas) por pack en compras/consignación terminados.

    P1=1, P2=2, P3=3, P6=6; si la U.M. es genérica, busca sufijo 1U/2U/3P en nombre o id_manual.
    """
    um = str_or_default(nombre_unimed, "").strip().upper()
    if um in UNIDADES_POR_PACK_COMPRAS_UM:
        return UNIDADES_POR_PACK_COMPRAS_UM[um]
    for text in (nombre_articulo, id_manual):
        raw = str_or_default(text, "").strip()
        if not raw:
            continue
        match = _PACK_SUFFIX_RE.search(raw)
        if match:
            try:
                return float(int(match.group(1)))
            except (TypeError, ValueError):
                continue
    return 1.0


def prendas_desde_packs(packs: float, unidades_por_pack: float) -> float:
    try:
        p = float(packs or 0)
        u = float(unidades_por_pack or 1)
    except (TypeError, ValueError):
        return 0.0
    return round(p * u, 4)


def docenas_desde_prendas(prendas: float) -> float:
    try:
        v = float(prendas or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(v / 12.0, 4)


def docenas_desde_pares(pares: float) -> float:
    return docenas_desde_prendas(pares)
