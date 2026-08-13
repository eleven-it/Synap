"""Worker de drenaje del inbox webhook (pending + retry vencido)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

from django.db.models import Q
from django.utils import timezone

from ..models import WebhookEvent, TiendanubeOutboxEvent
from .webhook_service import WebhookProcessor

logger = logging.getLogger(__name__)

DEFAULT_DRAIN_BATCH_SIZE = 50


@dataclass
class DrainResult:
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)


def _eligible_webhook_events_queryset():
    now = timezone.now()
    return WebhookEvent.objects.filter(
        Q(status=WebhookEvent.EventStatus.PENDING)
        | Q(
            status=WebhookEvent.EventStatus.RETRY,
            retry_count__gt=0,
            next_retry_at__lte=now,
        )
    ).select_related(
        'webhook_config',
        'webhook_config__tiendanube_config',
    ).order_by('received_at')


def drain_webhook_events(limit: int = DEFAULT_DRAIN_BATCH_SIZE) -> DrainResult:
    """
    Drenar eventos webhook pending o retry vencidos usando el handler canónico.

    Args:
        limit: Máximo de eventos a procesar por invocación (default 50).

    Returns:
        DrainResult con contadores de procesamiento.
    """
    result = DrainResult()
    batch_size = max(1, int(limit))
    events = list(_eligible_webhook_events_queryset()[:batch_size])

    for webhook_event in events:
        result.processed += 1
        try:
            outcome = WebhookProcessor.process_stored_webhook_event(webhook_event)
            if outcome.get('success'):
                result.succeeded += 1
            else:
                result.failed += 1
                error = outcome.get('error') or 'Error desconocido'
                result.errors.append(f"{webhook_event.event_id}: {error}")
        except Exception as exc:
            result.failed += 1
            msg = f"{webhook_event.event_id}: {exc}"
            result.errors.append(msg)
            logger.exception("Error drenando evento %s", webhook_event.event_id)

    if result.processed:
        logger.info(
            "Drain inbox webhook: processed=%s succeeded=%s failed=%s",
            result.processed,
            result.succeeded,
            result.failed,
        )

    return result


def _eligible_outbox_events_queryset():
    now = timezone.now()
    return TiendanubeOutboxEvent.objects.filter(
        Q(status=TiendanubeOutboxEvent.EventStatus.PENDING)
        | Q(
            status=TiendanubeOutboxEvent.EventStatus.RETRY,
            retry_count__gt=0,
            next_retry_at__lte=now,
        )
    ).select_related(
        'tiendanube_config',
        'adminet_config',
    ).order_by('created_at')


def drain_outbox_events(limit: int = DEFAULT_DRAIN_BATCH_SIZE) -> DrainResult:
    """
    Drenar eventos outbox pending o retry vencidos (stock push, catch-up).

    Args:
        limit: Máximo de eventos por invocación (default 50).

    Returns:
        DrainResult con contadores de procesamiento.
    """
    from .outbox_service import process_outbox_event

    result = DrainResult()
    batch_size = max(1, int(limit))
    events = list(_eligible_outbox_events_queryset()[:batch_size])

    for outbox_event in events:
        result.processed += 1
        try:
            outcome = process_outbox_event(outbox_event)
            if outcome.get('success'):
                result.succeeded += 1
            else:
                result.failed += 1
                error = outcome.get('error') or 'Error desconocido'
                result.errors.append(f"outbox-{outbox_event.id}: {error}")
        except Exception as exc:
            result.failed += 1
            msg = f"outbox-{outbox_event.id}: {exc}"
            result.errors.append(msg)
            logger.exception("Error drenando outbox %s", outbox_event.id)

    if result.processed:
        logger.info(
            "Drain outbox: processed=%s succeeded=%s failed=%s",
            result.processed,
            result.succeeded,
            result.failed,
        )

    return result
