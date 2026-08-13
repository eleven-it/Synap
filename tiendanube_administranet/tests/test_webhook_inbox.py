"""Tests inbox webhook: ACK rápido, persistencia y clasificación retry."""

import importlib
import inspect
import json
import time
from datetime import timedelta
from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from tiendanube_administranet.views.webhook_config_views import webhook_endpoint

from tiendanube_administranet.models import (
    TiendanubeConfig,
    WebhookConfig,
    WebhookEvent,
)
from tiendanube_administranet.services.webhook_service import WebhookProcessor


class WebhookInboxAckTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda inbox test',
            store_id='inbox-001',
            access_token='token-inbox',
            is_active=True,
        )
        self.webhook_url = reverse('tiendanube_administranet:webhook_endpoint')
        self.webhook_config = WebhookConfig.objects.create(
            tiendanube_config=self.tn_config,
            webhook_url=f'http://testserver{self.webhook_url}',
            is_active=True,
            events=['order/paid'],
        )
        self.payload = {
            'store_id': 1,
            'event': 'order/paid',
            'id': 501,
            'data': {'id': 9001},
        }

    def _post_webhook(self, payload=None, signature=''):
        body = json.dumps(payload or self.payload)
        request = self.factory.post(
            self.webhook_url,
            data=body,
            content_type='application/json',
            HTTP_HOST='testserver',
            HTTP_X_LINKEDSTORE_HMAC_SHA256=signature,
        )
        return webhook_endpoint(request)

    @patch('tiendanube_administranet.services.webhook_service.WebhookProcessor._handle_event_by_type')
    def test_post_valido_persiste_y_acepta_sin_negocio_inline(self, mock_handle_event):
        started = time.monotonic()
        response = self._post_webhook()
        elapsed = time.monotonic() - started

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'status': 'accepted'})
        self.assertLess(elapsed, 3.0)

        events = WebhookEvent.objects.filter(webhook_config=self.webhook_config)
        self.assertEqual(events.count(), 1)
        event = events.get()
        self.assertEqual(event.status, WebhookEvent.EventStatus.PENDING)
        self.assertEqual(event.event_type, 'order/paid')
        self.assertEqual(event.event_id, '501')
        self.assertEqual(event.resource_id, 9001)

        mock_handle_event.assert_not_called()

    @override_settings(ENVIRONMENT='production')
    def test_hmac_invalido_prod_401_sin_persistir(self):
        self.webhook_config.webhook_secret = 'prod-secret'
        self.webhook_config.save(update_fields=['webhook_secret'])

        response = self._post_webhook(signature='firma-invalida')

        self.assertEqual(response.status_code, 401)
        self.assertEqual(WebhookEvent.objects.count(), 0)


class WebhookMarkFailedRetryTests(TestCase):
    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda retry test',
            store_id='retry-001',
            access_token='token-retry',
            is_active=True,
        )
        self.webhook_config = WebhookConfig.objects.create(
            tiendanube_config=self.tn_config,
            webhook_url='http://example.com/webhook/',
            is_active=True,
            max_retries=5,
            retry_delay=60,
        )
        self.event_payload = {
            'type': 'order/paid',
            'id': 'evt-1',
            'data': {'id': 100},
        }

    @patch.object(WebhookProcessor, '_handle_event_by_type')
    def test_fallo_transient_programa_retry(self, mock_handle):
        mock_handle.return_value = {
            'success': False,
            'error': 'Service unavailable',
            'status_code': 503,
        }

        WebhookProcessor.process_webhook_event(
            self.webhook_config,
            self.event_payload,
            {},
        )

        event = WebhookEvent.objects.get(event_id='evt-1')
        self.assertEqual(event.status, WebhookEvent.EventStatus.RETRY)
        self.assertEqual(event.retry_count, 1)
        self.assertIsNotNone(event.next_retry_at)

    @patch.object(WebhookProcessor, '_handle_event_by_type')
    def test_fallo_not_configured_sin_retry(self, mock_handle):
        mock_handle.return_value = {
            'success': False,
            'error': 'Plan limit reached',
            'status_code': 402,
        }

        WebhookProcessor.process_webhook_event(
            self.webhook_config,
            self.event_payload,
            {},
        )

        event = WebhookEvent.objects.get(event_id='evt-1')
        self.assertEqual(event.status, WebhookEvent.EventStatus.FAILED)
        self.assertEqual(event.retry_count, 1)
        self.assertIsNone(event.next_retry_at)


class WebhookHandlerParityTests(TestCase):
    """Paridad: simulación/retry usan webhook_service.WebhookProcessor canónico."""

    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda paridad',
            store_id='parity-001',
            access_token='token-parity',
            is_active=True,
        )
        self.webhook_config = WebhookConfig.objects.create(
            tiendanube_config=self.tn_config,
            webhook_url='http://example.com/webhook/',
            is_active=True,
        )
        self.order_event_data = {
            'type': 'order/paid',
            'id': 'parity-evt-1',
            'data': {'id': 77001, 'payment_status': 'paid', 'total': 100},
        }

    def test_modulo_simulate_usa_webhook_processor_canonico(self):
        from tiendanube_administranet.management.commands import (
            tiendanube_simulate_order_paid as sim_module,
        )
        from tiendanube_administranet.services.webhook_service import (
            WebhookProcessor as CanonicalProcessor,
        )

        self.assertIs(sim_module.WebhookProcessor, CanonicalProcessor)

    def test_retry_ajax_y_endpoint_sin_webhook_processor_legacy(self):
        from tiendanube_administranet.views import webhook_config_views

        retry_src = inspect.getsource(webhook_config_views.retry_webhook_event_ajax)
        endpoint_src = inspect.getsource(webhook_config_views.webhook_endpoint)

        self.assertIn('webhook_service', retry_src)
        self.assertNotIn('webhook_processor', retry_src)
        self.assertNotIn('webhook_processor', endpoint_src)

    def test_webhook_views_sin_import_webhook_processor_legacy(self):
        from tiendanube_administranet.views import webhook_views

        src = inspect.getsource(webhook_views)
        self.assertNotIn('webhook_processor', src)

    def test_webhook_processor_legacy_modulo_eliminado(self):
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module('tiendanube_administranet.services.webhook_processor')

    @patch.object(WebhookProcessor, '_handle_order_event')
    def test_simulate_y_process_event_invocan_mismo_handler(self, mock_handle_order):
        mock_handle_order.return_value = {
            'success': True,
            'action': 'order_paid',
            'order_id': 77001,
        }

        WebhookProcessor.process_webhook_event(
            self.webhook_config,
            self.order_event_data,
            {},
        )

        webhook_event = WebhookEvent.objects.create(
            webhook_config=self.webhook_config,
            event_type='order/paid',
            event_id='sim-direct',
            resource_id=77001,
            resource_type='order',
            payload=self.order_event_data,
            headers={},
        )
        WebhookProcessor._handle_order_event(webhook_event, self.order_event_data)

        self.assertEqual(mock_handle_order.call_count, 2)
        for call in mock_handle_order.call_args_list:
            self.assertIs(call.args[1], self.order_event_data)


class WebhookInboxDrainTests(TestCase):
    """Worker drain: pending y retry vencido vía handler canónico."""

    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda drain test',
            store_id='drain-001',
            access_token='token-drain',
            is_active=True,
        )
        self.webhook_config = WebhookConfig.objects.create(
            tiendanube_config=self.tn_config,
            webhook_url='http://example.com/webhook/',
            is_active=True,
            max_retries=5,
            retry_delay=60,
        )
        self.event_payload = {
            'type': 'order/paid',
            'id': 'drain-retry-1',
            'data': {'id': 88001, 'payment_status': 'paid'},
        }

    def _create_retry_event_due(self, event_id='drain-retry-1'):
        past = timezone.now() - timedelta(minutes=5)
        return WebhookEvent.objects.create(
            webhook_config=self.webhook_config,
            event_type='order/paid',
            event_id=event_id,
            resource_id=88001,
            resource_type='order',
            payload=self.event_payload,
            headers={},
            status=WebhookEvent.EventStatus.RETRY,
            retry_count=1,
            next_retry_at=past,
            error_message='Service unavailable',
        )

    @patch.object(WebhookProcessor, '_handle_order_event')
    def test_retry_vencido_se_reprocesa(self, mock_handle_order):
        from tiendanube_administranet.services.inbox_worker import drain_webhook_events

        mock_handle_order.return_value = {
            'success': True,
            'action': 'order_paid',
            'order_id': 88001,
        }
        event = self._create_retry_event_due()

        result = drain_webhook_events(limit=50)

        event.refresh_from_db()
        self.assertEqual(result.processed, 1)
        self.assertEqual(result.succeeded, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(event.status, WebhookEvent.EventStatus.COMPLETED)
        mock_handle_order.assert_called_once()

    @patch.object(WebhookProcessor, '_handle_order_event')
    def test_pending_tambien_se_drena(self, mock_handle_order):
        from tiendanube_administranet.services.inbox_worker import drain_webhook_events

        mock_handle_order.return_value = {
            'success': True,
            'action': 'order_paid',
            'order_id': 88002,
        }
        pending_payload = {
            'type': 'order/paid',
            'id': 'drain-pending-1',
            'data': {'id': 88002, 'payment_status': 'paid'},
        }
        event = WebhookEvent.objects.create(
            webhook_config=self.webhook_config,
            event_type='order/paid',
            event_id='drain-pending-1',
            resource_id=88002,
            resource_type='order',
            payload=pending_payload,
            headers={},
            status=WebhookEvent.EventStatus.PENDING,
        )

        result = drain_webhook_events(limit=50)

        event.refresh_from_db()
        self.assertEqual(result.processed, 1)
        self.assertEqual(event.status, WebhookEvent.EventStatus.COMPLETED)
        mock_handle_order.assert_called_once()

    @patch.object(WebhookProcessor, '_handle_order_event')
    def test_batch_maximo_50_eventos(self, mock_handle_order):
        from tiendanube_administranet.services.inbox_worker import drain_webhook_events

        mock_handle_order.return_value = {'success': True, 'action': 'order_paid'}

        for i in range(55):
            WebhookEvent.objects.create(
                webhook_config=self.webhook_config,
                event_type='order/paid',
                event_id=f'drain-batch-{i}',
                resource_id=90000 + i,
                resource_type='order',
                payload={
                    'type': 'order/paid',
                    'id': f'drain-batch-{i}',
                    'data': {'id': 90000 + i},
                },
                headers={},
                status=WebhookEvent.EventStatus.PENDING,
            )

        result = drain_webhook_events(limit=50)

        self.assertEqual(result.processed, 50)
        self.assertEqual(mock_handle_order.call_count, 50)
        self.assertEqual(
            WebhookEvent.objects.filter(status=WebhookEvent.EventStatus.PENDING).count(),
            5,
        )

    @patch.object(WebhookProcessor, '_handle_order_event')
    def test_retry_futuro_no_se_drena(self, mock_handle_order):
        from tiendanube_administranet.services.inbox_worker import drain_webhook_events

        future = timezone.now() + timedelta(hours=1)
        WebhookEvent.objects.create(
            webhook_config=self.webhook_config,
            event_type='order/paid',
            event_id='drain-future-retry',
            resource_id=88003,
            resource_type='order',
            payload=self.event_payload,
            headers={},
            status=WebhookEvent.EventStatus.RETRY,
            retry_count=1,
            next_retry_at=future,
        )

        result = drain_webhook_events(limit=50)

        self.assertEqual(result.processed, 0)
        mock_handle_order.assert_not_called()
