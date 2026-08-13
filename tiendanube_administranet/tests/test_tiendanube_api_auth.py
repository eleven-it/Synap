"""Smoke tests — autenticación canónica API Tienda Nube 2025-03."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from tiendanube_administranet.services.sync_errors import SyncErrorKind
from tiendanube_administranet.services.tiendanube_service import (
    NUVEMSHOP_API_VERSION,
    TiendanubeService,
    build_tiendanube_auth_headers,
    interpret_tiendanube_http_status,
)


class TiendanubeAuthHeaderTests(SimpleTestCase):
    def test_build_auth_headers_canonico(self):
        headers = build_tiendanube_auth_headers('mi-token-secreto')

        self.assertEqual(headers['Authentication'], 'bearer mi-token-secreto')
        self.assertNotIn('Authorization', headers)

    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_get_store_usa_header_authentication_bearer(
        self, _wait, mock_request,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'name': 'Tienda demo'}
        mock_request.return_value = mock_response

        config = MagicMock()
        config.store_id = '12345'
        config.access_token = 'token-smoke-test'
        svc = TiendanubeService(config)
        result = svc.get_store_info()

        self.assertTrue(result['success'])
        mock_request.assert_called_once()
        sent_headers = mock_request.call_args.kwargs['headers']
        self.assertEqual(sent_headers['Authentication'], 'bearer token-smoke-test')
        self.assertNotIn('Authorization', sent_headers)
        url = mock_request.call_args.args[1]
        self.assertIn(f'/{NUVEMSHOP_API_VERSION}/12345/store', url)


class TiendanubeHttp402Tests(SimpleTestCase):
    def test_http_402_clasifica_not_configured(self):
        meta = interpret_tiendanube_http_status(402)

        self.assertEqual(meta['kind'], SyncErrorKind.NOT_CONFIGURED)
        self.assertFalse(meta['should_retry'])

    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_http_402_no_reintenta_como_transitorio(self, _wait, mock_request):
        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.text = 'Payment Required'
        mock_request.return_value = mock_response

        config = MagicMock()
        config.store_id = '999'
        config.access_token = 'token'
        svc = TiendanubeService(config)
        response = svc._request('GET', 'https://api.test/store')

        self.assertEqual(response.status_code, 402)
        mock_request.assert_called_once()
