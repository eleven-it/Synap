"""Unidad de empaquetado de venta (múltiplo mínimo) para pedidos masivos."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional, Sequence, Set

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none


def multiplo_empaque_venta(multiplo_cantidad_vta: Any) -> int:
    """Devuelve el múltiplo mínimo de empaque desde ``multiplo_cantidad_vta`` (>0; else 1).

    No usa ``multiplo_vta``: la unidad de empaquetado operativa es solo
    ``articulo.multiplo_cantidad_vta``.
    """
    mc = to_int_or_none(multiplo_cantidad_vta) or 0
    if mc > 0:
        return mc
    return 1


def cantidad_respeta_multiplo(cantidad: Any, multiplo: int) -> bool:
    """True si cantidad es 0/vacía o múltiplo entero de ``multiplo`` (>0)."""
    m = to_int_or_none(multiplo) or 1
    if m <= 1:
        return True
    qty = to_decimal_or_none(cantidad)
    if qty is None or qty <= 0:
        return True
    try:
        return qty % Decimal(m) == 0
    except Exception:
        return False


def disponible_unidades_a_packs(disponible: Any, multiplo_cantidad_vta: Any) -> float:
    """Convierte unidades base disponibles a packs según ``multiplo_cantidad_vta``."""
    disp = to_decimal_or_none(disponible) or Decimal("0")
    if disp <= 0:
        return 0.0
    mult = Decimal(multiplo_empaque_venta(multiplo_cantidad_vta))
    packs = disp / mult
    return float(packs.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def campos_multiplo_articulo(multiplo_cantidad_vta: Any) -> Dict[str, int]:
    """Campos expuestos al FE a partir de ``multiplo_cantidad_vta`` legacy."""
    mc = to_int_or_none(multiplo_cantidad_vta) or 0
    me = multiplo_empaque_venta(mc)
    return {
        "multiplo_cantidad_vta": mc,
        "multiplo_empaque": me,
    }


def mensaje_multiplo_invalido(multiplo: int) -> str:
    return f"La cantidad debe ser múltiplo de la unidad de empaquetado ({int(multiplo)})."


def infracciones_multiplo_celdas(
    celdas: Sequence[Any],
    multiplos_por_articulo: Dict[int, Dict[str, Any]],
    *,
    nombres: Optional[Dict[int, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Lista infracciones (celdas con qty>0 que no respetan el múltiplo)."""
    nombres = nombres or {}
    out: List[Dict[str, Any]] = []
    vistos: Set[tuple] = set()
    for celda in celdas:
        qty = to_decimal_or_none(getattr(celda, "cantidad_packs", None))
        if qty is None or qty <= 0:
            continue
        id_art = int(getattr(celda, "id_articulo", 0) or 0)
        id_dom = int(getattr(celda, "id_cliente_domicilio", 0) or 0)
        info = multiplos_por_articulo.get(id_art) or {}
        multiplo = int(info.get("multiplo_empaque") or 1)
        if cantidad_respeta_multiplo(qty, multiplo):
            continue
        key = (id_art, id_dom)
        if key in vistos:
            continue
        vistos.add(key)
        nom = nombres.get(id_art) or {}
        out.append(
            {
                "id_articulo": id_art,
                "id_cliente_domicilio": id_dom,
                "codigo": nom.get("codigo", ""),
                "cantidad": float(qty),
                "multiplo_empaque": multiplo,
            }
        )
    return out
