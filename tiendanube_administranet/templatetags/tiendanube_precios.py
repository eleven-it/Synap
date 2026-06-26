"""Filtros de plantilla — precios finales AdministraNET / Tiendanube."""

from functools import lru_cache

from django import template

from ..services.product_pricing import (
    precios_finales_desde_product_mapping,
    precios_finales_tiendanube_mapping,
)

register = template.Library()


@lru_cache(maxsize=1)
def _adminet_config_activa():
    from ..models import AdministraNETConfig

    return AdministraNETConfig.objects.filter(is_active=True).first()


def _precios_adminet(mapping):
    return precios_finales_desde_product_mapping(
        mapping,
        config=_adminet_config_activa(),
    )


@register.filter
def adminet_precio_venta_final(mapping):
    return _precios_adminet(mapping)['precio_venta']


@register.filter
def adminet_costo_final(mapping):
    return _precios_adminet(mapping)['costo']


@register.filter
def adminet_lista_precio_label(mapping):
    return _precios_adminet(mapping)['lista_label']


@register.filter
def tn_precio_venta_final(mapping):
    return precios_finales_tiendanube_mapping(mapping)['precio_venta']


@register.filter
def tn_costo_final(mapping):
    return precios_finales_tiendanube_mapping(mapping)['costo']
