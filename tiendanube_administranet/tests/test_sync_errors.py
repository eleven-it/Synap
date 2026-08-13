"""Tests clasificación de errores sync Tienda Nube ↔ AdministraNET."""

import json

from django.test import SimpleTestCase

from tiendanube_administranet.services.sync_errors import (
    SyncErrorKind,
    classify_tiendanube_response,
    classify_webhook_error,
    should_retry_webhook_failure,
)


class ClassifyTiendanubeResponseTests(SimpleTestCase):
    def test_http_402_es_not_configured(self):
        self.assertEqual(
            classify_tiendanube_response(402),
            SyncErrorKind.NOT_CONFIGURED,
        )

    def test_http_503_es_transient(self):
        self.assertEqual(
            classify_tiendanube_response(503),
            SyncErrorKind.TRANSIENT_FAILURE,
        )

    def test_http_429_es_transient(self):
        self.assertEqual(
            classify_tiendanube_response(429),
            SyncErrorKind.TRANSIENT_FAILURE,
        )


class ClassifyWebhookErrorTests(SimpleTestCase):
    def test_json_invalido_es_invalid_data(self):
        try:
            json.loads('{invalid')
        except json.JSONDecodeError as exc:
            kind = classify_webhook_error(exc)
        else:
            self.fail('Se esperaba JSONDecodeError')

        self.assertEqual(kind, SyncErrorKind.INVALID_DATA)

    def test_http_402_via_status_es_not_configured(self):
        self.assertEqual(
            classify_webhook_error(Exception('plan limit'), http_status=402),
            SyncErrorKind.NOT_CONFIGURED,
        )

    def test_http_503_via_status_es_transient(self):
        self.assertEqual(
            classify_webhook_error(Exception('service unavailable'), http_status=503),
            SyncErrorKind.TRANSIENT_FAILURE,
        )


class ShouldRetryWebhookFailureTests(SimpleTestCase):
    def test_transient_permite_retry(self):
        self.assertTrue(should_retry_webhook_failure(http_status=503))

    def test_not_configured_no_retry(self):
        self.assertFalse(should_retry_webhook_failure(http_status=402))

    def test_invalid_data_no_retry(self):
        self.assertFalse(
            should_retry_webhook_failure(
                exc=json.JSONDecodeError('msg', 'doc', 0),
            )
        )
