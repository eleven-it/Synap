"""Stock publicable Tiendanube: artículo × depósito configurado (unidades enteras)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from core.utils.administranet_types import to_int_or_none


def stock_unidades_articulo_deposito(
    adminet_product: Dict[str, Any],
    deposito_id: Optional[int],
) -> int:
    """
    Unidades disponibles de un artículo en el depósito Tiendanube.

    Disponible = ``saldo - saldo_pedido_cliente`` del depósito TN
    (campo ``stock_deposito`` / ``stock_pedido_cliente`` en listados con JOIN).
    Tiendanube opera a nivel artículo por unidades, siempre bajo el depósito definido.
    """
    dep = to_int_or_none(deposito_id)
    if dep is None or dep <= 0:
        raise ValueError(
            'Se requiere deposito_tiendanube_id para calcular stock hacia Tiendanube.'
        )
    raw = adminet_product.get('stock_deposito')
    if raw is None and 'stock_deposito' not in adminet_product:
        raw = 0
    saldo = to_int_or_none(raw)
    if saldo is None:
        try:
            saldo = int(Decimal(str(raw or 0)))
        except (ArithmeticError, ValueError):
            saldo = 0

    reserva_raw = adminet_product.get('stock_pedido_cliente')
    if reserva_raw is None:
        reserva_raw = adminet_product.get('saldo_pedido_cliente', 0)
    reserva = to_int_or_none(reserva_raw)
    if reserva is None:
        try:
            reserva = int(Decimal(str(reserva_raw or 0)))
        except (ArithmeticError, ValueError):
            reserva = 0

    return max(0, saldo - reserva)
