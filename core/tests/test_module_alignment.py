"""Alineación Module Management ↔ menú ↔ INSTALLED_APPS."""

from django.apps import apps as django_apps
from django.test import TestCase

from core.module_registry import MODULE_CONFIGS
from core.url_registry import SKIP_MODULES_IN_MAIN_URLS
from core.utils.utils import APPS_MENU

# Apps Synap que no usan ModuleConfig (siempre visibles si hay permiso).
MODULOS_SIN_MODULE_CONFIG = frozenset(
    {"stock", "ventas", "compras", "self_checkout", "archivo", "settings", "module_management"}
)

# Cadena base: visibles aunque ModuleConfig esté vacío (bootstrap).
MODULOS_MENU_SIEMPRE_ACTIVOS = frozenset({"core", "login", "dashboard"})

CORE_MODULES_MENU = frozenset(
    {
        "core",
        "login",
        "dashboard",
        "stock",
        "ventas",
        "compras",
        "self_checkout",
    }
)


class ModuleAlignmentTest(TestCase):
    def test_module_configs_coherentes_con_apps_instaladas(self):
        omitir = {"mercadopago", "clover"}  # registry legacy; apps opcionales comentadas en settings
        for nombre in MODULE_CONFIGS:
            if nombre in omitir:
                continue
            with self.subTest(modulo=nombre):
                self.assertTrue(
                    django_apps.is_installed(nombre),
                    f"Módulo {nombre} en MODULE_CONFIGS pero app no instalada",
                )

    def test_menu_ids_gestionados_no_estan_en_core_modules_bypass(self):
        menu_ids = {app["id"] for app in APPS_MENU}
        gestionados = menu_ids & set(MODULE_CONFIGS.keys())
        bypass_indeseado = (gestionados - MODULOS_MENU_SIEMPRE_ACTIVOS) & CORE_MODULES_MENU
        self.assertEqual(
            bypass_indeseado,
            set(),
            f"Módulos en MODULE_CONFIGS no deben estar en core_modules: {bypass_indeseado}",
        )

    def test_menu_apps_sin_module_config_no_en_registry(self):
        for app_id in MODULOS_SIN_MODULE_CONFIG:
            if app_id in ("archivo", "settings", "module_management"):
                continue
            with self.subTest(app=app_id):
                self.assertNotIn(
                    app_id,
                    MODULE_CONFIGS,
                    f"{app_id} es core sin ModuleConfig y no debe estar en MODULE_CONFIGS",
                )

    def test_mpr_en_skip_urls_principales(self):
        self.assertIn("mpr", SKIP_MODULES_IN_MAIN_URLS)

    def test_odoo_migracion_en_skip_urls_principales(self):
        self.assertIn("odoo_migracion", SKIP_MODULES_IN_MAIN_URLS)

    def test_modulos_montados_en_urls_principales_en_skip(self):
        montados_en_main = {
            "reports", "ia", "stock", "ventas", "compras", "mpr",
            "self_checkout", "logistica", "odoo_migracion",
        }
        faltantes = montados_en_main - set(SKIP_MODULES_IN_MAIN_URLS)
        self.assertEqual(
            faltantes,
            {"stock", "ventas", "compras"},
            "stock/ventas/compras no están en MODULE_CONFIGS; el resto debe estar en SKIP",
        )
