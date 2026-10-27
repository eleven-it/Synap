# -*- coding: utf-8 -*-
"""Menú MPR: entrada Fabricados por superartículo."""

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from core.utils.utils import _resolver_url_item, apps_visibles_para_usuario


class MprMenuFabricadosSuperartTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _user(self, permisos):
        return SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            cod_usuario="mpr_user",
            is_admin=lambda: False,
            get_permisos_totales=lambda: permisos,
            tiene_permiso=lambda codigo: codigo in permisos,
        )

    def _item_fabricados(self):
        from core.utils.utils import APPS_MENU

        mpr = next(a for a in APPS_MENU if a["id"] == "mpr")
        reportes = next(s for s in mpr["submenus"] if s.get("seccion") == "Reportes")
        return next(
            i for i in reportes["items"] if i.get("menu_item_id") == "mpr_rep_fabricados_superart"
        )

    def test_resolver_url_item_anexa_url_query(self):
        item = self._item_fabricados()
        request = self.factory.get("/")
        resolved = _resolver_url_item(item, request, {"mpr.ver", "mpr.reportes"})
        self.assertIsNotNone(resolved)
        expected = (
            reverse("mpr:reportes")
            + "?grupo=produccion&reporte=fabricados_superart"
        )
        self.assertEqual(resolved["url"], expected)
        self.assertEqual(resolved["menu_item_id"], "mpr_rep_fabricados_superart")

    def test_visible_con_permisos_reportes_mpr(self):
        request = self.factory.get("/")
        request.user = self._user({"mpr.ver", "mpr.reportes"})
        request.session = {}
        with ExitStack() as stack:
            mocked_manager = stack.enter_context(patch("core.module_manager.ModuleManager"))
            mocked_manager.return_value.get_active_modules.return_value = ["mpr"]
            stack.enter_context(
                patch(
                    "core.services.navbar_visibilidad.cargar_estado_granular",
                    return_value=(set(), set()),
                )
            )
            stack.enter_context(
                patch(
                    "core.services.navbar_visibilidad.app_visible_en_navbar_granular",
                    return_value=True,
                )
            )
            stack.enter_context(
                patch(
                    "core.services.navbar_visibilidad.item_visible_en_navbar_granular",
                    return_value=True,
                )
            )
            stack.enter_context(
                patch("core.utils.utils._navbar_menu_oculto_global", return_value=False)
            )
            apps = apps_visibles_para_usuario(request.user, request)
        mpr = next(a for a in apps if a["id"] == "mpr")
        ids = [
            it["menu_item_id"]
            for sec in mpr.get("submenus", [])
            for it in sec.get("items", [])
        ]
        self.assertIn("mpr_rep_fabricados_superart", ids)
        self.assertIn("mpr_rep_reportes", ids)

    def test_permiso_or_mpr_ver_o_reportes(self):
        item = self._item_fabricados()
        self.assertIsNotNone(_resolver_url_item(item, None, {"mpr.ver"}))
        self.assertIsNotNone(_resolver_url_item(item, None, {"mpr.reportes"}))
        self.assertIsNone(_resolver_url_item(item, None, set()))
