# -*- coding: utf-8 -*-
"""
Reglas compartidas del informe Ventas BOM en docenas.

Fuente de verdad para tipos de comprobante, signos y divisor de docenas de planta.
"""
from __future__ import annotations

from typing import Tuple

TIPOS_FAC: Tuple[str, ...] = ("FA", "FB", "FC", "FE", "FM")
TIPOS_NC: Tuple[str, ...] = ("NCA", "NCB", "NCC", "NCE", "NCM")
STOCK_TIPO_COMP: Tuple[str, ...] = ("Venta", "Venta TPV", "Devol - Cliente", "ND Anul NC")

# Docenas de pares en planta (fabricados / componentes). No usar factor comercial P1–P6.
UNIDADES_POR_DOCENA = 12.0

VENTAS_BOM_DOCENAS_SLUG = "ventas-bom-docenas"


def sql_in_literals(values: Tuple[str, ...]) -> str:
    return ",".join(f"'{v}'" for v in values)


def sql_signo_qty_expr(cantidad_alias: str = "COALESCE(st.Cantidad, 0)") -> str:
    fac = sql_in_literals(TIPOS_FAC)
    nc = sql_in_literals(TIPOS_NC)
    return f"""
        CASE
            WHEN cc.TipoComprobante IN ({fac}) THEN {cantidad_alias}
            WHEN cc.TipoComprobante IN ({nc}) THEN -({cantidad_alias})
            ELSE 0
        END
    """


def docenas_desde_pares(pares: float) -> float:
    """Convierte pares a docenas con 2 decimales."""
    try:
        p = float(pares or 0)
    except (TypeError, ValueError):
        p = 0.0
    return round(p / UNIDADES_POR_DOCENA, 2)


def explode_pack_qty_to_components(
    qty_pack_firmada: float,
    componentes: list,
) -> dict:
    """
    Explota cantidad firmada de packs a pares por id_articulo componente.

    componentes: iterable de dicts con id_articulo y cantidad_articulo.
    Retorna {id_art_comp: pares}.
    """
    agregado: dict = {}
    try:
        qty = float(qty_pack_firmada or 0)
    except (TypeError, ValueError):
        qty = 0.0
    if not qty or not componentes:
        return agregado
    for comp in componentes:
        try:
            id_comp = int(float(comp.get("id_articulo") or 0))
        except (TypeError, ValueError):
            continue
        if id_comp <= 0:
            continue
        try:
            cant = float(comp.get("cantidad_articulo") or 0)
        except (TypeError, ValueError):
            cant = 0.0
        if cant == 0:
            continue
        agregado[id_comp] = agregado.get(id_comp, 0.0) + (qty * cant)
    return agregado
