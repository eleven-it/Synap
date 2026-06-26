"""Tests rate limiter Nuvemshop."""

import time
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from tiendanube_administranet.services.rate_limit import (
    DEFAULT_MAX_CONSECUTIVE_429,
    DEFAULT_MAX_RETRIES,
    NUVEMSHOP_MAX_REQUESTS_PER_SECOND,
    reset_rate_limit_state,
    update_rate_limit_from_response,
    wait_after_rate_limit_response,
    wait_for_rate_limit,
)


def _mock_response(
    remaining=None,
    reset_ms=None,
    limit=None,
    status_code=200,
):
    response = MagicMock()
    response.status_code = status_code
    headers = {}
    if limit is not None:
        headers['x-rate-limit-limit'] = str(limit)
    if remaining is not None:
        headers['x-rate-limit-remaining'] = str(remaining)
    if reset_ms is not None:
        headers['x-rate-limit-reset'] = str(reset_ms)
    response.headers = headers
    return response


class RateLimitTests(SimpleTestCase):
    def setUp(self):
        reset_rate_limit_state()

    @patch('tiendanube_administranet.services.rate_limit.time.sleep')
    @patch('tiendanube_administranet.services.rate_limit.time.monotonic')
    def test_espera_si_llamadas_rapidas(self, mock_mono, mock_sleep):
        mock_mono.side_effect = [0.0, 0.0, 0.1, 0.1]
        wait_for_rate_limit()
        wait_for_rate_limit()
        self.assertGreaterEqual(mock_sleep.call_count, 1)

    def test_max_requests_por_segundo(self):
        self.assertEqual(NUVEMSHOP_MAX_REQUESTS_PER_SECOND, 2)

    def test_constantes_reintentos_por_defecto(self):
        self.assertEqual(DEFAULT_MAX_RETRIES, 5)
        self.assertEqual(DEFAULT_MAX_CONSECUTIVE_429, 5)

    @patch('tiendanube_administranet.services.rate_limit.time.monotonic')
    def test_update_rate_limit_from_response_guarda_remaining_y_reset(
        self, mock_mono,
    ):
        mock_mono.return_value = 100.0
        update_rate_limit_from_response(
            _mock_response(remaining=0, reset_ms=500, limit=40)
        )

        import tiendanube_administranet.services.rate_limit as rl

        self.assertEqual(rl._rate_limit_remaining, 0)
        self.assertEqual(rl._rate_limit_reset_at, 100.5)

    @patch('tiendanube_administranet.services.rate_limit.time.sleep')
    @patch('tiendanube_administranet.services.rate_limit.time.monotonic')
    def test_wait_for_rate_limit_espera_cuando_remaining_cero(
        self, mock_mono, mock_sleep,
    ):
        mock_mono.side_effect = [10.0, 10.0, 10.0, 10.0]
        update_rate_limit_from_response(
            _mock_response(remaining=0, reset_ms=2000)
        )
        wait_for_rate_limit()
        mock_sleep.assert_called()
        first_sleep = mock_sleep.call_args_list[0][0][0]
        self.assertGreater(first_sleep, 0)

    @patch('tiendanube_administranet.services.rate_limit.time.sleep')
    def test_wait_after_rate_limit_response_usa_reset_header(self, mock_sleep):
        response = _mock_response(reset_ms=1500, status_code=429)
        wait_after_rate_limit_response(response, attempt=1)
        mock_sleep.assert_called_once_with(1.5)

    @patch('tiendanube_administranet.services.rate_limit.time.sleep')
    def test_wait_after_rate_limit_response_backoff_exponencial_sin_reset(
        self, mock_sleep,
    ):
        response = _mock_response(status_code=429)
        wait_after_rate_limit_response(response, attempt=3)
        mock_sleep.assert_called_once_with(4.0)

    @override_settings(NUVEMSHOP_MAX_RETRIES=7)
    def test_get_max_retries_desde_settings(self):
        from tiendanube_administranet.services.rate_limit import get_max_retries

        self.assertEqual(get_max_retries(), 7)

    @override_settings(NUVEMSHOP_MAX_CONSECUTIVE_429=3)
    def test_get_max_consecutive_429_desde_settings(self):
        from tiendanube_administranet.services.rate_limit import (
            get_max_consecutive_429,
        )

        self.assertEqual(get_max_consecutive_429(), 3)
