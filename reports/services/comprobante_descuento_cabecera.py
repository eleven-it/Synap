# -*- coding: utf-8 -*-
"""
Factor de descuento al pie de factura (cabecera cuentacliente).

Compartido entre Ventas marcas mensual (VMM) e informe DABRA consolidado remitos.
Las líneas de ``stock`` guardan precios pre-pie; el descuento vive en cabecera
(``SubTotal1``, ``SubtotalDesc`` derivado de ``PorDesc1``/``ImpDesc1``).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.utils.administranet_types import to_decimal_or_none

# Tolerancia para evitar división por cero cuando SubTotal1 es 0 o residual.
_EPSILON_SUBTOTAL1 = Decimal("0.0001")


def _dec(value: Any) -> Decimal:
    d = to_decimal_or_none(value)
    return d if d is not None else Decimal("0")


def factor_descuento_cabecera(subtotal1: Any, subtotal_desc: Any) -> Decimal:
    """
    Factor de descuento de cabecera FA.

    Las líneas de ``stock`` guardan precios predescuento; ``SubTotal1`` es la
    suma neta predescuento y ``SubtotalDesc`` el neto ya descontado. El IVA de
    cabecera se recalcula sobre la base descontada, así que el bruto comparable
    a ``ImporteVenta`` es Σ bruto líneas × (SubtotalDesc / SubTotal1).

    ``SubTotal1==0`` → ``Decimal("1")``; ``SubtotalDesc is None`` → factor 1.
    """
    cab_neto = _dec(subtotal1)
    if cab_neto == 0:
        return Decimal("1")
    cab_neto_desc = to_decimal_or_none(subtotal_desc)
    if cab_neto_desc is None:
        cab_neto_desc = cab_neto
    return cab_neto_desc / cab_neto


def porcentaje_descuento_cabecera(subtotal1: Any, subtotal_desc: Any) -> Decimal:
    """
    % de descuento al pie de FA: (SubTotal1 − SubtotalDesc) / SubTotal1 × 100.

    Cubre PorDesc1/ImpDesc1 (y PorDesc2) sin depender solo del porcentaje
    cargado: si el descuento se cargó como importe, el ratio sigue siendo correcto.
    """
    factor = factor_descuento_cabecera(subtotal1, subtotal_desc)
    return (Decimal("1") - factor) * Decimal("100")


def sql_factor_descuento_cabecera_expr(
    subtotal1_col: str = "cc.SubTotal1",
    subtotal_desc_col: str = "cc.SubtotalDesc",
) -> str:
    """
    Expresión SQL escalar del factor de descuento al pie por fila.

    Usa ε=0.0001 para evitar división por cero cuando ``SubTotal1`` es 0 o
    residual; ``SubtotalDesc`` nulo se trata como ``SubTotal1`` (sin descuento).
    """
    return f"""
        CASE
            WHEN ABS(COALESCE({subtotal1_col}, 0)) < 0.0001 THEN 1
            ELSE COALESCE({subtotal_desc_col}, {subtotal1_col}) / {subtotal1_col}
        END
    """.strip()
