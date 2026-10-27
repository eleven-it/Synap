"""Acceso a Armado de cajas desde escritorio, PWA y permisos por puesto."""

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import reverse

from core.middleware.mobile_level_a_middleware import mobile_path_allowed_for_level_a
from core.services.synap_permisos_seed import asegurar_synap_schema_si_procede
from core.utils.utils import apps_visibles_para_usuario, apps_visibles_sin_filtro_pwa
from stock.prep_cajas_views import pagina


class StockCajasNavegacionTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _user(self, permisos):
        return SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            cod_usuario="operador",
            is_admin=lambda: False,
            get_permisos_totales=lambda: permisos,
            tiene_permiso=lambda codigo: codigo in permisos,
        )

    def _request(self, permisos, mobile=False):
        request = self.factory.get(reverse("stock:prep_cajas"))
        request.user = self._user(permisos)
        request.session = {}
        request.is_mobile = mobile
        return request

    def _menu(self, request):
        with ExitStack() as stack:
            mocked_manager = stack.enter_context(patch("core.module_manager.ModuleManager"))
            mocked_manager.return_value.get_active_modules.return_value = []
            stack.enter_context(patch("core.services.navbar_visibilidad.cargar_estado_granular", return_value=(set(), set())))
            stack.enter_context(patch("core.services.navbar_visibilidad.app_visible_en_navbar_granular", return_value=True))
            stack.enter_context(patch("core.services.navbar_visibilidad.item_visible_en_navbar_granular", return_value=True))
            stack.enter_context(patch("core.utils.utils._navbar_menu_oculto_global", return_value=False))
            return apps_visibles_para_usuario(request.user, request)

    def test_permiso_de_cajas_muestra_stock_y_abre_pagina_en_desktop_y_pwa(self):
        for mobile in (False, True):
            with self.subTest(mobile=mobile):
                request = self._request({"stock.preparacion_cajas"}, mobile)
                stock = next(app for app in self._menu(request) if app["id"] == "stock")
                self.assertEqual(stock["url"], reverse("stock:prep_cajas"))
                self.assertEqual(
                    [item["menu_item_id"] for section in stock["submenus"] for item in section["items"]],
                    ["stock_prep_cajas"],
                )
                with patch("stock.prep_cajas_views.render", return_value=HttpResponse("Cajas")):
                    self.assertEqual(pagina(request).status_code, 200)

        self.assertTrue(mobile_path_allowed_for_level_a(reverse("stock:prep_cajas")))

    def test_pwa_stock_con_varios_permisos_navega_a_una_pantalla_permitida(self):
        request = self._request(
            {"stock.ver", "stock.crear_movimiento", "stock.preparacion_cajas"}, mobile=True
        )
        stock = next(app for app in self._menu(request) if app["id"] == "stock")
        self.assertEqual(stock["url"], reverse("stock:prep_cajas"))
        self.assertFalse(mobile_path_allowed_for_level_a(reverse("stock:alta_movimiento")))

    def test_sin_permiso_de_cajas_no_muestra_ni_abre_la_pagina(self):
        request = self._request({"stock.ver", "stock.crear_movimiento"}, mobile=True)
        self.assertFalse(any(app["id"] == "stock" for app in self._menu(request)))
        with self.assertRaises(PermissionDenied):
            pagina(request)

@override_settings(SYNAP_AUTO_ENSURE_SCHEMA=True)
class StockCajasCatalogoTests(SimpleTestCase):
    def test_cache_vieja_no_impide_sembrar_el_permiso_nuevo(self):
        with patch("core.services.synap_permisos_seed.cache") as mocked_cache, patch(
            "core.mysql_pool.get_connection"
        ) as mocked_connection, patch(
            "core.services.legacy_mysql_schema.catalog.run_synap_permisos_tables_mysql",
            return_value={"success": True},
        ) as mocked_seed:
            mocked_cache.get.side_effect = lambda key: key == "synap_schema_ensure:administranet2"
            mocked_connection.return_value.__enter__.return_value = MagicMock()
            asegurar_synap_schema_si_procede("administranet2")

        mocked_seed.assert_called_once()
        cache_key = mocked_cache.get.call_args.args[0]
        self.assertTrue(cache_key.startswith("synap_schema_ensure:administranet2:"))
        mocked_cache.set.assert_called_once()

    def test_no_cachea_un_intento_de_siembra_fallido(self):
        with patch("core.services.synap_permisos_seed.cache") as mocked_cache, patch(
            "core.mysql_pool.get_connection"
        ), patch(
            "core.services.legacy_mysql_schema.catalog.run_synap_permisos_tables_mysql",
            return_value={"success": False, "message": "Sin permisos MySQL"},
        ):
            mocked_cache.get.return_value = False
            asegurar_synap_schema_si_procede("administranet2")
        mocked_cache.set.assert_not_called()
