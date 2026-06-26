"""Precios AdministraNET → Tiendanube (finales con IVA, sin desglose)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from core.utils.administranet_types import to_decimal_or_none

# Lista 4 = Web (paridad e-commerce legacy / pantalla Modificar artículo)
LISTA_PRECIO_TN_DEFAULT = 4
FACTOR_IVA_AR_DEFAULT = Decimal('1.21')


def lista_precio_tiendanube_id(config: Any = None) -> int:
    """ID de lista Adminet para publicar en TN (default Lista 4 Web)."""
    if config is not None:
        raw = getattr(config, 'lista_precio_tiendanube_id', None)
        if raw:
            return int(raw)
    return LISTA_PRECIO_TN_DEFAULT


def _campos_lista(articulo: Dict[str, Any], lista_id: int) -> tuple[Optional[Decimal], Optional[Decimal]]:
    idx = int(lista_id)
    if idx < 1 or idx > 5:
        raise ValueError(f'lista_precio inválida: {lista_id}')
    neto = to_decimal_or_none(articulo.get(f'Precio{idx}V'))
    final = to_decimal_or_none(articulo.get(f'Precio{idx}VI'))
    return neto, final


def factor_iva_lista_articulo(
    articulo: Dict[str, Any],
    lista_id: int = LISTA_PRECIO_TN_DEFAULT,
) -> Decimal:
    """Relación precio final / neto de la lista (para costo final)."""
    neto, final = _campos_lista(articulo, lista_id)
    if neto and neto > 0 and final and final > 0:
        return final / neto
    return FACTOR_IVA_AR_DEFAULT


def precio_venta_final_articulo(
    articulo: Dict[str, Any],
    lista_id: int = LISTA_PRECIO_TN_DEFAULT,
) -> float:
    """
    Precio de venta publicable en TN (``variant.price``).

    Usa ``Precio{i}VI`` (precio final con IVA en Adminet). TN no maneja IVA por separado
    (API Product Variant 2025-03: un único campo ``price``).
    """
    neto, final = _campos_lista(articulo, lista_id)
    if final and final > 0:
        return float(final)
    if neto and neto > 0:
        return float(neto * factor_iva_lista_articulo(articulo, lista_id))
    return 0.0


def costo_final_articulo(
    articulo: Dict[str, Any],
    lista_id: int = LISTA_PRECIO_TN_DEFAULT,
) -> float:
    """
    Costo publicable en TN (``variant.cost``): costo neto × factor IVA de la lista.

    Paridad con «Precio de costo bruto → Final» en Modificar artículo (Adminet).
    """
    costo_neto = to_decimal_or_none(articulo.get('PrecioCosto'))
    if not costo_neto or costo_neto <= 0:
        return 0.0
    return float(costo_neto * factor_iva_lista_articulo(articulo, lista_id))


def precios_tiendanube_desde_articulo(
    articulo: Dict[str, Any],
    lista_id: Optional[int] = None,
    config: Any = None,
) -> Dict[str, float]:
    """Devuelve ``price`` y ``cost`` finales para variantes TN."""
    lista = int(lista_id or lista_precio_tiendanube_id(config))
    return {
        'price': precio_venta_final_articulo(articulo, lista),
        'cost': costo_final_articulo(articulo, lista),
    }


def articulo_dict_desde_product_mapping(mapping: Any) -> Dict[str, Any]:
    """Arma un dict tipo ``articulo`` desde campos netos del ``ProductMapping``."""
    articulo: Dict[str, Any] = {}
    if mapping.adminet_precio_costo is not None:
        articulo['PrecioCosto'] = float(mapping.adminet_precio_costo)
    for i in range(1, 6):
        neto = getattr(mapping, f'adminet_precio_{i}v', None)
        if neto is not None:
            articulo[f'Precio{i}V'] = float(neto)
        final = getattr(mapping, f'adminet_precio_{i}vi', None)
        if final is not None:
            articulo[f'Precio{i}VI'] = float(final)
    return articulo


def etiqueta_lista_precio_tn(lista_id: Optional[int] = None, config: Any = None) -> str:
    lista = int(lista_id or lista_precio_tiendanube_id(config))
    nombres = {1: 'Lista 1', 2: 'Lista 2', 3: 'Lista 3', 4: 'Lista 4 Web', 5: 'Lista 5'}
    return nombres.get(lista, f'Lista {lista}')


def precios_finales_desde_product_mapping(
    mapping: Any,
    config: Any = None,
) -> Dict[str, Any]:
    """
    Precio de venta y costo **finales con IVA** para mostrar en UI AdministraNET.

    Usa la misma lista configurada para publicar en Tiendanube (default Lista 4 Web).
    """
    lista = lista_precio_tiendanube_id(config)
    if mapping.adminet_precio_venta_final is not None:
        return {
            'precio_venta': float(mapping.adminet_precio_venta_final),
            'costo': float(mapping.adminet_costo_final or 0),
            'lista_id': lista,
            'lista_label': etiqueta_lista_precio_tn(lista, config),
        }
    precios = precios_tiendanube_desde_articulo(
        articulo_dict_desde_product_mapping(mapping),
        lista_id=lista,
        config=config,
    )
    return {
        'precio_venta': precios['price'],
        'costo': precios['cost'],
        'lista_id': lista,
        'lista_label': etiqueta_lista_precio_tn(lista, config),
    }


def precios_finales_tiendanube_mapping(mapping: Any) -> Dict[str, float]:
    """Montos finales almacenados/consultados para Tiendanube (sin IVA desglosado)."""
    return {
        'precio_venta': float(mapping.tiendanube_price or 0),
        'costo': float(mapping.tiendanube_cost or 0),
    }
