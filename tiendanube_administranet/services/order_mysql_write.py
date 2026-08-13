"""
Normalización MySQL legacy para escritura de pedidos Tienda Nube → AdministraNET.

Usa ``core.utils.administranet_types`` en todos los valores enviados a comp_ped/stockp.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)


def resolve_fecha_entrega(
    shipping_method: Optional[Dict[str, Any]] = None,
    *,
    now: Optional[datetime] = None,
) -> Optional[str]:
    """
    Resuelve ``FechaEntrega`` / ``Vencimiento`` (DATE nullable).

    - Sin ``estimated_delivery_date`` → default +7 días (ISO YYYY-MM-DD).
    - Fecha estimada inválida → ``None`` (NULL en MySQL).
    """
    shipping_method = shipping_method or {}
    raw = shipping_method.get('estimated_delivery_date')
    if raw is not None and str(raw).strip() != '':
        text = str(raw).strip()
        try:
            if 'T' in text:
                dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
                return to_date_or_none(dt)
            dt = datetime.strptime(text[:10], '%Y-%m-%d')
            return to_date_or_none(dt)
        except (TypeError, ValueError):
            return None
    base = now or datetime.now()
    return to_date_or_none(base + timedelta(days=7))


def _decimal_amount(value: Any, *, default: str = '0') -> Decimal:
    return to_decimal_or_none(value) or Decimal(default)


def normalize_comp_ped_params(
    *,
    nro_comprobante: str,
    codigo_movimiento: int,
    estado_pedido: str,
    cliente_id: Any,
    total: Any,
    importe_letras: str,
    subtotal: Any,
    subtotal_sin_iva: Any,
    iva_21: Any,
    discount: Any,
    subtotal_menos_desc: Any,
    id_condventa: Any,
    cond_venta: str,
    cod_viajante: Any,
    user_id: Any,
    sucursal_id: Any,
    deposito_id: Any,
    fecha_entrega: Optional[str],
    forma_entrega: str,
    carrier: Any,
    tiendanube_order_id: Any,
    ped_eco_number: Any,
    info_ped_eco: str,
    estado_pago_ecom: str,
    tipo_pedido: str,
    punto_venta_id: Any,
) -> Tuple[Any, ...]:
    """Tupla de parámetros INSERT comp_ped con tipos AdministraNET."""
    zero = Decimal('0')
    alicuota_21 = Decimal('21')
    return (
        nro_comprobante,
        codigo_movimiento,
        str_or_default(estado_pedido, 'En preparación'),
        to_int_or_none(cliente_id) or 1,
        _decimal_amount(total),
        str_or_default(importe_letras, '-'),
        _decimal_amount(subtotal),
        _decimal_amount(subtotal_sin_iva),
        zero,
        _decimal_amount(iva_21),
        zero,
        alicuota_21,
        zero,
        zero,
        _decimal_amount(discount),
        _decimal_amount(discount),
        zero,
        zero,
        _decimal_amount(subtotal_menos_desc),
        to_int_or_none(id_condventa) or 1,
        str_or_default(cond_venta, 'Contado'),
        to_int_or_none(cod_viajante),
        to_int_or_none(user_id) or 1,
        to_int_or_none(sucursal_id) or 1,
        to_int_or_none(deposito_id) or 1,
        to_date_or_none(fecha_entrega),
        str_or_default(forma_entrega, '-'),
        str_or_default(carrier, '-'),
        str_or_default(tiendanube_order_id, '-'),
        to_int_or_none(ped_eco_number),
        info_ped_eco,
        str_or_default(estado_pago_ecom, 'No'),
        to_date_or_none(fecha_entrega),
        str_or_default(tipo_pedido, 'Ecom cliente'),
        to_int_or_none(punto_venta_id) or 1,
    )


def normalize_stockp_line_params(
    *,
    product: Dict[str, Any],
    codigo_movimiento: int,
    deposito_id: Any,
    sucursal_id: Any,
    cod_viajante: Any,
    nro_comprobante: str,
    orden: int,
) -> Tuple[Any, ...]:
    """Tupla de parámetros INSERT stockp con tipos AdministraNET."""
    cantidad = _decimal_amount(product.get('quantity', 1), default='1')
    precio_unitario = _decimal_amount(product.get('price', 0))
    precio_total = cantidad * precio_unitario
    iva_producto = precio_unitario * Decimal('0.21') / Decimal('1.21')
    precio_sin_iva = precio_unitario - iva_producto
    precio_total_sin_iva = precio_total - (iva_producto * cantidad)
    id_art = to_int_or_none(product.get('adminet_product_id')) or 0
    zero = Decimal('0')
    alicuota_21 = Decimal('21')

    return (
        str_or_default(product.get('sku'), '-'),
        str_or_default(product.get('name'), '-'),
        cantidad,
        cantidad,
        cantidad,
        precio_unitario,
        precio_sin_iva,
        precio_sin_iva,
        precio_unitario,
        iva_producto,
        alicuota_21,
        zero,
        zero,
        precio_total,
        precio_total_sin_iva,
        precio_total_sin_iva,
        precio_total,
        iva_producto * cantidad,
        codigo_movimiento,
        to_int_or_none(deposito_id) or 1,
        id_art,
        cantidad,
        cantidad,
        orden,
        to_int_or_none(sucursal_id) or 1,
        to_int_or_none(cod_viajante),
        nro_comprobante,
        'PED',
    )
