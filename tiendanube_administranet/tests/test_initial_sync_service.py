"""Tests unitarios — InitialSyncService (sync inicial por lotes)."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from tiendanube_administranet.models import (
    AdministraNETConfig,
    InitialSyncCheckpoint,
    TiendanubeConfig,
)
from tiendanube_administranet.services.initial_sync_service import InitialSyncService


class InitialSyncServiceTests(TestCase):
    def setUp(self):
        self.tn_config = TiendanubeConfig.objects.create(
            name='Tienda test',
            store_id='999001',
            access_token='token-test',
            is_active=True,
        )
        self.adminet_config = AdministraNETConfig.objects.create(
            name='Adminet test',
            database='empresa_test',
            is_active=True,
        )

    def _service(self) -> InitialSyncService:
        return InitialSyncService(self.tn_config, self.adminet_config)

    @patch.object(InitialSyncService, '_sync_disabled_response')
    @patch('tiendanube_administranet.services.initial_sync_service.tiendanube_sync_disabled_reason')
    def test_run_customer_batch_deshabilitado(self, mock_disabled, mock_response):
        mock_disabled.return_value = 'Sync off'
        mock_response.return_value = {'success': False, 'message': 'Sync off'}
        result = self._service().run_customer_batch(limit=10, offset=0)
        self.assertFalse(result['success'])
        mock_response.assert_called_once()

    @patch('tiendanube_administranet.services.initial_sync_service.TiendanubeAdministraNETSyncService')
    def test_run_customer_batch_actualiza_checkpoint(self, mock_sync_cls):
        mock_sync = MagicMock()
        mock_sync.sync_customers_from_adminet.return_value = {
            'success': True,
            'message': 'ok',
            'total_processed': 2,
            'successful': 2,
            'failed': 0,
            'total_available': 5,
            'sync_log_id': 1,
        }
        mock_sync_cls.return_value = mock_sync

        result = self._service().run_customer_batch(limit=2, offset=0)

        self.assertTrue(result['success'])
        self.assertEqual(result['last_offset'], 2)
        self.assertEqual(result['total_items'], 5)
        self.assertTrue(result['has_more'])
        self.assertEqual(result['checkpoint_status'], InitialSyncCheckpoint.Status.IN_PROGRESS)

        checkpoint = InitialSyncCheckpoint.objects.get(
            sync_type=InitialSyncCheckpoint.SyncType.CUSTOMER,
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
        )
        self.assertEqual(checkpoint.last_offset, 2)
        self.assertEqual(checkpoint.total_items, 5)

        mock_sync.sync_customers_from_adminet.assert_called_once_with(limit=2, offset=0)

    @patch('tiendanube_administranet.services.initial_sync_service.TiendanubeAdministraNETSyncService')
    def test_run_customer_batch_completa_checkpoint(self, mock_sync_cls):
        mock_sync = MagicMock()
        mock_sync.sync_customers_from_adminet.return_value = {
            'success': True,
            'message': 'ok',
            'total_processed': 3,
            'successful': 3,
            'failed': 0,
            'total_available': 3,
        }
        mock_sync_cls.return_value = mock_sync

        result = self._service().run_customer_batch(limit=30, offset=0)

        self.assertFalse(result['has_more'])
        self.assertEqual(result['checkpoint_status'], InitialSyncCheckpoint.Status.COMPLETED)

    @patch('tiendanube_administranet.services.initial_sync_service.TiendanubeAdministraNETSyncService')
    def test_run_product_batch_marca_fallo(self, mock_sync_cls):
        mock_sync = MagicMock()
        mock_sync.sync_products_from_adminet.return_value = {
            'success': False,
            'message': 'Error MySQL',
            'total_available': 10,
        }
        mock_sync_cls.return_value = mock_sync

        result = self._service().run_product_batch(limit=5, offset=0)

        self.assertFalse(result['success'])
        checkpoint = InitialSyncCheckpoint.objects.get(
            sync_type=InitialSyncCheckpoint.SyncType.PRODUCT,
        )
        self.assertEqual(checkpoint.status, InitialSyncCheckpoint.Status.FAILED)
        self.assertIn('MySQL', checkpoint.error_message)

    @patch.object(InitialSyncService, 'run_customer_batch')
    def test_run_next_pending_batch_usa_offset_checkpoint(self, mock_run_batch):
        InitialSyncCheckpoint.objects.create(
            sync_type=InitialSyncCheckpoint.SyncType.CUSTOMER,
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            last_offset=60,
            total_items=120,
            status=InitialSyncCheckpoint.Status.IN_PROGRESS,
        )
        mock_run_batch.return_value = {'success': True, 'last_offset': 90}

        self._service().run_next_pending_batch(
            sync_type=InitialSyncCheckpoint.SyncType.CUSTOMER,
            limit=30,
        )

        mock_run_batch.assert_called_once_with(limit=30, offset=60)

    @patch.object(InitialSyncService, 'run_product_batch')
    def test_run_next_pending_batch_producto(self, mock_run_batch):
        InitialSyncCheckpoint.objects.create(
            sync_type=InitialSyncCheckpoint.SyncType.PRODUCT,
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            last_offset=15,
            total_items=40,
            status=InitialSyncCheckpoint.Status.IN_PROGRESS,
        )
        mock_run_batch.return_value = {'success': True}

        self._service().run_next_pending_batch(
            sync_type=InitialSyncCheckpoint.SyncType.PRODUCT,
            limit=15,
        )

        mock_run_batch.assert_called_once_with(limit=15, offset=15)

    def test_run_next_pending_batch_ya_completado(self):
        InitialSyncCheckpoint.objects.create(
            sync_type=InitialSyncCheckpoint.SyncType.CUSTOMER,
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            last_offset=10,
            total_items=10,
            status=InitialSyncCheckpoint.Status.COMPLETED,
        )

        result = self._service().run_next_pending_batch(
            sync_type=InitialSyncCheckpoint.SyncType.CUSTOMER,
        )

        self.assertTrue(result['success'])
        self.assertFalse(result['has_more'])
        self.assertEqual(result['checkpoint_status'], InitialSyncCheckpoint.Status.COMPLETED)

    def test_reset_checkpoint(self):
        checkpoint = InitialSyncCheckpoint.objects.create(
            sync_type=InitialSyncCheckpoint.SyncType.CUSTOMER,
            tiendanube_config=self.tn_config,
            adminet_config=self.adminet_config,
            last_offset=90,
            total_items=100,
            status=InitialSyncCheckpoint.Status.COMPLETED,
            error_message='previo',
        )

        self._service().reset_checkpoint(InitialSyncCheckpoint.SyncType.CUSTOMER)

        checkpoint.refresh_from_db()
        self.assertEqual(checkpoint.last_offset, 0)
        self.assertEqual(checkpoint.total_items, 0)
        self.assertEqual(checkpoint.status, InitialSyncCheckpoint.Status.PENDING)
        self.assertEqual(checkpoint.error_message, '')
