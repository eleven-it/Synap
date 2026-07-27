"""Tests tablero solo lectura para operario (mpr.tablero_ver)."""

from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from core.utils.utils import apps_visibles_sin_filtro_pwa
from mpr.landing import landing_url_para_usuario
from mpr.views import (
    ClasificacionProduccionView,
    EnviarProduccionLoteView,
    ReportesMPRView,
    TableroProduccionActualizarView,
    TableroProduccionView,
    _context_flags_tablero,
    _usuario_puede_enviar_desde_tablero,
    _usuario_puede_ver_tablero_produccion,
)


def _mock_user(*permisos: str):
    user = MagicMock(is_authenticated=True)
    user.is_admin.return_value = False
    user.is_superuser = False
    user.cod_usuario = "operario"
    user.roles.all.return_value = []
    perm_set = set(permisos)

    def tiene_permiso(p):
        return p in perm_set

    user.tiene_permiso.side_effect = tiene_permiso
    user.get_permisos_totales.return_value = perm_set
    return user


class TestHelpersTableroLectura(SimpleTestCase):
    def test_ver_tablero_or_mpr_ver_o_tablero_ver(self):
        self.assertTrue(_usuario_puede_ver_tablero_produccion(_mock_user("mpr.ver")))
        self.assertTrue(
            _usuario_puede_ver_tablero_produccion(_mock_user("mpr.tablero_ver"))
        )
        self.assertFalse(_usuario_puede_ver_tablero_produccion(_mock_user()))

    def test_enviar_desde_tablero_solo_mpr_ver(self):
        self.assertTrue(_usuario_puede_enviar_desde_tablero(_mock_user("mpr.ver")))
        self.assertFalse(
            _usuario_puede_enviar_desde_tablero(_mock_user("mpr.tablero_ver"))
        )

    def test_context_flags_operario_tablero(self):
        user = _mock_user("mpr.parte_operario", "mpr.tablero_ver")
        flags = _context_flags_tablero(user)
        self.assertFalse(flags["puede_enviar"])
        self.assertTrue(flags["solo_lectura_tablero"])
        self.assertFalse(flags["puede_anular_envios"])

    def test_context_flags_supervisor_mpr_ver(self):
        user = _mock_user("mpr.ver")
        flags = _context_flags_tablero(user)
        self.assertTrue(flags["puede_enviar"])
        self.assertFalse(flags["solo_lectura_tablero"])


class TestVistasTableroLectura(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.views._context_filtro_marcas", return_value={})
    @patch("mpr.services_maquina_linea.enriquecer_filas_tablero_indicadores_fabricando", return_value=[])
    @patch("mpr.presentacion_operativa.enriquecer_filas_tablero_presentacion", side_effect=lambda f, _m: f)
    @patch("mpr.views.listar_tablero_por_articulo", return_value=[])
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_get_tablero_200_con_tablero_ver(
        self,
        *_mocks,
    ):
        request = self.factory.get(reverse("mpr:tablero_produccion"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.parte_operario", "mpr.tablero_ver")
        response = TableroProduccionView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context_data["puede_enviar"])
        self.assertTrue(response.context_data["solo_lectura_tablero"])

    def test_get_tablero_403_sin_permiso(self):
        request = self.factory.get(reverse("mpr:tablero_produccion"))
        request.session = {"user": {"id_usuario": 1}}
        request.user = _mock_user("mpr.parte_operario")
        with self.assertRaises(PermissionDenied):
            TableroProduccionView.as_view()(request)

    @patch("django.contrib.messages.api.add_message")
    @patch("mpr.views._redirect_tablero_produccion")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_post_actualizar_ok_con_tablero_ver(self, _base, mock_redirect, _add_msg):
        mock_redirect.return_value = MagicMock(status_code=302)
        request = self.factory.post(reverse("mpr:tablero_produccion_actualizar"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.tablero_ver")
        response = TableroProduccionActualizarView.as_view()(request)
        self.assertIn(response.status_code, (200, 302))

    def test_post_enviar_403_con_solo_tablero_ver(self):
        request = self.factory.post(reverse("mpr:tablero_produccion_enviar"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.parte_operario", "mpr.tablero_ver")
        with self.assertRaises(PermissionDenied):
            EnviarProduccionLoteView.as_view()(request)

    def test_clasificacion_403_con_solo_tablero_ver(self):
        request = self.factory.get(reverse("mpr:clasificacion_produccion"))
        request.session = {"user": {"id_usuario": 1}}
        request.user = _mock_user("mpr.tablero_ver")
        with self.assertRaises(PermissionDenied):
            ClasificacionProduccionView.as_view()(request)

    def test_reportes_403_con_solo_tablero_ver(self):
        request = self.factory.get(reverse("mpr:reportes"))
        request.session = {"user": {"id_usuario": 1}}
        request.user = _mock_user("mpr.tablero_ver")
        with self.assertRaises(PermissionDenied):
            ReportesMPRView.as_view()(request)


class TestLandingOperarioTablero(SimpleTestCase):
    def test_landing_sigue_mi_parte(self):
        user = _mock_user("mpr.parte_operario", "mpr.tablero_ver")
        url = landing_url_para_usuario(user)
        self.assertTrue(url.endswith("/mpr/mi-parte/"))


class TestMenuOperarioTablero(SimpleTestCase):
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
    def test_menu_mpr_solo_tablero(self, *_mocks):
        user = _mock_user("mpr.parte_operario", "mpr.tablero_ver")
        apps = apps_visibles_sin_filtro_pwa(user)
        mpr = next((a for a in apps if a.get("id") == "mpr"), None)
        self.assertIsNotNone(mpr)
        labels = [
            item["label"]
            for submenu in mpr.get("submenus", [])
            for item in submenu.get("items", [])
        ]
        self.assertEqual(labels, ["Tablero de producción"])
        self.assertNotIn("Mi parte", labels)
        self.assertNotIn("Control de calidad", labels)
        self.assertNotIn("Reportes MPR", labels)


class TestRegresionMprVer(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.views._context_filtro_marcas", return_value={})
    @patch("mpr.services_maquina_linea.enriquecer_filas_tablero_indicadores_fabricando", return_value=[])
    @patch("mpr.presentacion_operativa.enriquecer_filas_tablero_presentacion", side_effect=lambda f, _m: f)
    @patch("mpr.views.listar_tablero_por_articulo", return_value=[])
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_get_tablero_200_con_mpr_ver(self, *_mocks):
        request = self.factory.get(reverse("mpr:tablero_produccion"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.ver")
        response = TableroProduccionView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["puede_enviar"])

    @patch("mpr.views._redirect_tablero_produccion")
    @patch("mpr.services.enviar_a_produccion_lote", return_value=(True, 0, [], None))
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_post_enviar_ok_con_mpr_ver(self, _base, _enviar, mock_redirect):
        mock_redirect.return_value = MagicMock(status_code=302)
        request = self.factory.post(reverse("mpr:tablero_produccion_enviar"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.ver")
        response = EnviarProduccionLoteView.as_view()(request)
        self.assertIn(response.status_code, (200, 302))

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
    def test_menu_mpr_completo_con_mpr_ver(self, *_mocks):
        user = _mock_user("mpr.ver")
        apps = apps_visibles_sin_filtro_pwa(user)
        mpr = next((a for a in apps if a.get("id") == "mpr"), None)
        self.assertIsNotNone(mpr)
        labels = [
            item["label"]
            for submenu in mpr.get("submenus", [])
            for item in submenu.get("items", [])
        ]
        self.assertIn("Tablero de producción", labels)
        self.assertIn("Control de calidad", labels)
        self.assertIn("Reportes MPR", labels)
