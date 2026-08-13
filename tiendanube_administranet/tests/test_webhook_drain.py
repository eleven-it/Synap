"""Tests comando y task Celery de drenaje inbox webhook."""

import io
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from tiendanube_administranet.models import TiendanubeConfig, WebhookConfig, WebhookEvent
from tiendanube_administranet.services.inbox_worker import DrainResult


class TiendanubeDrainInboxCommandTests(TestCase):
    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda cmd drain',
            store_id='cmd-drain-001',
            access_token='token-cmd',
            is_active=True,
        )
        self.webhook_config = WebhookConfig.objects.create(
            tiendanube_config=self.tn_config,
            webhook_url='http://example.com/webhook/',
            is_active=True,
        )

    @patch('tiendanube_administranet.management.commands.tiendanube_drain_inbox.drain_webhook_events')
    def test_comando_invoca_drain_y_exit_0_sin_fallos(self, mock_drain):
        mock_drain.return_value = DrainResult(processed=2, succeeded=2, failed=0)

        out = io.StringIO()
        call_command('tiendanube_drain_inbox', stdout=out)

        mock_drain.assert_called_once_with(limit=50)
        self.assertIn('2 procesados', out.getvalue())

    @patch('tiendanube_administranet.management.commands.tiendanube_drain_inbox.drain_webhook_events')
    def test_comando_exit_1_si_hay_fallos(self, mock_drain):
        mock_drain.return_value = DrainResult(processed=3, succeeded=2, failed=1)

        with self.assertRaises(SystemExit) as ctx:
            call_command('tiendanube_drain_inbox', stdout=io.StringIO())

        self.assertEqual(ctx.exception.code, 1)

    @patch('tiendanube_administranet.management.commands.tiendanube_drain_inbox.drain_webhook_events')
    def test_comando_limit_personalizado(self, mock_drain):
        mock_drain.return_value = DrainResult(processed=0, succeeded=0, failed=0)

        call_command('tiendanube_drain_inbox', limit=10, stdout=io.StringIO())

        mock_drain.assert_called_once_with(limit=10)


class DrainWebhookInboxTaskTests(TestCase):
    @patch('tiendanube_administranet.tasks.webhook_tasks.drain_webhook_events')
    def test_task_celery_reutiliza_inbox_worker(self, mock_drain):
        from tiendanube_administranet.tasks.webhook_tasks import drain_webhook_inbox

        mock_drain.return_value = DrainResult(processed=1, succeeded=1, failed=0)

        result = drain_webhook_inbox(limit=50)

        mock_drain.assert_called_once_with(limit=50)
        self.assertTrue(result['success'])
        self.assertEqual(result['processed'], 1)
        self.assertEqual(result['succeeded'], 1)
        self.assertEqual(result['failed'], 0)
