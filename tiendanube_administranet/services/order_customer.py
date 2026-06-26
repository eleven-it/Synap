"""Resolución de cliente AdministraNET para pedidos Tiendanube."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .sync_service import TiendanubeAdministraNETSyncService

logger = logging.getLogger(__name__)


def resolve_adminet_customer_id(
    sync_service: 'TiendanubeAdministraNETSyncService',
    customer_data: Dict[str, Any],
) -> int:
    """Obtiene ``Codigo`` cliente Adminet desde mapeo TN o sync bajo demanda."""
    from ..models import CustomerMapping

    tn_id = customer_data.get('id')
    if tn_id:
        mapping = CustomerMapping.objects.filter(tiendanube_id=tn_id).first()
        if mapping and mapping.adminet_codigo:
            try:
                return int(mapping.adminet_codigo)
            except (TypeError, ValueError):
                pass
        if mapping and mapping.sync_enabled:
            ok, _msg = sync_service.sync_customer_to_adminet(mapping, force=True)
            if ok and mapping.adminet_codigo:
                mapping.refresh_from_db()
                try:
                    return int(mapping.adminet_codigo)
                except (TypeError, ValueError):
                    pass

    email = (customer_data.get('email') or '').strip()
    if email:
        mapping = CustomerMapping.objects.filter(tiendanube_email__iexact=email).first()
        if mapping and mapping.adminet_codigo:
            try:
                return int(mapping.adminet_codigo)
            except (TypeError, ValueError):
                pass

    logger.warning(
        'Pedido TN sin cliente mapeado (tn_id=%s email=%s); se usa cliente genérico.',
        tn_id,
        email,
    )
    return 1


def enrich_order_from_api(
    sync_service: 'TiendanubeAdministraNETSyncService',
    order_id: int,
    webhook_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Completa datos de pago vía GET /orders/{id} si el webhook viene incompleto."""
    merged = dict(webhook_payload)
    api = sync_service.tiendanube_service.get_order(order_id)
    if api.get('success') and api.get('order'):
        full = api['order']
        for key, value in full.items():
            if value not in (None, '', {}, []):
                merged[key] = value
    return merged
