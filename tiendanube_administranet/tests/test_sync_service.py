"""Tests unitarios — sync_customer_to_adminet y skip reciente."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from tiendanube_administranet.models import CustomerMapping
from tiendanube_administranet.services.sync_service import (
    SYNC_SKIP_MINUTES,
    TiendanubeAdministraNETSyncService,
)


class SyncCustomerToAdminetTests(SimpleTestCase):
    def _mapping(self, **kwargs):
        defaults = {
            'tiendanube_id': 100,
            'tiendanube_email': 'test@example.com',
            'sync_enabled': True,
            'adminet_codigo': None,
        }
        defaults.update(kwargs)
        return CustomerMapping(**defaults)

    def test_skip_si_sincronizado_recientemente(self):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        mapping = self._mapping(last_synced=timezone.now())
        self.assertTrue(svc._should_skip_recent_sync(mapping))

    def test_no_skip_si_antiguo(self):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        mapping = self._mapping(
            last_synced=timezone.now() - timedelta(minutes=SYNC_SKIP_MINUTES + 1)
        )
        self.assertFalse(svc._should_skip_recent_sync(mapping))

    def test_sync_customer_to_adminet_omite_sin_cambios_tn(self):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        updated = timezone.now() - timedelta(days=1)
        mapping = self._mapping(
            sync_status=CustomerMapping.SyncStatus.SYNCED,
            tiendanube_updated_at=updated,
        )
        svc.tiendanube_service = MagicMock()
        svc.tiendanube_service.get_customer.return_value = {
            'success': True,
            'customer': {'updated_at': updated.isoformat()},
        }
        ok, msg = svc.sync_customer_to_adminet(mapping)
        self.assertTrue(ok)
        self.assertIn('Omitido', msg)

    def test_sin_tiendanube_id_falla(self):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        ok, msg = svc.sync_customer_to_adminet(self._mapping(tiendanube_id=None))
        self.assertFalse(ok)
        self.assertIn('tiendanube_id', msg)

    def test_sync_disabled_bloquea_sin_force(self):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        ok, msg = svc.sync_customer_to_adminet(
            self._mapping(sync_enabled=False), force=False
        )
        self.assertFalse(ok)
        self.assertIn('deshabilitada', msg)

    def test_force_omite_check_sync_disabled(self):
        svc = TiendanubeAdministraNETSyncService.__new__(TiendanubeAdministraNETSyncService)
        mapping = self._mapping(sync_enabled=False)
        mapping.pk = 1
        mapping.save = MagicMock()
        svc.tiendanube_service = MagicMock()
        svc.tiendanube_service.get_customer.return_value = {
            'success': False,
            'message': 'fallo TN simulado',
        }
        ok, msg = svc.sync_customer_to_adminet(mapping, force=True)
        self.assertFalse(ok)
        self.assertNotIn('deshabilitada', msg.lower())
        self.assertIn('fallo TN simulado', msg)
