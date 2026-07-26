"""Tests de vistas de eliminación de asientos contables."""
from pathlib import Path
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, SimpleTestCase
from django.urls import reverse

from contabilidad_audit.views import (
    PERMISO_CORREGIR,
    PERMISO_LEER,
    auditoria_asientos_eliminar,
    auditoria_asientos_eliminar_ejecutar,
)


def _session_user(base_empresa: str = "empresa_test"):
    return {
        "id_usuario": 1,
        "cod_usuario": "auditor",
        "base_empresa": base_empresa,
    }


class _UserConPermisoLeer:
    is_authenticated = True
    cod_usuario = "auditor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return code == PERMISO_LEER


class _UserConPermisoCorregir:
    is_authenticated = True
    cod_usuario = "auditor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return code in (PERMISO_LEER, PERMISO_CORREGIR)


class _UserSinPermiso:
    is_authenticated = True
    cod_usuario = "vendedor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return False


_TEMPLATES = Path(__file__).resolve().parent.parent / "templates" / "contabilidad_audit"


class AsientosEliminarUrlsTestCase(SimpleTestCase):
    def test_reverse_urls(self):
        self.assertEqual(
            reverse("contabilidad_audit:auditoria_asientos"),
            "/contabilidad/auditoria/asientos/",
        )
        self.assertEqual(
            reverse("contabilidad_audit:auditoria_asientos_preview"),
            "/contabilidad/auditoria/asientos/preview/",
        )
        self.assertEqual(
            reverse("contabilidad_audit:auditoria_asientos_eliminar"),
            "/contabilidad/auditoria/asientos/eliminar/",
        )


class AsientosEliminarVistasTestCase(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.session = {"user": _session_user()}

    def _attach_session(self, request):
        request.session = self.session
        setattr(request, "_messages", FallbackStorage(request))

    def test_get_sin_permiso_403(self):
        request = self.factory.get("/contabilidad/auditoria/asientos/?id_ejercicio=1")
        request.user = _UserSinPermiso()
        self._attach_session(request)
        with self.assertRaises(PermissionDenied):
            auditoria_asientos_eliminar(request)

    @patch("contabilidad_audit.views.render")
    def test_get_con_permiso_200(self, mock_render):
        from legacy_db.services import cont_eliminacion_asientos_service

        mock_render.return_value.status_code = 200

        request = self.factory.get("/contabilidad/auditoria/asientos/?id_ejercicio=1")
        request.user = _UserConPermisoLeer()
        self._attach_session(request)

        with patch.object(cont_eliminacion_asientos_service, "listar_conceptos", return_value=[]):
            auditoria_asientos_eliminar(request)

        mock_render.assert_called_once()
        self.assertEqual(mock_render.call_args[0][1], "contabilidad_audit/auditoria_asientos_eliminar.html")

    @patch("contabilidad_audit.views.render")
    def test_get_sin_ejercicio_no_muestra_error_obligatorio(self, mock_render):
        """Abrir la pantalla vacía no debe mostrar error de id_ejercicio."""
        mock_render.return_value.status_code = 200
        request = self.factory.get("/contabilidad/auditoria/asientos/")
        request.user = _UserConPermisoLeer()
        self._attach_session(request)

        auditoria_asientos_eliminar(request)

        ctx = mock_render.call_args[0][2]
        self.assertNotEqual(
            ctx.get("error_parametros"),
            "El parámetro id_ejercicio es obligatorio.",
        )
        self.assertFalse(ctx.get("error_parametros"))

    def test_post_eliminar_sin_permiso_403(self):
        request = self.factory.post(
            "/contabilidad/auditoria/asientos/eliminar/",
            data='{"asientos":[{"id_ejercicio":1,"nro_asiento":79}]}',
            content_type="application/json",
        )
        request.user = _UserSinPermiso()
        self._attach_session(request)
        with self.assertRaises(PermissionDenied):
            auditoria_asientos_eliminar_ejecutar(request)


class AsientosEliminarTemplateTestCase(SimpleTestCase):
    def test_template_contiene_elementos_ui(self):
        html = (_TEMPLATES / "auditoria_asientos_eliminar.html").read_text(encoding="utf-8")
        self.assertIn("Eliminar asientos", html)
        self.assertIn('type="checkbox"', html)
        self.assertIn("auditoriaAsientosEliminar", html)
        self.assertIn("synapShowPostLoadingProgress", html)
        self.assertNotIn("window.alert", html)
        self.assertNotIn("window.confirm", html)
        self.assertNotIn("alert(", html)
        self.assertNotIn("confirm(", html)
