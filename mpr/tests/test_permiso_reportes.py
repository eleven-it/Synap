"""Tests permiso granular mpr.reportes (hub sin escritorio completo)."""

from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from core.utils.utils import apps_visibles_sin_filtro_pwa
from mpr.landing import es_solo_reportes, landing_url_para_usuario
from mpr.views import (
    ClasificacionProduccionView,
    ReportesMPRView,
    TableroProduccionView,
    _usuario_puede_ver_reportes_mpr,
)


def _mock_user(*permisos: str):
    user = MagicMock(is_authenticated=True)
    user.is_admin.return_value = False
    user.is_superuser = False
    user.cod_usuario = "analista"
    user.roles.all.return_value = []
    perm_set = set(permisos)

    def tiene_permiso(p):
        return p in perm_set

    user.tiene_permiso.side_effect = tiene_permiso
    user.get_permisos_totales.return_value = perm_set
    return user


class TestHelpersReportes(SimpleTestCase):
    def test_ver_reportes_or_mpr_ver_o_reportes(self):
        self.assertTrue(_usuario_puede_ver_reportes_mpr(_mock_user("mpr.ver")))
        self.assertTrue(_usuario_puede_ver_reportes_mpr(_mock_user("mpr.reportes")))
        self.assertFalse(_usuario_puede_ver_reportes_mpr(_mock_user("mpr.tablero_ver")))
        self.assertFalse(_usuario_puede_ver_reportes_mpr(_mock_user()))

    def test_es_solo_reportes(self):
        self.assertTrue(es_solo_reportes(_mock_user("mpr.reportes")))
        self.assertFalse(es_solo_reportes(_mock_user("mpr.ver", "mpr.reportes")))
        self.assertFalse(es_solo_reportes(_mock_user("mpr.reportes", "mpr.tablero_ver")))
        self.assertFalse(es_solo_reportes(_mock_user("mpr.parte_operario", "mpr.reportes")))

    def test_landing_solo_reportes(self):
        url = landing_url_para_usuario(_mock_user("mpr.reportes"))
        self.assertTrue(url.endswith("/mpr/reportes/"))
        self.assertIsNone(landing_url_para_usuario(_mock_user("mpr.ver")))


class TestVistasReportesPermiso(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request_reportes(self, *permisos: str):
        request = self.factory.get(reverse("mpr:reportes"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user(*permisos)
        return request

    @patch.object(ReportesMPRView, "get", return_value=HttpResponse("ok"))
    def test_reportes_200_con_solo_reportes(self, _get):
        response = ReportesMPRView.as_view()(self._request_reportes("mpr.reportes"))
        self.assertEqual(response.status_code, 200)

    @patch.object(ReportesMPRView, "get", return_value=HttpResponse("ok"))
    def test_reportes_200_con_mpr_ver_sin_reportes(self, _get):
        response = ReportesMPRView.as_view()(self._request_reportes("mpr.ver"))
        self.assertEqual(response.status_code, 200)

    def test_reportes_403_sin_permiso(self):
        with self.assertRaises(PermissionDenied):
            ReportesMPRView.as_view()(self._request_reportes("mpr.tablero_ver"))

    def test_escritorio_403_con_solo_reportes(self):
        request = self.factory.get(reverse("mpr:clasificacion_produccion"))
        request.session = {"user": {"id_usuario": 1}}
        request.user = _mock_user("mpr.reportes")
        with self.assertRaises(PermissionDenied):
            ClasificacionProduccionView.as_view()(request)

    def test_tablero_403_con_solo_reportes(self):
        request = self.factory.get(reverse("mpr:tablero_produccion"))
        request.session = {"user": {"id_usuario": 1}}
        request.user = _mock_user("mpr.reportes")
        with self.assertRaises(PermissionDenied):
            TableroProduccionView.as_view()(request)


class TestMenuReportes(SimpleTestCase):
    @patch("core.module_manager.ModuleManager.get_active_modules", return_value=["mpr"])
    @patch(
        "core.services.navbar_visibilidad.cargar_estado_granular",
        return_value=({}, {}),
    )
    @patch(
        "core.services.navbar_visibilidad.app_visible_en_navbar_granular",
        return_value=True,
    )
    @patch(
        "core.services.navbar_visibilidad.item_visible_en_navbar_granular",
        return_value=True,
    )
    def test_menu_mpr_solo_reportes(self, *_mocks):
        user = _mock_user("mpr.reportes")
        apps = apps_visibles_sin_filtro_pwa(user)
        mpr = next((a for a in apps if a.get("id") == "mpr"), None)
        self.assertIsNotNone(mpr)
        labels = [
            item["label"]
            for submenu in mpr.get("submenus", [])
            for item in submenu.get("items", [])
        ]
        self.assertEqual(labels, ["Reportes MPR"])
        self.assertTrue(mpr["url"].endswith("/mpr/reportes/"))
        self.assertNotIn("Tablero de producción", labels)
        self.assertNotIn("Control de calidad", labels)
