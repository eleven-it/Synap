"""Tests de vistas de eliminación de asientos contables."""
import json
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

    @patch("legacy_db.services.cont_eliminacion_asientos_service.eliminar_asientos")
    def test_post_eliminar_json_clasico(self, mock_eliminar):
        mock_eliminar.return_value = {
            "ok": True,
            "lote_id": "L1",
            "backups": {},
            "asientos_eliminados": 1,
        }
        request = self.factory.post(
            "/contabilidad/auditoria/asientos/eliminar/",
            data='{"asientos":[{"id_ejercicio":1,"nro_asiento":79}]}',
            content_type="application/json",
        )
        request.user = _UserConPermisoCorregir()
        self._attach_session(request)

        response = auditoria_asientos_eliminar_ejecutar(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertTrue(body["ok"])
        mock_eliminar.assert_called_once()

    @patch("legacy_db.services.cont_eliminacion_asientos_service._eliminar_asientos_iter")
    def test_post_eliminar_stream_ndjson(self, mock_iter):
        mock_iter.return_value = iter(
            [
                {"type": "progress", "phase": "backup", "current": 0, "total": 1, "label": ""},
                {
                    "type": "result",
                    "payload": {
                        "ok": True,
                        "lote_id": "L1",
                        "backups": {},
                        "asientos_eliminados": 1,
                    },
                },
            ]
        )
        request = self.factory.post(
            "/contabilidad/auditoria/asientos/eliminar/",
            data='{"asientos":[{"id_ejercicio":1,"nro_asiento":79}],"stream":true}',
            content_type="application/json",
            HTTP_ACCEPT="application/x-ndjson",
        )
        request.user = _UserConPermisoCorregir()
        self._attach_session(request)

        response = auditoria_asientos_eliminar_ejecutar(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("application/x-ndjson", response["Content-Type"])
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertEqual(response["X-Accel-Buffering"], "no")

        lineas = [ln for ln in response.streaming_content if ln]
        eventos = [json.loads(ln.decode("utf-8")) for ln in lineas]
        self.assertEqual(eventos[0]["type"], "progress")
        self.assertEqual(eventos[-1]["type"], "done")
        self.assertTrue(eventos[-1]["ok"])


class AsientosEliminarTemplateTestCase(SimpleTestCase):
    def test_template_contiene_elementos_ui(self):
        html = (_TEMPLATES / "auditoria_asientos_eliminar.html").read_text(encoding="utf-8")
        self.assertIn("Eliminar asientos", html)
        self.assertIn('type="checkbox"', html)
        self.assertIn("auditoriaAsientosEliminar", html)
        self.assertIn("synapShowPostLoadingProgress", html)
        self.assertIn("synapUpdatePostLoadingProgress", html)
        self.assertIn("application/x-ndjson", html)
        self.assertIn("stream: true", html)
        self.assertIn("previewCargando", html)
        self.assertIn("Calculando impacto", html)
        self.assertIn("synapHidePostLoading()", html)
        self.assertNotIn("synapHidePostLoadingProgress", html)
        self.assertNotIn("window.alert", html)
        self.assertNotIn("window.confirm", html)
        self.assertNotIn("alert(", html)
        self.assertNotIn("confirm(", html)
