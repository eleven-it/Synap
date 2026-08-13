"""Push inmediato de stock Adminet → Tiendanube tras movimiento en depósito TN."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING

from .product_stock import stock_unidades_articulo_deposito

if TYPE_CHECKING:
    from .sync_service import TiendanubeAdministraNETSyncService

logger = logging.getLogger(__name__)


def push_stock_for_article_ids(
    sync_service: 'TiendanubeAdministraNETSyncService',
    article_ids: Iterable[int],
    deposito_id: Optional[int],
    *,
    enqueue_on_failure: bool = True,
) -> Dict[str, Any]:
    """
    Publica stock disponible (saldo − reservas) de artículos afectados en TN.

    Idempotente por lectura actual de ``stock_deposito`` post-movimiento.
    """
    dep = int(deposito_id or 0)
    if dep <= 0:
        return {'success': False, 'message': 'Depósito TN no configurado.', 'pushed': 0}

    from ..models import ProductMapping, ProductVariantMapping

    pending: List[dict] = []
    for id_art in {int(a) for a in article_ids if a}:
        mapping = ProductMapping.objects.filter(adminet_id=id_art).first()
        if not mapping or not mapping.tiendanube_id or not mapping.sync_stock:
            continue

        stock_row = sync_service.adminet_service.get_stock_by_deposito(id_art, dep)
        if not stock_row.get('success'):
            continue

        disponible = stock_unidades_articulo_deposito(
            {
                'stock_deposito': stock_row.get('stock', 0),
                'stock_pedido_cliente': stock_row.get('stock_pedido_cliente', 0),
            },
            deposito_id=dep,
        )

        variant = ProductVariantMapping.objects.filter(
            product_mapping=mapping,
            tiendanube_variant_id__isnull=False,
        ).first()
        if not variant:
            continue
        variant_id = variant.tiendanube_variant_id

        pending.append({
            'product_id': mapping.tiendanube_id,
            'variant_id': variant_id,
            'stock': disponible,
            'mapping': mapping,
        })

    if not pending:
        return {'success': True, 'message': 'Sin variantes TN para actualizar.', 'pushed': 0}

    payload = sync_service._build_stock_price_patch_payload(pending)
    result = sync_service.product_service.patch_products_stock_price(payload)
    pushed = 0
    if result.get('success'):
        for item in pending:
            mapping = item['mapping']
            mapping.tiendanube_stock = item['stock']
            mapping.sync_status = ProductMapping.SyncStatus.SYNCED
            mapping.save(update_fields=['tiendanube_stock', 'sync_status', 'updated_at'])
            pushed += 1
    else:
        logger.error('Push stock TN falló: %s', result.get('message'))
        status_code = result.get('status_code')
        from .sync_errors import should_retry_webhook_failure
        from .outbox_service import enqueue_stock_push_outbox

        if should_retry_webhook_failure(http_status=status_code) and enqueue_on_failure:
            enqueue_stock_push_outbox(
                tiendanube_config=sync_service.tiendanube_config,
                adminet_config=sync_service.adminet_config,
                article_ids=list(article_ids),
                deposito_id=dep,
            )

    return {
        'success': bool(result.get('success')),
        'message': result.get('message', ''),
        'pushed': pushed,
        'errors': 0 if result.get('success') else len(pending),
        'status_code': result.get('status_code'),
    }
