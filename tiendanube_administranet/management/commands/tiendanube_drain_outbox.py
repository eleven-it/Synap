"""
Drenar outbox saliente Tienda Nube (stock push, catch-up pedidos).

Operación recomendada sin Celery activo (cron cada 60 s, batch 50):

    */1 * * * * docker exec Synap_app python manage.py tiendanube_drain_outbox

Cuando ops reactive Celery, usar la task ``drain_outbox`` en
``tiendanube_administranet.tasks.webhook_tasks`` con Beat cada 60 s.
La infraestructura en ``django_project/celery.py`` permanece comentada
hasta que se habilite en el entorno.
"""

import sys

from django.core.management.base import BaseCommand

from tiendanube_administranet.services.inbox_worker import (
    DEFAULT_DRAIN_BATCH_SIZE,
    drain_outbox_events,
)


class Command(BaseCommand):
    help = (
        'Drena eventos outbox pending/retry vencidos (batch default 50). '
        'Cron sin Celery: */1 * * * * docker exec Synap_app '
        'python manage.py tiendanube_drain_outbox'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=DEFAULT_DRAIN_BATCH_SIZE,
            help=f'Máximo de eventos por ejecución (default {DEFAULT_DRAIN_BATCH_SIZE})',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        result = drain_outbox_events(limit=limit)

        self.stdout.write(
            f'Drenaje outbox: {result.processed} procesados, '
            f'{result.succeeded} exitosos, {result.failed} fallidos.'
        )

        for error in result.errors[:10]:
            self.stderr.write(error)

        if result.failed > 0:
            sys.exit(1)
