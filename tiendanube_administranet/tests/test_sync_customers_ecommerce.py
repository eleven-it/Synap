"""Tests sync AdministraNET → Tienda Nube con cliente_ecommerce=Si."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from tiendanube_administranet.models import (
    AdministraNETConfig,
    CustomerMapping,
    TiendanubeConfig,
)
from tiendanube_administranet.services.sync_service import TiendanubeAdministraNETSyncService


class AdminetEcommerceCustomerHelpersTests(SimpleTestCase):
    def test_is_adminet_ecommerce_customer_si(self):
        self.assertTrue(
            TiendanubeAdministraNETSyncService._is_adminet_ecommerce_customer(
                {'cliente_ecommerce': 'Si'}
            )
        )

    def test_is_adminet_ecommerce_customer_no(self):
        self.assertFalse(
            TiendanubeAdministraNETSyncService._is_adminet_ecommerce_customer(
                {'cliente_ecommerce': 'No'}
            )
        )

    def test_customer_email_fallback(self):
        email = TiendanubeAdministraNETSyncService._customer_email_for_tiendanube(
            {'Codigo': 10, 'Email': ''}
        )
        self.assertEqual(email, 'adminet_10@noemail.local')

    def test_customer_email_real(self):
        email = TiendanubeAdministraNETSyncService._customer_email_for_tiendanube(
            {'Codigo': 10, 'Email': 'cliente@example.com'}
        )
        self.assertEqual(email, 'cliente@example.com')


class PushAdminetCustomerToTiendanubeTests(TestCase):
    def setUp(self):
        self.tn_cfg = TiendanubeConfig.objects.create(
            store_id='6359148',
            access_token='token-test',
            is_active=True,
        )
        self.an_cfg = AdministraNETConfig.objects.create(
            database='administranet74',
            is_active=True,
        )

    def _svc(self):
        with patch.object(
            TiendanubeAdministraNETSyncService, '_ensure_webhooks_configured'
        ):
            return TiendanubeAdministraNETSyncService(
                tiendanube_config=self.tn_cfg,
                adminet_config=self.an_cfg,
                base_empresa='administranet74',
            )

    def test_crea_en_tiendanube_y_persiste_id(self):
        svc = self._svc()
        customer = {
            'Codigo': 99,
            'nombre_cliente': 'Cliente Test',
            'Email': 'test@example.com',
            'CUIT': '20123456789',
            'telefono': '111',
            'Calle': 'Calle',
            'NroCalle': '1',
            'cliente_ecommerce': 'Si',
        }
        svc.tiendanube_service.find_customer_by_email = MagicMock(
            return_value={'success': True, 'customer': None}
        )
        svc.tiendanube_service.create_customer = MagicMock(
            return_value={'success': True, 'customer': {'id': 555001}}
        )
        svc.tiendanube_service.update_customer = MagicMock()
        svc.adminet_service.update_customer_tiendanube_id = MagicMock(
            return_value={'success': True}
        )

        ok, msg, tn_id, mapping = svc._push_adminet_customer_to_tiendanube(customer)

        self.assertTrue(ok)
        self.assertEqual(tn_id, 555001)
        self.assertIn('creado', msg)
        svc.tiendanube_service.create_customer.assert_called_once()
        svc.adminet_service.update_customer_tiendanube_id.assert_called_once_with(99, 555001)
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.tiendanube_id, 555001)
        self.assertEqual(mapping.adminet_codigo, 99)
        self.assertEqual(mapping.tiendanube_name, 'Cliente Test')
        self.assertEqual(mapping.tiendanube_first_name, 'Cliente')
        self.assertEqual(mapping.tiendanube_last_name, 'Test')
        self.assertEqual(mapping.display_name, 'Cliente Test')

    def test_actualiza_si_ya_tiene_id_tiendanube(self):
        svc = self._svc()
        customer = {
            'Codigo': 10,
            'nombre_cliente': 'Cliente Existente',
            'Email': 'existente@example.com',
            'id_tiendanube': 236564352,
            'cliente_ecommerce': 'Si',
        }
        svc.tiendanube_service.update_customer = MagicMock(
            return_value={'success': True, 'customer': {'id': 236564352}}
        )
        svc.tiendanube_service.create_customer = MagicMock()
        svc.adminet_service.update_customer_tiendanube_id = MagicMock()

        ok, msg, tn_id, _ = svc._push_adminet_customer_to_tiendanube(customer)

        self.assertTrue(ok)
        self.assertEqual(tn_id, 236564352)
        self.assertIn('actualizado', msg)
        svc.tiendanube_service.update_customer.assert_called_once()
        svc.tiendanube_service.create_customer.assert_not_called()
        svc.adminet_service.update_customer_tiendanube_id.assert_not_called()

    def test_rechaza_sin_cliente_ecommerce(self):
        svc = self._svc()
        customer = {'Codigo': 1, 'cliente_ecommerce': 'No'}
        ok, msg, tn_id, mapping = svc._push_adminet_customer_to_tiendanube(customer)
        self.assertFalse(ok)
        self.assertIn('cliente_ecommerce', msg)
        self.assertIsNone(tn_id)

    @patch.object(TiendanubeAdministraNETSyncService, '_push_adminet_customer_to_tiendanube')
    def test_sync_masiva_filtra_cliente_ecommerce(self, mock_push):
        svc = self._svc()
        mock_push.return_value = (True, 'ok', 1, None)
        svc.adminet_service.get_customers = MagicMock(
            return_value={
                'success': True,
                'data': [{'Codigo': 1, 'cliente_ecommerce': 'Si'}],
            }
        )

        result = svc.sync_customers_from_adminet()

        svc.adminet_service.get_customers.assert_called_once_with(
            limit=None,
            cliente_ecommerce='Si',
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['successful'], 1)
        mock_push.assert_called_once()
