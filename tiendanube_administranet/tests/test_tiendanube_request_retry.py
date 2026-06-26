"""Tests reintentos HTTP en TiendanubeService._request."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from tiendanube_administranet.services.rate_limit import reset_rate_limit_state
from tiendanube_administranet.services.tiendanube_service import TiendanubeService


def _mock_http_response(status_code, reset_ms=None, remaining=None):
    response = MagicMock()
    response.status_code = status_code
    headers = {}
    if reset_ms is not None:
        headers['x-rate-limit-reset'] = str(reset_ms)
    if remaining is not None:
        headers['x-rate-limit-remaining'] = str(remaining)
    response.headers = headers
    return response


class TiendanubeRequestRetryTests(SimpleTestCase):
    def setUp(self):
        reset_rate_limit_state()
        self.config = MagicMock()
        self.config.store_id = '6359148'
        self.config.access_token = 'token-test'
        self.service = TiendanubeService(self.config)

    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch(
        'tiendanube_administranet.services.tiendanube_service.wait_after_rate_limit_response'
    )
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_429_reintenta_hasta_exito(
        self, mock_wait, mock_wait_after, mock_request,
    ):
        mock_request.side_effect = [
            _mock_http_response(429, reset_ms=100),
            _mock_http_response(200, remaining=39),
        ]

        response = self.service._request('GET', 'https://api.test/products')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)
        mock_wait_after.assert_called_once()

    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch(
        'tiendanube_administranet.services.tiendanube_service.wait_after_rate_limit_response'
    )
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_429_agota_reintentos_y_devuelve_ultima_respuesta(
        self, mock_wait, mock_wait_after, mock_request,
    ):
        mock_request.return_value = _mock_http_response(429, reset_ms=50)

        with override_settings(
            NUVEMSHOP_MAX_RETRIES=2,
            NUVEMSHOP_MAX_CONSECUTIVE_429=10,
        ):
            response = self.service._request('GET', 'https://api.test/products')

        self.assertEqual(response.status_code, 429)
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_wait_after.call_count, 2)

    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch(
        'tiendanube_administranet.services.tiendanube_service.wait_after_rate_limit_response'
    )
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_429_consecutivos_abandonan_antes_de_max_retries(
        self, mock_wait, mock_wait_after, mock_request,
    ):
        mock_request.return_value = _mock_http_response(429, reset_ms=10)

        with override_settings(
            NUVEMSHOP_MAX_RETRIES=10,
            NUVEMSHOP_MAX_CONSECUTIVE_429=3,
        ):
            response = self.service._request('GET', 'https://api.test/products')

        self.assertEqual(response.status_code, 429)
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_wait_after.call_count, 2)

    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch(
        'tiendanube_administranet.services.tiendanube_service.wait_after_rate_limit_response'
    )
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_503_reintenta_con_backoff(
        self, mock_wait, mock_wait_after, mock_request,
    ):
        mock_request.side_effect = [
            _mock_http_response(503),
            _mock_http_response(200),
        ]

        response = self.service._request('GET', 'https://api.test/products')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)
        mock_wait_after.assert_called_once()

    @patch('tiendanube_administranet.services.rate_limit.time.sleep')
    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_429_invoca_sleep_via_wait_after(
        self, mock_wait, mock_request, mock_sleep,
    ):
        mock_request.side_effect = [
            _mock_http_response(429, reset_ms=250),
            _mock_http_response(200),
        ]

        self.service._request('GET', 'https://api.test/products')

        mock_sleep.assert_called()
        delays = [call.args[0] for call in mock_sleep.call_args_list]
        self.assertIn(0.25, delays)

    @patch('tiendanube_administranet.services.tiendanube_service.requests.request')
    @patch('tiendanube_administranet.services.tiendanube_service.wait_for_rate_limit')
    def test_respuesta_ok_sin_reintentos(self, mock_wait, mock_request):
        mock_request.return_value = _mock_http_response(200, remaining=40)

        response = self.service._request('GET', 'https://api.test/products')

        self.assertEqual(response.status_code, 200)
        mock_request.assert_called_once()
        self.assertEqual(mock_wait.call_count, 1)
