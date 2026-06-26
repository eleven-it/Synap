"""Extracción de campos publicables desde respuestas de producto Tiendanube (API 2025-03)."""

from __future__ import annotations

from typing import Any, Dict, Optional


def _texto_localizado_tiendanube(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get('es') or next(iter(value.values()), ''))
    return str(value or '')


def _nombre_producto_tiendanube(tn_product: Dict[str, Any]) -> str:
    return _texto_localizado_tiendanube(tn_product.get('name', ''))[:255]


def _handle_producto_tiendanube(tn_product: Dict[str, Any]) -> str:
    return _texto_localizado_tiendanube(tn_product.get('handle', ''))[:255]


def _stock_variante_tiendanube(variant: Dict[str, Any]) -> int:
    stock = variant.get('stock')
    if stock is not None:
        try:
            return max(0, int(stock))
        except (TypeError, ValueError):
            pass
    levels = variant.get('inventory_levels') or []
    if levels:
        try:
            return max(0, int(levels[0].get('stock', 0)))
        except (TypeError, ValueError):
            return 0
    return 0


def variante_principal_tiendanube(tn_product: Dict[str, Any]) -> Dict[str, Any]:
    variants = tn_product.get('variants') or []
    return variants[0] if variants else {}


def resolver_campos_producto_tiendanube(tn_product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza producto TN para persistir en ``ProductMapping``.

    Precio, costo, stock y SKU viven en la **variante**, no en la raíz del producto.
    """
    variant = variante_principal_tiendanube(tn_product)
    description = _texto_localizado_tiendanube(tn_product.get('description', ''))

    return {
        'tiendanube_name': _nombre_producto_tiendanube(tn_product),
        'tiendanube_handle': _handle_producto_tiendanube(tn_product),
        'tiendanube_description': description,
        'tiendanube_sku': str(variant.get('sku') or ''),
        'tiendanube_price': float(variant['price']) if variant.get('price') is not None else None,
        'tiendanube_compare_at_price': (
            float(variant['compare_at_price'])
            if variant.get('compare_at_price') is not None
            else None
        ),
        'tiendanube_cost': float(variant['cost']) if variant.get('cost') is not None else None,
        'tiendanube_stock': _stock_variante_tiendanube(variant),
        'tiendanube_weight': float(variant.get('weight') or tn_product.get('weight') or 0),
        'tiendanube_width': float(variant.get('width') or tn_product.get('width') or 0),
        'tiendanube_height': float(variant.get('height') or tn_product.get('height') or 0),
        'tiendanube_depth': float(variant.get('depth') or tn_product.get('depth') or 0),
        'tiendanube_free_shipping': bool(tn_product.get('free_shipping', False)),
        'tiendanube_published': bool(tn_product.get('published', True)),
        'tiendanube_featured': bool(tn_product.get('featured', False)),
        'tiendanube_product_type': str(tn_product.get('product_type') or 'physical'),
        'tiendanube_brand': str(tn_product.get('brand') or ''),
        'tiendanube_categories': tn_product.get('categories') or [],
        'tiendanube_tags': tn_product.get('tags') or [],
        'tiendanube_images': tn_product.get('images') or [],
        'tiendanube_videos': tn_product.get('videos') or [],
        'tiendanube_seo_title': str(tn_product.get('seo_title') or ''),
        'tiendanube_seo_description': str(tn_product.get('seo_description') or ''),
        'tiendanube_created_at': tn_product.get('created_at'),
        'tiendanube_updated_at': tn_product.get('updated_at'),
    }


def aplicar_campos_producto_tiendanube(
    mapping: Any,
    tn_product: Dict[str, Any],
    *,
    variant: Optional[Dict[str, Any]] = None,
) -> None:
    """Aplica campos resueltos al modelo ``ProductMapping`` (sin guardar)."""
    campos = resolver_campos_producto_tiendanube(tn_product)
    if variant:
        if variant.get('price') is not None:
            campos['tiendanube_price'] = float(variant['price'])
        if variant.get('cost') is not None:
            campos['tiendanube_cost'] = float(variant['cost'])
        if variant.get('sku'):
            campos['tiendanube_sku'] = str(variant['sku'])
        campos['tiendanube_stock'] = _stock_variante_tiendanube(variant)
    for field, value in campos.items():
        if value is not None:
            setattr(mapping, field, value)
