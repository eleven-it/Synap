"""Tests del servicio de correo saliente (SystemConfiguration + fallback settings)."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from core.models import SystemConfiguration
from core.services.outbound_email import (
    guardar_config_correo_saliente,
    leer_config_correo_saliente,
    probar_conexion_correo_saliente,
    resolver_parametros_smtp,
)


class TestOutboundEmailLeerGuardar(TestCase):
    def setUp(self):
        SystemConfiguration.objects.filter(key__startswith="email.outbound.").delete()

    def test_leer_defaults_sin_filas(self):
        cfg = leer_config_correo_saliente()
        self.assertFalse(cfg["enabled"])
        self.assertEqual(cfg["port"], 587)
        self.assertTrue(cfg["use_tls"])
        self.assertFalse(cfg["use_ssl"])
        self.assertEqual(cfg["timeout"], 20)
        self.assertFalse(cfg["password_set"])
        self.assertEqual(cfg["password"], "")

    def test_guardar_y_leer_enmascara_password(self):
        guardar_config_correo_saliente(
            {
                "enabled": True,
                "host": "smtp.example.com",
                "port": 465,
                "use_tls": False,
                "use_ssl": True,
                "username": "user@test.com",
                "password": "secreto123",
                "from_email": "noreply@test.com",
                "timeout": 30,
            }
        )
        cfg = leer_config_correo_saliente()
        self.assertTrue(cfg["enabled"])
        self.assertEqual(cfg["host"], "smtp.example.com")
        self.assertEqual(cfg["port"], 465)
        self.assertFalse(cfg["use_tls"])
        self.assertTrue(cfg["use_ssl"])
        self.assertEqual(cfg["username"], "user@test.com")
        self.assertTrue(cfg["password_set"])
        self.assertEqual(cfg["password"], "")
        self.assertEqual(cfg["from_email"], "noreply@test.com")
        self.assertEqual(cfg["timeout"], 30)

    def test_password_vacio_no_borra_existente(self):
        guardar_config_correo_saliente(
            {"enabled": True, "host": "smtp.test.local", "password": "primera"}
        )
        guardar_config_correo_saliente({"password": ""})
        cfg = leer_config_correo_saliente()
        self.assertTrue(cfg["password_set"])
        params = resolver_parametros_smtp()
        self.assertEqual(params["password"], "primera")

    @override_settings(
        EMAIL_HOST="fallback.smtp.local",
        EMAIL_PORT=2525,
        EMAIL_HOST_USER="fb_user",
        EMAIL_HOST_PASSWORD="fb_pass",
        EMAIL_USE_TLS=False,
        EMAIL_USE_SSL=True,
        DEFAULT_FROM_EMAIL="fallback@local",
        EMAIL_TIMEOUT=15,
    )
    def test_resolver_usa_settings_si_db_inactiva(self):
        params = resolver_parametros_smtp()
        self.assertEqual(params["source"], "settings")
        self.assertEqual(params["host"], "fallback.smtp.local")
        self.assertEqual(params["port"], 2525)
        self.assertEqual(params["username"], "fb_user")
        self.assertEqual(params["password"], "fb_pass")
        self.assertFalse(params["use_tls"])
        self.assertTrue(params["use_ssl"])
        self.assertEqual(params["from_email"], "fallback@local")
        self.assertEqual(params["timeout"], 15)

    def test_resolver_usa_db_si_enabled_y_host(self):
        guardar_config_correo_saliente(
            {
                "enabled": True,
                "host": "db.smtp.local",
                "port": 587,
                "username": "db_user",
                "password": "db_pass",
                "from_email": "db@local",
            }
        )
        params = resolver_parametros_smtp()
        self.assertEqual(params["source"], "db")
        self.assertEqual(params["host"], "db.smtp.local")
        self.assertEqual(params["password"], "db_pass")
        self.assertEqual(params["from_email"], "db@local")


class TestProbarConexionCorreoSaliente(SimpleTestCase):
    @patch("core.services.outbound_email.correo_saliente_configurado", return_value=False)
    def test_sin_config_devuelve_error(self, _mock_cfg):
        result = probar_conexion_correo_saliente()
        self.assertFalse(result["ok"])
        self.assertIn("no configurado", result["message"].lower())

    @patch("core.services.outbound_email.get_connection_correo_saliente")
    @patch("core.services.outbound_email.correo_saliente_configurado", return_value=True)
    def test_conexion_ok_sin_envio(self, _mock_cfg, mock_conn_factory):
        conn = MagicMock()
        mock_conn_factory.return_value = conn
        result = probar_conexion_correo_saliente()
        self.assertTrue(result["ok"])
        conn.open.assert_called_once()
        conn.close.assert_called_once()
