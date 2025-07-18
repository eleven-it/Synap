from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest import mock
from administraNET_integration.models import SyncLog
from administraNET_integration.services.sync_service import AdministraNETSyncService
import sys
import importlib

class SyncLogWatchdogTest(TestCase):
    def test_watchdog_marks_stuck_logs_as_failed(self):
        # Importar el script como módulo
        if 'misc.scripts.watchdog_synclog' in sys.modules:
            importlib.reload(sys.modules['misc.scripts.watchdog_synclog'])
        else:
            import misc.scripts.watchdog_synclog
        watchdog = sys.modules['misc.scripts.watchdog_synclog']
        # Crear un log en RUNNING hace 31 minutos
        stuck_log = SyncLog.objects.create(
            sync_type='PRODUCTS',
            status='RUNNING',
            started_at=timezone.now() - timedelta(minutes=31)
        )
        # Ejecutar watchdog
        watchdog.main()
        stuck_log.refresh_from_db()
        self.assertEqual(stuck_log.status, 'FAILED')
        self.assertIn('[WATCHDOG]', stuck_log.error_message)
        self.assertIsNotNone(stuck_log.completed_at)

    def test_sync_all_closes_log_on_success(self):
        config = mock.Mock()
        service = AdministraNETSyncService(config)
        sync_log = SyncLog.objects.create(sync_type='PRODUCTS', status='PENDING')
        # Mockear métodos de sincronización para simular éxito
        service.sync_products = mock.Mock(return_value={'processed': 2, 'created': 1, 'updated': 1, 'failed': 0})
        service.sync_stock = mock.Mock(return_value={'processed': 0, 'created': 0, 'updated': 0, 'failed': 0})
        service.sync_customers = mock.Mock(return_value={'processed': 0, 'created': 0, 'updated': 0, 'failed': 0})
        service.sync_orders = mock.Mock(return_value={'processed': 0, 'created': 0, 'updated': 0, 'failed': 0})
        result = service.sync_all(sync_log)
        sync_log.refresh_from_db()
        self.assertTrue(result['success'])
        self.assertEqual(sync_log.status, 'COMPLETED')
        self.assertEqual(sync_log.records_processed, 2)
        self.assertEqual(sync_log.records_created, 1)
        self.assertEqual(sync_log.records_updated, 1)
        self.assertEqual(sync_log.records_failed, 0)
        self.assertIsNotNone(sync_log.completed_at)

    def test_sync_all_closes_log_on_error(self):
        config = mock.Mock()
        service = AdministraNETSyncService(config)
        sync_log = SyncLog.objects.create(sync_type='PRODUCTS', status='PENDING')
        # Forzar excepción
        service.sync_products = mock.Mock(side_effect=Exception('Fallo de prueba'))
        service.sync_stock = mock.Mock(return_value={'processed': 0, 'created': 0, 'updated': 0, 'failed': 0})
        service.sync_customers = mock.Mock(return_value={'processed': 0, 'created': 0, 'updated': 0, 'failed': 0})
        service.sync_orders = mock.Mock(return_value={'processed': 0, 'created': 0, 'updated': 0, 'failed': 0})
        result = service.sync_all(sync_log)
        sync_log.refresh_from_db()
        self.assertFalse(result['success'])
        self.assertEqual(sync_log.status, 'FAILED')
        self.assertTrue('Fallo de prueba' in sync_log.error_message or 'Error en sincronización completa' in sync_log.error_message)
        self.assertIsNotNone(sync_log.completed_at) 