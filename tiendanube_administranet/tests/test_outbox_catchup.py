"""Tests outbox saliente Adminet→TN y catch-up de pedidos tras reconexión."""

import io
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from tiendanube_administranet.models import (
    AdministraNETConfig,
    OrderMapping,
    ProductMapping,
    ProductVariantMapping,
    TiendanubeConfig,
    TiendanubeOutboxEvent,
    WebhookConfig,
)
from tiendanube_administranet.services.inbox_worker import DrainResult, drain_outbox_events
from tiendanube_administranet.services.outbox_service import enqueue_stock_push_outbox
from tiendanube_administranet.services.sync_service import TiendanubeAdministraNETSyncService


class OutboxStockEnqueueTests(TestCase):
    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda outbox',
            store_id='outbox-001',
            access_token='token-outbox',
            is_active=True,
        )
        self.adminet_config = AdministraNETConfig.objects.create(
            name='Adminet outbox',
            database='test_empresa',
            deposito_tiendanube_id=5,
            is_active=True,
        )

    def test_cambio_stock_encola_evento_outbox_pending(self):
        event = enqueue_stock_push_outbox(
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            article_ids=[101, 102],
            deposito_id=5,
        )

        self.assertIsInstance(event, TiendanubeOutboxEvent)
        self.assertEqual(event.status, TiendanubeOutboxEvent.EventStatus.PENDING)
        self.assertEqual(event.event_type, TiendanubeOutboxEvent.EventType.STOCK_PUSH)
        self.assertEqual(event.payload['article_ids'], [101, 102])
        self.assertEqual(event.payload['deposito_id'], 5)
        self.assertEqual(TiendanubeOutboxEvent.objects.count(), 1)


class OutboxDrainTests(TestCase):
    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda drain outbox',
            store_id='outbox-drain-001',
            access_token='token-drain',
            is_active=True,
        )
        self.adminet_config = AdministraNETConfig.objects.create(
            name='Adminet drain outbox',
            database='test_empresa',
            deposito_tiendanube_id=3,
            is_active=True,
        )

    @patch('tiendanube_administranet.services.outbox_service.push_stock_for_article_ids')
    @patch('tiendanube_administranet.services.outbox_service.TiendanubeAdministraNETSyncService')
    def test_drain_outbox_procesa_stock_push_exitoso(self, mock_sync_cls, mock_push):
        mock_sync = MagicMock()
        mock_sync_cls.return_value = mock_sync
        mock_push.return_value = {'success': True, 'pushed': 1}

        event = TiendanubeOutboxEvent.objects.create(
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            event_type=TiendanubeOutboxEvent.EventType.STOCK_PUSH,
            payload={'article_ids': [55], 'deposito_id': 3},
            status=TiendanubeOutboxEvent.EventStatus.PENDING,
        )

        result = drain_outbox_events(limit=50)

        self.assertEqual(result.processed, 1)
        self.assertEqual(result.succeeded, 1)
        self.assertEqual(result.failed, 0)
        event.refresh_from_db()
        self.assertEqual(event.status, TiendanubeOutboxEvent.EventStatus.COMPLETED)
        mock_push.assert_called_once()

    @patch('tiendanube_administranet.services.outbox_service.push_stock_for_article_ids')
    @patch('tiendanube_administranet.services.outbox_service.TiendanubeAdministraNETSyncService')
    def test_drain_outbox_incrementa_retry_fallo_red(self, mock_sync_cls, mock_push):
        mock_sync_cls.return_value = MagicMock()
        mock_push.return_value = {
            'success': False,
            'message': 'Service unavailable',
            'status_code': 503,
        }

        event = TiendanubeOutboxEvent.objects.create(
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            event_type=TiendanubeOutboxEvent.EventType.STOCK_PUSH,
            payload={'article_ids': [77], 'deposito_id': 3},
            status=TiendanubeOutboxEvent.EventStatus.RETRY,
            retry_count=1,
            next_retry_at=timezone.now() - timedelta(minutes=1),
        )

        result = drain_outbox_events(limit=50)

        self.assertEqual(result.processed, 1)
        self.assertEqual(result.failed, 1)
        event.refresh_from_db()
        self.assertEqual(event.retry_count, 2)
        self.assertEqual(event.status, TiendanubeOutboxEvent.EventStatus.RETRY)
        self.assertIsNotNone(event.next_retry_at)

    @patch('tiendanube_administranet.services.outbox_service.process_outbox_event')
    def test_drain_outbox_respeta_batch_max_50(self, mock_process):
        mock_process.return_value = {'success': True}

        for i in range(55):
            TiendanubeOutboxEvent.objects.create(
                tiendanube_config=self.tn_config,
                adminet_config=self.adminet_config,
                event_type=TiendanubeOutboxEvent.EventType.STOCK_PUSH,
                payload={'article_ids': [i], 'deposito_id': 3},
                status=TiendanubeOutboxEvent.EventStatus.PENDING,
            )

        result = drain_outbox_events(limit=50)

        self.assertEqual(result.processed, 50)
        self.assertEqual(mock_process.call_count, 50)


class CatchUpOrdersTests(TestCase):
    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda catch-up',
            store_id='catchup-001',
            access_token='token-catchup',
            is_active=True,
            last_sync=timezone.now() - timedelta(hours=2),
        )
        self.adminet_config = AdministraNETConfig.objects.create(
            name='Adminet catch-up',
            database='test_empresa',
            deposito_tiendanube_id=1,
            is_active=True,
        )
        self.webhook_config = WebhookConfig.objects.create(
            tiendanube_config=self.tn_config,
            webhook_url='http://example.com/webhook/',
            is_active=True,
        )
        OrderMapping.objects.create(
            tiendanube_id=1001,
            tiendanube_number='1001',
            adminet_codigo='MOV-1001',
            sync_status=OrderMapping.SyncStatus.SYNCED,
        )

    @patch('tiendanube_administranet.services.webhook_service.WebhookProcessor._handle_order_event')
    @patch.object(TiendanubeAdministraNETSyncService, '__init__', lambda self, *a, **k: None)
    def test_catch_up_importa_pedido_ausente_sin_duplicar(self, mock_handle_order):
        mock_handle_order.return_value = {
            'success': True,
            'action': 'order_paid',
            'order_id': 2002,
        }

        svc = TiendanubeAdministraNETSyncService()
        svc.tiendanube_config = self.tn_config
        svc.adminet_config = self.adminet_config
        svc.tiendanube_service = MagicMock()
        svc.tiendanube_service.get_orders.return_value = {
            'success': True,
            'orders': [
                {
                    'id': 1001,
                    'number': '1001',
                    'payment_status': 'paid',
                    'status': 'open',
                    'total': 100,
                },
                {
                    'id': 2002,
                    'number': '2002',
                    'payment_status': 'paid',
                    'status': 'open',
                    'total': 250,
                },
            ],
        }

        result = svc.catch_up_missing_orders()

        self.assertTrue(result['success'])
        self.assertEqual(result['imported'], 1)
        self.assertEqual(result['skipped_existing'], 1)
        mock_handle_order.assert_called_once()
        call_args = mock_handle_order.call_args
        self.assertEqual(call_args[0][1]['data']['id'], 2002)


class TiendanubeDrainOutboxCommandTests(TestCase):
    @patch('tiendanube_administranet.management.commands.tiendanube_drain_outbox.drain_outbox_events')
    def test_comando_drain_outbox_invoca_worker(self, mock_drain):
        mock_drain.return_value = DrainResult(processed=2, succeeded=2, failed=0)

        out = io.StringIO()
        call_command('tiendanube_drain_outbox', stdout=out)

        mock_drain.assert_called_once_with(limit=50)
        self.assertIn('2 procesados', out.getvalue())

    @patch('tiendanube_administranet.tasks.webhook_tasks.drain_outbox_events')
    def test_task_celery_drain_outbox_reutiliza_worker(self, mock_drain):
        from tiendanube_administranet.tasks.webhook_tasks import drain_outbox

        mock_drain.return_value = DrainResult(processed=1, succeeded=1, failed=0)

        result = drain_outbox(limit=50)

        mock_drain.assert_called_once_with(limit=50)
        self.assertTrue(result['success'])
        self.assertEqual(result['processed'], 1)


class PushStockFailureEnqueuesOutboxTests(TestCase):
    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda push fail',
            store_id='push-fail-001',
            access_token='token-fail',
            is_active=True,
        )
        self.adminet_config = AdministraNETConfig.objects.create(
            name='Adminet push fail',
            database='test_empresa',
            deposito_tiendanube_id=7,
            is_active=True,
        )
        ProductMapping.objects.create(
            tiendanube_id=500,
            adminet_id=42,
            sync_stock=True,
            sync_status=ProductMapping.SyncStatus.SYNCED,
        )
        ProductVariantMapping.objects.create(
            product_mapping=ProductMapping.objects.get(adminet_id=42),
            tiendanube_variant_id=900,
        )

    @patch('tiendanube_administranet.services.outbox_service.enqueue_stock_push_outbox')
    @patch('tiendanube_administranet.services.order_stock_push.stock_unidades_articulo_deposito', return_value=10)
    def test_push_fallido_transitorio_encola_outbox(self, _stock_units, mock_enqueue):
        from tiendanube_administranet.services.order_stock_push import push_stock_for_article_ids

        mock_sync = MagicMock()
        mock_sync.adminet_config.deposito_tiendanube_id = 7
        mock_sync.adminet_service.get_stock_by_deposito.return_value = {
            'success': True,
            'stock': 10,
            'stock_pedido_cliente': 0,
        }
        mock_sync._build_stock_price_patch_payload.return_value = [{'id': 500, 'variants': []}]
        mock_sync.product_service.patch_products_stock_price.return_value = {
            'success': False,
            'message': 'Service unavailable',
            'status_code': 503,
        }
        mock_sync.tiendanube_config = self.tn_config
        mock_sync.adminet_config = self.adminet_config

        result = push_stock_for_article_ids(mock_sync, [42], deposito_id=7)

        self.assertFalse(result['success'])
        mock_enqueue.assert_called_once_with(
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            article_ids=[42],
            deposito_id=7,
        )
