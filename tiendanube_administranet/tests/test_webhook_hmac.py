"""Tests HMAC webhooks Nuvemshop."""

import hmac
import hashlib

from django.test import SimpleTestCase

from tiendanube_administranet.services.webhook_service import WebhookProcessor


class WebhookHmacTests(SimpleTestCase):
    def test_verify_hmac_hex_oficial(self):
        secret = 'app-secret-test'
        body = '{"store_id":1,"event":"order/paid","id":99}'
        expected = hmac.new(
            secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        self.assertTrue(WebhookProcessor.verify_hmac_signature(body, expected, secret))

    def test_rechaza_firma_invalida(self):
        self.assertFalse(
            WebhookProcessor.verify_hmac_signature('{}', 'invalid', 'secret')
        )
