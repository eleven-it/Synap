"""Vistas Mtrix: permisos, triggered_by y contrato de preview."""

from pathlib import Path
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from mtrix.models import MtrixJob
from mtrix.views import generar, hub


class _UserConPermiso:
    is_authenticated = True
    is_superuser = False
    cod_usuario = "operador_mtrix"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return code.startswith("mtrix.")


class _UserSinPermiso:
    is_authenticated = True
    is_superuser = False
    cod_usuario = "vendedor"

    def is_admin(self):
        return False

    def tiene_permiso(self, code):
        return False


def _attach_messages(request):
    setattr(request, "_messages", FallbackStorage(request))


class MtrixViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.client = Client()

    def _session(self, request, *, cod="operador_mtrix", base="emp_ui"):
        request.session = self.client.session
        request.session["user"] = {
            "id_usuario": 9,
            "cod_usuario": cod,
            "base_empresa": base,
        }
        request.session.save()
        _attach_messages(request)
        return request

    def test_hub_sin_permiso_403(self):
        request = self._session(self.factory.get("/mtrix/"))
        request.user = _UserSinPermiso()
        with self.assertRaises(PermissionDenied):
            hub(request)

    def test_generar_sin_permiso_403(self):
        request = self._session(self.factory.post("/mtrix/generar/"))
        request.user = _UserSinPermiso()
        with self.assertRaises(PermissionDenied):
            generar(request)

    @patch("mtrix.views._launch_subprocess")
    def test_generar_guarda_triggered_by(self, mock_launch):
        request = self._session(self.factory.post("/mtrix/generar/"))
        request.user = _UserConPermiso()
        response = generar(request)
        self.assertEqual(response.status_code, 302)
        job = MtrixJob.objects.get()
        self.assertEqual(job.triggered_by, "operador_mtrix")
        self.assertEqual(job.origen, MtrixJob.Origen.UI)
        self.assertEqual(job.status, MtrixJob.Estado.QUEUED)
        mock_launch.assert_called_once_with(str(job.id))

    def test_rutas_nombradas(self):
        self.assertEqual(reverse("mtrix:hub"), "/mtrix/")
        self.assertTrue(reverse("mtrix:preview", args=["ci"]).endswith("/preview/ci/"))
        self.assertEqual(reverse("mtrix:configuracion"), "/mtrix/configuracion/")
        self.assertEqual(reverse("mtrix:job_list"), "/mtrix/jobs/")

    def test_templates_sin_dialogos_nativos(self):
        root = Path(__file__).resolve().parents[1] / "templates"
        for path in root.rglob("*.html"):
            texto = path.read_text(encoding="utf-8")
            self.assertNotIn("alert(", texto)
            self.assertNotIn("confirm(", texto)
            self.assertNotIn("prompt(", texto)
