"""Medidas Stock UM + Docenas para inventario por depósito (paridad Excel BEST)."""
from __future__ import annotations

from typing import Any

from core.utils.administranet_types import to_decimal_or_none

from mpr.services import divisor_docena_pack

_TIPOS_PIPELINE = frozenset({"Produccion", "SemiElaborado"})


def divisor_docena_inventario(tipo_mpr: str, cantidad_promedio_bulto: Any) -> tuple[int, str]:
    """Divisor docenas y etiqueta UM nativa según etapa MPR del depósito."""
    if (tipo_mpr or "").strip() in _TIPOS_PIPELINE:
        return 12, "pares"
    return divisor_docena_pack(cantidad_promedio_bulto), "packs"


def medidas_inventario_excel(
    stock: Any,
    tipo_mpr: str,
    cantidad_promedio_bulto: Any,
) -> dict[str, Any]:
    """Stock en UM nativa y docenas float (no división entera doc+resto)."""
    divisor, um = divisor_docena_inventario(tipo_mpr, cantidad_promedio_bulto)
    stock_n = float(to_decimal_or_none(stock) or 0)
    docenas = round(stock_n / divisor, 2) if divisor else 0.0
    return {
        "stock_um": stock_n,
        "um_etiqueta": um,
        "docenas": docenas,
        "divisor": divisor,
    }
