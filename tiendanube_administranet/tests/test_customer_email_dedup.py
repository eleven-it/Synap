"""Tests deduplicación de clientes por email antes de crear en Tienda Nube."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from tiendanube_administranet.models import (
    AdministraNETConfig,
    CustomerMapping,
    TiendanubeConfig,
)
from tiendanube_administranet.services.sync_service import TiendanubeAdministraNETSyncService


class CustomerEmailDedupHelperTests(SimpleTestCase):
    def test_email_real_permite_dedup(self):
        self.assertTrue(
            TiendanubeAdministraNETSyncService._customer_email_is_real_for_dedup(
                'cliente@example.com'
            )
        )

    def test_email_fallback_no_permite_dedup(self):
        self.assertFalse(
            TiendanubeAdministraNETSyncService._customer_email_is_real_for_dedup(
                'adminet_42@noemail.local'
            )
        )


class PushCustomerEmailDedupTests(TestCase):
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

    def test_dedup_encontrado_usa_update_y_persiste_id(self):
        svc = self._svc()
        customer = {
            'Codigo': 77,
            'nombre_cliente': 'Cliente Existente TN',
            'Email': 'existente@example.com',
            'cliente_ecommerce': 'Si',
        }
        svc.tiendanube_service.find_customer_by_email = MagicMock(
            return_value={
                'success': True,
                'found': True,
                'customer': {'id': 888001, 'email': 'existente@example.com'},
            }
        )
        svc.tiendanube_service.update_customer = MagicMock(
            return_value={'success': True, 'customer': {'id': 888001}}
        )
        svc.tiendanube_service.create_customer = MagicMock()
        svc.adminet_service.update_customer_tiendanube_id = MagicMock(
            return_value={'success': True}
        )

        ok, msg, tn_id, mapping = svc._push_adminet_customer_to_tiendanube(customer)

        self.assertTrue(ok)
        self.assertEqual(tn_id, 888001)
        self.assertIn('actualizado', msg)
        svc.tiendanube_service.find_customer_by_email.assert_called_once_with(
            'existente@example.com'
        )
        svc.tiendanube_service.create_customer.assert_not_called()
        svc.tiendanube_service.update_customer.assert_called_once()
        svc.adminet_service.update_customer_tiendanube_id.assert_called_once_with(77, 888001)
        self.assertEqual(customer['id_tiendanube'], 888001)
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping.tiendanube_id, 888001)
        self.assertEqual(mapping.adminet_codigo, 77)

    def test_dedup_no_encontrado_crea_cliente(self):
        svc = self._svc()
        customer = {
            'Codigo': 88,
            'nombre_cliente': 'Cliente Nuevo',
            'Email': 'nuevo@example.com',
            'cliente_ecommerce': 'Si',
        }
        svc.tiendanube_service.find_customer_by_email = MagicMock(
            return_value={'success': True, 'found': False, 'customer': None}
        )
        svc.tiendanube_service.create_customer = MagicMock(
            return_value={'success': True, 'customer': {'id': 999002}}
        )
        svc.tiendanube_service.update_customer = MagicMock()
        svc.adminet_service.update_customer_tiendanube_id = MagicMock(
            return_value={'success': True}
        )

        ok, msg, tn_id, mapping = svc._push_adminet_customer_to_tiendanube(customer)

        self.assertTrue(ok)
        self.assertEqual(tn_id, 999002)
        self.assertIn('creado', msg)
        svc.tiendanube_service.find_customer_by_email.assert_called_once_with(
            'nuevo@example.com'
        )
        svc.tiendanube_service.create_customer.assert_called_once()
        svc.tiendanube_service.update_customer.assert_not_called()
        svc.adminet_service.update_customer_tiendanube_id.assert_called_once_with(88, 999002)
        self.assertEqual(mapping.tiendanube_id, 999002)

    def test_fallback_email_salta_dedup_y_crea(self):
        svc = self._svc()
        customer = {
            'Codigo': 55,
            'nombre_cliente': 'Sin Email',
            'Email': '',
            'cliente_ecommerce': 'Si',
        }
        svc.tiendanube_service.find_customer_by_email = MagicMock()
        svc.tiendanube_service.create_customer = MagicMock(
            return_value={'success': True, 'customer': {'id': 777003}}
        )
        svc.tiendanube_service.update_customer = MagicMock()
        svc.adminet_service.update_customer_tiendanube_id = MagicMock(
            return_value={'success': True}
        )

        ok, msg, tn_id, _ = svc._push_adminet_customer_to_tiendanube(customer)

        self.assertTrue(ok)
        self.assertEqual(tn_id, 777003)
        self.assertIn('creado', msg)
        svc.tiendanube_service.find_customer_by_email.assert_not_called()
        svc.tiendanube_service.create_customer.assert_called_once()
        create_payload = svc.tiendanube_service.create_customer.call_args[0][0]
        self.assertEqual(create_payload['email'], 'adminet_55@noemail.local')

    def test_dedup_error_busqueda_retorna_fallo(self):
        svc = self._svc()
        customer = {
            'Codigo': 66,
            'nombre_cliente': 'Cliente',
            'Email': 'error@example.com',
            'cliente_ecommerce': 'Si',
        }
        svc.tiendanube_service.find_customer_by_email = MagicMock(
            return_value={'success': False, 'message': 'Error API TN'}
        )
        svc.tiendanube_service.create_customer = MagicMock()
        svc.tiendanube_service.update_customer = MagicMock()

        ok, msg, tn_id, mapping = svc._push_adminet_customer_to_tiendanube(customer)

        self.assertFalse(ok)
        self.assertEqual(msg, 'Error API TN')
        self.assertIsNone(tn_id)
        svc.tiendanube_service.create_customer.assert_not_called()
        svc.tiendanube_service.update_customer.assert_not_called()
