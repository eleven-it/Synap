"""Vincular manualmente productos Tiendanube ↔ AdministraNET (mapeo operativo)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.utils import timezone

from ..models import ProductMapping, ProductVariantMapping
from .adminet_service import AdministraNETService
from .automatic_mapping_service import AutomaticMappingService
from .product_stock import stock_unidades_articulo_deposito
from .tiendanube_service import TiendanubeService

logger = logging.getLogger(__name__)


def link_tiendanube_product_to_adminet(
    *,
    tiendanube_config,
    adminet_config,
    tiendanube_product_id: int,
    tiendanube_variant_id: int,
    adminet_id: int,
    base_empresa: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Crea o actualiza ``ProductMapping`` + ``ProductVariantMapping`` y persiste
    ``articulo.id_tiendanube`` en MySQL legacy.
    """
    tn_service = TiendanubeService(tiendanube_config)
    adminet = AdministraNETService(
        adminet_config,
        base_empresa=base_empresa or adminet_config.database,
    )
    deposito_id = adminet_config.deposito_tiendanube_id
    if not deposito_id:
        return {'success': False, 'message': 'Configure deposito_tiendanube_id.'}

    tn_result = tn_service.get_product(tiendanube_product_id)
    if not tn_result.get('success'):
        return {
            'success': False,
            'message': tn_result.get('message', 'No se pudo leer producto TN'),
        }
    tn_product = tn_result['product']
    variant = None
    for v in tn_product.get('variants') or []:
        if int(v.get('id') or 0) == int(tiendanube_variant_id):
            variant = v
            break
    if not variant:
        return {
            'success': False,
            'message': f'Variante TN {tiendanube_variant_id} no encontrada en producto {tiendanube_product_id}',
        }

    stock_row = adminet.get_stock_by_deposito(adminet_id, deposito_id)
    adminet_row = adminet.execute_query(
        'SELECT IDArt, NombreArticulo, CodigoArticulo, NroCodBarra, '
        'PrecioCosto, Precio1V, Precio2V, Precio3V, Precio4V, Precio5V, '
        'Precio1VI, Precio2VI, Precio3VI, Precio4VI, Precio5VI, ecommerce '
        'FROM articulo WHERE IDArt = %s LIMIT 1',
        (adminet_id,),
    )
    if not adminet_row.get('results'):
        return {'success': False, 'message': f'Artículo Adminet {adminet_id} inexistente.'}
    adminet_product = adminet_row['results'][0]
    adminet_product['stock_deposito'] = stock_row.get('stock', 0)
    adminet_product['stock_pedido_cliente'] = stock_row.get('stock_pedido_cliente', 0)

    tn_name = tn_product.get('name')
    if isinstance(tn_name, dict):
        tn_name = tn_name.get('es') or next(iter(tn_name.values()), '')

    mapping, created = ProductMapping.objects.update_or_create(
        tiendanube_id=tiendanube_product_id,
        defaults={
            'adminet_id': adminet_id,
            'tiendanube_name': str(tn_name)[:255],
            'tiendanube_sku': variant.get('sku') or '',
            'tiendanube_price': variant.get('price') or 0,
            'tiendanube_stock': variant.get('stock') or 0,
            'sync_enabled': True,
            'sync_stock': True,
            'sync_price': True,
            'sync_status': ProductMapping.SyncStatus.SYNCED,
            'last_synced': timezone.now(),
            'error_message': '',
        },
    )

    disponible = stock_unidades_articulo_deposito(adminet_product, deposito_id)
    mapping.adminet_nombre = adminet_product.get('NombreArticulo', '')
    mapping.adminet_codigo_barra = adminet_product.get('NroCodBarra', '')
    mapping.adminet_stock = disponible
    mapping.save()

    ProductVariantMapping.objects.update_or_create(
        product_mapping=mapping,
        defaults={
            'tiendanube_variant_id': tiendanube_variant_id,
            'tiendanube_sku': variant.get('sku') or '',
            'tiendanube_price': variant.get('price'),
            'tiendanube_stock': variant.get('stock', 0),
            'adminet_id': adminet_id,
            'adminet_nombre': adminet_product.get('NombreArticulo', ''),
            'sync_enabled': True,
            'sync_stock': True,
            'sync_status': ProductVariantMapping.SyncStatus.SYNCED,
        },
    )

    id_tn_result = adminet.update_product_tiendanube_id(adminet_id, tiendanube_product_id)
    if not id_tn_result.get('success'):
        logger.warning('No se actualizó articulo.id_tiendanube: %s', id_tn_result.get('message'))

    mapper = AutomaticMappingService()
    mapper.update_product_mapping_from_adminet(mapping, adminet_product, deposito_id=deposito_id)

    return {
        'success': True,
        'created': created,
        'mapping_id': mapping.id,
        'tiendanube_product_id': tiendanube_product_id,
        'tiendanube_variant_id': tiendanube_variant_id,
        'adminet_id': adminet_id,
        'disponible_deposito_tn': disponible,
        'message': (
            f'Vinculado TN {tiendanube_product_id} ↔ Adminet {adminet_id} '
            f'(disponible depósito TN: {disponible})'
        ),
    }


def link_products_from_tiendanube_order(
    *,
    tiendanube_config,
    adminet_config,
    order_id: int,
    adminet_ids: list[int],
    base_empresa: Optional[str] = None,
) -> Dict[str, Any]:
    """Vincula líneas de una orden TN con artículos Adminet (mismo orden)."""
    tn_service = TiendanubeService(tiendanube_config)
    order_result = tn_service.get_order(order_id)
    if not order_result.get('success'):
        return order_result

    lines = order_result['order'].get('products') or []
    if not lines:
        return {'success': False, 'message': 'La orden TN no tiene líneas de producto.'}
    if len(adminet_ids) < len(lines):
        return {
            'success': False,
            'message': (
                f'Se requieren {len(lines)} adminet_id(s); recibidos {len(adminet_ids)}.'
            ),
        }

    results = []
    for line, adminet_id in zip(lines, adminet_ids):
        pid = line.get('product_id')
        vid = line.get('variant_id')
        if not pid or not vid:
            results.append({'success': False, 'line': line, 'message': 'Sin product_id/variant_id'})
            continue
        results.append(
            link_tiendanube_product_to_adminet(
                tiendanube_config=tiendanube_config,
                adminet_config=adminet_config,
                tiendanube_product_id=int(pid),
                tiendanube_variant_id=int(vid),
                adminet_id=int(adminet_id),
                base_empresa=base_empresa,
            )
        )

    ok = sum(1 for r in results if r.get('success'))
    return {
        'success': ok == len(results),
        'linked': ok,
        'total': len(results),
        'results': results,
    }
