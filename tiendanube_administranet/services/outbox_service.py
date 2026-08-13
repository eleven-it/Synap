"""Outbox saliente Adminet → Tienda Nube (stock push, catch-up pedidos)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from django.utils import timezone

from ..models import (
    AdministraNETConfig,
    TiendanubeConfig,
    TiendanubeOutboxEvent,
)
from .order_stock_push import push_stock_for_article_ids
from .sync_errors import should_retry_webhook_failure
from .sync_service import TiendanubeAdministraNETSyncService

logger = logging.getLogger(__name__)


def enqueue_stock_push_outbox(
    *,
    tiendanube_config: TiendanubeConfig,
    adminet_config: AdministraNETConfig,
    article_ids: Iterable[int],
    deposito_id: int,
) -> TiendanubeOutboxEvent:
    """Encolar push de stock Adminet → TN para procesamiento asíncrono."""
    ids = sorted({int(a) for a in article_ids if a})
    return TiendanubeOutboxEvent.objects.create(
        tiendanube_config=tiendanube_config,
        adminet_config=adminet_config,
        event_type=TiendanubeOutboxEvent.EventType.STOCK_PUSH,
        payload={'article_ids': ids, 'deposito_id': int(deposito_id)},
        status=TiendanubeOutboxEvent.EventStatus.PENDING,
    )


def enqueue_catch_up_orders_outbox(
    *,
    tiendanube_config: TiendanubeConfig,
    adminet_config: AdministraNETConfig,
    since=None,
) -> TiendanubeOutboxEvent:
    """Encolar catch-up GET orders tras reconexión."""
    payload: Dict[str, Any] = {}
    if since is not None:
        payload['since'] = since.isoformat() if hasattr(since, 'isoformat') else str(since)
    return TiendanubeOutboxEvent.objects.create(
        tiendanube_config=tiendanube_config,
        adminet_config=adminet_config,
        event_type=TiendanubeOutboxEvent.EventType.CATCH_UP_ORDERS,
        payload=payload,
        status=TiendanubeOutboxEvent.EventStatus.PENDING,
    )


def _process_stock_push_event(event: TiendanubeOutboxEvent) -> Dict[str, Any]:
    payload = event.payload or {}
    article_ids: List[int] = payload.get('article_ids') or []
    deposito_id = payload.get('deposito_id')
    adminet_config = event.adminet_config or AdministraNETConfig.objects.filter(
        is_active=True
    ).first()
    if not adminet_config:
        return {'success': False, 'error': 'Sin configuración AdministraNET activa.'}

    sync_service = TiendanubeAdministraNETSyncService(
        event.tiendanube_config,
        adminet_config,
        base_empresa=adminet_config.database,
    )
    result = push_stock_for_article_ids(
        sync_service,
        article_ids,
        deposito_id,
        enqueue_on_failure=False,
    )
    if result.get('success'):
        return {'success': True, **result}

    status_code = result.get('status_code')
    return {
        'success': False,
        'error': result.get('message', 'Error en push stock TN'),
        'status_code': status_code,
    }


def _process_catch_up_orders_event(event: TiendanubeOutboxEvent) -> Dict[str, Any]:
    adminet_config = event.adminet_config or AdministraNETConfig.objects.filter(
        is_active=True
    ).first()
    if not adminet_config:
        return {'success': False, 'error': 'Sin configuración AdministraNET activa.'}

    since_raw = (event.payload or {}).get('since')
    since = None
    if since_raw:
        since = timezone.datetime.fromisoformat(since_raw.replace('Z', '+00:00'))
        if timezone.is_naive(since):
            since = timezone.make_aware(since)

    sync_service = TiendanubeAdministraNETSyncService(
        event.tiendanube_config,
        adminet_config,
        base_empresa=adminet_config.database,
    )
    return sync_service.catch_up_missing_orders(since=since)


def process_outbox_event(event: TiendanubeOutboxEvent) -> Dict[str, Any]:
    """Procesar un evento outbox ya persistido."""
    try:
        event.mark_processing()
        if event.event_type == TiendanubeOutboxEvent.EventType.STOCK_PUSH:
            result = _process_stock_push_event(event)
        elif event.event_type == TiendanubeOutboxEvent.EventType.CATCH_UP_ORDERS:
            result = _process_catch_up_orders_event(event)
        else:
            result = {
                'success': False,
                'error': f'Tipo outbox no soportado: {event.event_type}',
            }

        if result.get('success'):
            event.mark_completed(result)
        else:
            retry = should_retry_webhook_failure(
                http_status=result.get('status_code'),
            )
            event.mark_failed(result.get('error', 'Error outbox'), retry=retry)

        return result

    except Exception as exc:
        error_msg = f'Error procesando outbox {event.id}: {exc}'
        logger.exception(error_msg)
        event.mark_failed(error_msg, retry=should_retry_webhook_failure(exc=exc))
        return {'success': False, 'error': error_msg}
