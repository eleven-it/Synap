"""Simular webhook order/paid con una orden TN existente (prueba operativa)."""

import copy
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from tiendanube_administranet.models import WebhookConfig, WebhookEvent
from tiendanube_administranet.services.tiendanube_service import TiendanubeService
from tiendanube_administranet.services.webhook_service import WebhookProcessor


class Command(BaseCommand):
    help = (
        'Clona una orden TN (--source-order), la marca como pagada y procesa '
        'order/paid como en el webhook real (sin HMAC).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-order',
            type=int,
            required=True,
            help='ID orden TN a clonar (ej. 1814670210)',
        )
        parser.add_argument(
            '--simulate-id',
            type=int,
            default=9000000002,
            help='id_tiendanube ficticio para Adminet (default 9000000002)',
        )

    def handle(self, *args, **options):
        webhook_config = WebhookConfig.objects.filter(is_active=True).first()
        if not webhook_config:
            raise CommandError('No hay WebhookConfig activa.')

        tn_service = TiendanubeService(webhook_config.tiendanube_config)
        source_id = options['source_order']
        simulate_id = options['simulate_id']

        api = tn_service.get_order(source_id)
        if not api.get('success'):
            raise CommandError(api.get('message', f'No se pudo leer orden TN {source_id}'))

        order = copy.deepcopy(api['order'])
        order['id'] = simulate_id
        order['payment_status'] = 'paid'
        order['paid_at'] = timezone.now().isoformat()

        event_data = {
            'type': 'order/paid',
            'id': f'simulate-{uuid.uuid4().hex[:12]}',
            'data': order,
        }

        webhook_event = WebhookEvent.objects.create(
            webhook_config=webhook_config,
            event_type='order/paid',
            event_id=event_data['id'],
            resource_id=simulate_id,
            resource_type='order',
            payload=event_data,
            headers={'X-Simulated': 'true'},
        )

        self.stdout.write(
            f'Simulando order/paid: source={source_id} → simulate_id={simulate_id}'
        )

        result = WebhookProcessor._handle_order_event(webhook_event, event_data)

        if result.get('success'):
            webhook_event.mark_completed(result)
            self.stdout.write(self.style.SUCCESS(str(result)))
        else:
            webhook_event.mark_failed(result.get('error', 'Error desconocido'))
            raise CommandError(result.get('error', str(result)))
