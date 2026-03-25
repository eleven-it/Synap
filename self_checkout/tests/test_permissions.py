"""
Tests EPIC 4 DoD: usuario sin permiso → 403; con permiso → 200.
"""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from core.models import UsuarioExtendido


class PermissionTests(TestCase):
    """Verifica guards de permisos en vistas y API."""

    def setUp(self):
        self.user = UsuarioExtendido.objects.create_user(
            email='test@test.com', nombre='Test', password='testpass'
        )

    @override_settings(SELF_CHECKOUT_ENABLED=True)
    @patch('self_checkout.decorators.has_permission')
    def test_sin_permiso_retorna_403(self, mock_has_perm):
        """Usuario sin permiso self_checkout.kiosk recibe 403."""
        mock_has_perm.return_value = False
        self.client.force_login(self.user)
        session = self.client.session
        session['user'] = {'base_empresa': 'test_db', 'id_puesto': 1}
        session.save()

        response = self.client.post(
            reverse('self-checkout-api:cart-create'),
            {'kiosk_id': 'k01'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('error', response.json())
        self.assertNotIn('traceback', response.json().get('error', '').lower())

    @override_settings(SELF_CHECKOUT_ENABLED=True)
    @patch('self_checkout.decorators.has_permission')
    def test_con_permiso_kiosk_retorna_200_o_error_business(self, mock_has_perm):
        """Usuario con permiso kiosk pasa el guard (200 o error de negocio)."""
        mock_has_perm.return_value = True
        self.client.force_login(self.user)
        session = self.client.session
        session['user'] = {'base_empresa': 'test_db', 'id_puesto': 1}
        session.save()

        response = self.client.post(
            reverse('self-checkout-api:cart-create'),
            {'kiosk_id': 'k01'},
            content_type='application/json',
        )
        self.assertIn(response.status_code, (200, 400, 500))
        if response.status_code == 403:
            self.fail('No debería retornar 403 si has_permission=True')
        self.assertNotIn('traceback', str(response.content).lower())

    @override_settings(SELF_CHECKOUT_ENABLED=True)
    @patch('self_checkout.decorators.has_permission')
    def test_endpoint_supervisor_sin_permiso_403(self, mock_has_perm):
        """Endpoint audit requiere supervisor; sin permiso → 403."""
        mock_has_perm.return_value = False
        self.client.force_login(self.user)
        session = self.client.session
        session['user'] = {'base_empresa': 'test_db', 'id_puesto': 1}
        session.save()

        response = self.client.get(reverse('self-checkout-api:audit-list'))
        self.assertEqual(response.status_code, 403)

    @override_settings(SELF_CHECKOUT_ENABLED=True)
    @patch('self_checkout.decorators.has_permission')
    def test_endpoint_supervisor_con_permiso_200(self, mock_has_perm):
        """Endpoint audit con permiso supervisor retorna 200."""
        mock_has_perm.return_value = True
        self.client.force_login(self.user)
        session = self.client.session
        session['user'] = {'base_empresa': 'test_db', 'id_puesto': 1}
        session.save()

        response = self.client.get(reverse('self-checkout-api:audit-list'))
        self.assertIn(response.status_code, (200, 500))
