from unittest.mock import MagicMock, patch

from django.test import TestCase

from odoo_migracion.models import OdooConnection
from odoo_migracion.services.crypto import decrypt_secret, encrypt_secret
from odoo_migracion.services.odoo_client import OdooJson2Client


class CryptoTest(TestCase):
    def test_roundtrip(self):
        plain = "test-api-key-12345"
        enc = encrypt_secret(plain)
        self.assertNotEqual(enc, plain)
        self.assertEqual(decrypt_secret(enc), plain)


class OdooJson2ClientTest(TestCase):
    def setUp(self):
        self.conn = OdooConnection.objects.create(
            nombre="Test",
            base_empresa="administranet_test",
            base_url="https://odoo.test",
            database="odoo_db",
        )
        self.conn.set_api_key("secret-key")
        self.conn.save()

    @patch("odoo_migracion.services.odoo_client.requests.post")
    def test_smoke_test(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'{"lang": "es_AR"}'
        mock_resp.json.return_value = {"lang": "es_AR"}
        mock_post.return_value = mock_resp

        client = OdooJson2Client(self.conn)
        result = client.smoke_test()
        self.assertTrue(result["ok"])
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("/json/2/res.users/context_get", args[0])
        self.assertEqual(kwargs["headers"]["Authorization"], "bearer secret-key")
