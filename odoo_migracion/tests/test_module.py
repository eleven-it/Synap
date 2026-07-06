"""Registro en Module Management."""

from django.test import TestCase

from core.module_registry import MODULE_CONFIGS, path_belongs_to_module


class OdooMigracionModuleConfigTest(TestCase):
    def test_odoo_migracion_en_module_configs(self):
        self.assertIn("odoo_migracion", MODULE_CONFIGS)
        cfg = MODULE_CONFIGS["odoo_migracion"]
        self.assertEqual(cfg["display_name"], "Migración Odoo")
        self.assertIn("odoo_migracion.ver", cfg["permissions"])
        self.assertFalse(cfg["is_core"])
        self.assertEqual(cfg.get("url_prefix"), "odoo-migracion")

    def test_url_prefix_reconocido_por_middleware(self):
        self.assertTrue(path_belongs_to_module("odoo-migracion/", "odoo_migracion"))
        self.assertTrue(path_belongs_to_module("odoo-migracion/conexiones/", "odoo_migracion"))
