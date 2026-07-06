"""Acceso al módulo: solo usuario cod_usuario supervisor."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from core.models import ModuleConfig
from core.module_manager import ModuleManager
from odoo_migracion.views import dashboard


@contextmanager
def _mysql_pool_mock():
    mock_conn = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_conn)
    mock_cm.__exit__ = MagicMock(return_value=None)
    with patch("core.middleware.request_scoped_mysql.get_mysql_pool") as mock_get_pool:
        mock_get_pool.return_value.get_connection.return_value = mock_cm
        yield


class SupervisorAccessTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        ModuleConfig.objects.update_or_create(
            name="odoo_migracion",
            defaults={
                "display_name": "Migración Odoo",
                "description": "test",
                "version": "1.0.0",
                "is_active": True,
            },
        )
        ModuleManager()._refresh_active_modules_from_cache_or_db(force=True)

    def _session_supervisor(self):
        session = self.client.session
        session["user"] = {
            "id_usuario": 1,
            "cod_usuario": "supervisor",
            "nombre_usuario": "Supervisor",
            "base_empresa": "administranet_test",
        }
        session.save()

    def _session_operario(self):
        session = self.client.session
        session["user"] = {
            "id_usuario": 2,
            "cod_usuario": "jperez",
            "nombre_usuario": "Juan",
            "base_empresa": "administranet_test",
        }
        session.save()

    def test_supervisor_accede_dashboard(self):
        self._session_supervisor()
        with _mysql_pool_mock():
            response = self.client.get(reverse("odoo_migracion:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_no_supervisor_decorador_403(self):
        """El decorador solo_usuario_supervisor rechaza usuarios distintos de supervisor."""
        request = self.factory.get(reverse("odoo_migracion:dashboard"))
        request.session = self.client.session
        request.session["user"] = {
            "id_usuario": 2,
            "cod_usuario": "jperez",
            "nombre_usuario": "Juan",
            "base_empresa": "administranet_test",
        }
        from core.middleware.base_middleware import get_usuario_extendiendo_desde_sesion

        request.user = get_usuario_extendiendo_desde_sesion(request)
        with self.assertRaises(PermissionDenied):
            dashboard(request)

    def test_no_supervisor_modulo_redirige_dashboard(self):
        """Sin permisos de módulo, el middleware redirige antes del decorador."""
        self._session_operario()
        with _mysql_pool_mock():
            response = self.client.get(reverse("odoo_migracion:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/core/dashboard", response.url)
