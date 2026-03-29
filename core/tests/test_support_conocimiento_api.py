"""Tests de autenticación JWT para GET /core/api/support/conocimiento/."""
import jwt
from django.test import Client, TestCase, override_settings


class SupportConocimientoApiAuthTests(TestCase):
    """Valida SUPPORT_SYNAP_JWT_SECRET y Bearer HS256 según ENVIRONMENT."""

    url = '/core/api/support/conocimiento/'

    def setUp(self):
        self.client = Client()

    @override_settings(ENVIRONMENT='production', SUPPORT_SYNAP_JWT_SECRET='')
    def test_production_sin_secret_responde_503(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 503)
        data = r.json()
        self.assertIn('error', data)

    @override_settings(ENVIRONMENT='production', SUPPORT_SYNAP_JWT_SECRET='secreto_test')
    def test_production_sin_bearer_responde_401(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 401)

    @override_settings(ENVIRONMENT='production', SUPPORT_SYNAP_JWT_SECRET='secreto_test')
    def test_production_token_invalido_responde_401(self):
        r = self.client.get(self.url, HTTP_AUTHORIZATION='Bearer no-es-un-jwt')
        self.assertEqual(r.status_code, 401)

    @override_settings(ENVIRONMENT='production', SUPPORT_SYNAP_JWT_SECRET='secreto_test')
    def test_production_jwt_valido_responde_200(self):
        token = jwt.encode(
            {'sub': 'support-service', 'exp': 9_999_999_999},
            'secreto_test',
            algorithm='HS256',
        )
        if isinstance(token, bytes):
            token = token.decode()
        r = self.client.get(self.url, HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        self.assertIn('items', r.json())

    @override_settings(ENVIRONMENT='development', SUPPORT_SYNAP_JWT_SECRET='', DEBUG=True)
    def test_desarrollo_sin_secret_y_debug_permite_sin_token(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertIn('items', r.json())

    @override_settings(ENVIRONMENT='development', SUPPORT_SYNAP_JWT_SECRET='', DEBUG=False)
    def test_desarrollo_sin_secret_sin_debug_exige_config(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 503)
        self.assertIn('error', r.json())

    @override_settings(ENVIRONMENT='development', SUPPORT_SYNAP_JWT_SECRET='secreto_test')
    def test_desarrollo_con_secret_exige_jwt_valido(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 401)
        token = jwt.encode(
            {'sub': 'support-service', 'exp': 9_999_999_999},
            'secreto_test',
            algorithm='HS256',
        )
        if isinstance(token, bytes):
            token = token.decode()
        r2 = self.client.get(self.url, HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r2.status_code, 200)
        self.assertIn('items', r2.json())
