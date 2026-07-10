"""
Etiquetas legibles de promoción para UI de catálogo y carrito.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none


def etiqueta_promocion_linea(row: Dict[str, Any]) -> str:
    """Texto corto para mostrar bajo el artículo cuando tiene promo vigente."""
    promo = str(row.get("promocion") or row.get("en_promocion") or "").strip().lower()
    if promo not in ("si", "sí", "true", "1") and not row.get("en_promocion"):
        return ""
    tipo = str(row.get("promocion_tipo") or "").strip()
    por = to_decimal_or_none(row.get("promocion_por"))
    cant = to_int_or_none(row.get("promocion_cant"))
    partes = []
    if tipo:
        partes.append(tipo)
    if por is not None and por > 0:
        if tipo.lower() == "monto fijo":
            partes.append(f"${por:.2f}")
        else:
            partes.append(f"{por:.0f}%")
    if cant is not None and cant > 1:
        partes.append(f"mín. {cant} u.")
    return " · ".join(partes) if partes else "Promoción vigente"


def enriquecer_item_promocion(item: Dict[str, Any]) -> Dict[str, Any]:
    """Añade ``promocion_etiqueta`` si corresponde."""
    if item.get("en_promocion") or str(item.get("promocion") or "").strip().lower() in ("si", "sí"):
        item["promocion_etiqueta"] = etiqueta_promocion_linea(item)
    else:
        item["promocion_etiqueta"] = ""
    return item
