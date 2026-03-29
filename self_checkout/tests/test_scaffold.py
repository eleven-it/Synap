"""
Tests smoke para EPIC 3 DoD: ruta kiosco, endpoint API health.
"""
from django.test import TestCase, override_settings
from django.urls import reverse, resolve


class ScaffoldTests(TestCase):
    """Verifica que el scaffold del módulo esté correcto."""

    @override_settings(SELF_CHECKOUT_ENABLED=True)
    def test_kiosco_route_resolves(self):
        """La ruta /self-checkout/kiosco/<kiosk_id>/ debe resolver."""
        url = reverse('self_checkout:kiosco', kwargs={'kiosk_id': 'k01'})
        self.assertEqual(url, '/self-checkout/kiosco/k01/')
        resolver = resolve('/self-checkout/kiosco/k01/')
        self.assertEqual(resolver.view_name, 'self_checkout:kiosco')

    @override_settings(SELF_CHECKOUT_ENABLED=True)
    def test_api_health_resolves_and_returns_200(self):
        """El endpoint GET /api/self-checkout/health/ debe resolver y retornar 200."""
        url = reverse('self-checkout-api:health')
        self.assertEqual(url, '/api/self-checkout/health/')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('status'), 'ok')
        self.assertEqual(response.json().get('module'), 'self_checkout')

    @override_settings(SELF_CHECKOUT_ENABLED=False)
    def test_returns_404_when_disabled(self):
        """Cuando SELF_CHECKOUT_ENABLED=False, el middleware retorna 404."""
        response = self.client.get('/self-checkout/kiosco/k01/')
        self.assertEqual(response.status_code, 404)
