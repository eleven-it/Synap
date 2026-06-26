"""Tests de intercambio OAuth Tienda Nube."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from tiendanube_administranet.services.tiendanube_oauth import exchange_oauth_code


class TiendanubeOAuthExchangeTests(SimpleTestCase):
    def test_missing_credentials(self):
        result = exchange_oauth_code(
            app_id='',
            client_secret='',
            code='abc',
            redirect_uri='https://example.com/callback/',
        )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'missing_credentials')

    def test_successful_exchange(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'token-nuevo',
            'user_id': '999',
        }
        with patch('tiendanube_administranet.services.tiendanube_oauth.requests.post', return_value=mock_response):
            with patch(
                'tiendanube_administranet.services.tiendanube_oauth._resolve_store_id',
                return_value='6359148',
            ):
                result = exchange_oauth_code(
                    app_id='app123',
                    client_secret='secret',
                    code='code123',
                    redirect_uri='https://example.com/callback/',
                )
        self.assertTrue(result['success'])
        self.assertEqual(result['access_token'], 'token-nuevo')
        self.assertEqual(result['store_id'], '6359148')

    def test_invalid_client_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': 'invalid_client',
            'error_description': 'Client credentials were not found',
        }
        with patch('tiendanube_administranet.services.tiendanube_oauth.requests.post', return_value=mock_response):
            result = exchange_oauth_code(
                app_id='app123',
                client_secret='bad',
                code='code123',
                redirect_uri='https://example.com/callback/',
            )
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'invalid_client')
