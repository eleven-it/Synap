"""Tareas Celery para drenaje del inbox webhook Tienda Nube."""

import logging
from typing import Any, Dict

try:
    from celery import shared_task
except ImportError:  # Celery opcional en instalaciones mínimas
    def shared_task(*args, **kwargs):
        def _decorator(f):
            return f
        return _decorator

from django.utils import timezone

from ..services.inbox_worker import DEFAULT_DRAIN_BATCH_SIZE, drain_outbox_events, drain_webhook_events

logger = logging.getLogger(__name__)

# Beat schedule (activar cuando django_project/celery.py esté habilitado):
# 'drain-webhook-inbox-every-60s': {
#     'task': 'tiendanube_administranet.tasks.webhook_tasks.drain_webhook_inbox',
#     'schedule': 60.0,
#     'kwargs': {'limit': DEFAULT_DRAIN_BATCH_SIZE},
# },
# 'drain-outbox-every-60s': {
#     'task': 'tiendanube_administranet.tasks.webhook_tasks.drain_outbox',
#     'schedule': 60.0,
#     'kwargs': {'limit': DEFAULT_DRAIN_BATCH_SIZE},
# },


@shared_task(bind=True, name='tiendanube_administranet.tasks.webhook_tasks.drain_webhook_inbox')
def drain_webhook_inbox(self, limit: int = DEFAULT_DRAIN_BATCH_SIZE) -> Dict[str, Any]:
    """
    Drenar inbox webhook pending/retry vencido (misma lógica que manage.py).

    Fallback operativo sin Beat: cron cada 60 s con ``tiendanube_drain_inbox``.
    """
    try:
        result = drain_webhook_events(limit=limit)
        return {
            'success': result.failed == 0,
            'processed': result.processed,
            'succeeded': result.succeeded,
            'failed': result.failed,
            'errors': result.errors[:10],
            'timestamp': timezone.now().isoformat(),
        }
    except Exception as exc:
        error_msg = f'Error en drain_webhook_inbox: {exc}'
        logger.exception(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat(),
        }


@shared_task(bind=True, name='tiendanube_administranet.tasks.webhook_tasks.drain_outbox')
def drain_outbox(self, limit: int = DEFAULT_DRAIN_BATCH_SIZE) -> Dict[str, Any]:
    """
    Drenar outbox saliente pending/retry vencido (misma lógica que manage.py).

    Fallback operativo sin Beat: cron cada 60 s con ``tiendanube_drain_outbox``.
    """
    try:
        result = drain_outbox_events(limit=limit)
        return {
            'success': result.failed == 0,
            'processed': result.processed,
            'succeeded': result.succeeded,
            'failed': result.failed,
            'errors': result.errors[:10],
            'timestamp': timezone.now().isoformat(),
        }
    except Exception as exc:
        error_msg = f'Error en drain_outbox: {exc}'
        logger.exception(error_msg)
        return {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat(),
        }
