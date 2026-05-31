"""MPR registrado en Module Management (MODULE_CONFIGS + ModuleConfig)."""

from django.test import TestCase

from core.models import ModuleConfig
from core.module_manager import ModuleManager
from core.module_registry import MODULE_CONFIGS
from reports.services.executive_dashboard.base import mpr_modulo_activo


class MprModuleConfigTest(TestCase):
    def test_mpr_en_module_configs(self):
        self.assertIn("mpr", MODULE_CONFIGS)
        cfg = MODULE_CONFIGS["mpr"]
        self.assertEqual(cfg["display_name"], "Producción (MPR)")
        self.assertIn("mpr.ver", cfg["permissions"])

    def test_mpr_modulo_activo_refleja_moduleconfig(self):
        ModuleConfig.objects.update_or_create(
            name="mpr",
            defaults={
                "display_name": "Producción (MPR)",
                "description": "test",
                "version": "1.0.0",
                "is_active": True,
            },
        )
        self.assertTrue(mpr_modulo_activo())
        ModuleConfig.objects.filter(name="mpr").update(is_active=False)
        ModuleManager()._refresh_active_modules_from_cache_or_db(force=True)
        self.assertFalse(mpr_modulo_activo())

    def test_setup_modules_puede_activar_mpr(self):
        for dep in ("core", "login", "dashboard"):
            ModuleConfig.objects.update_or_create(
                name=dep,
                defaults={
                    "display_name": dep,
                    "description": "",
                    "version": "1.0.0",
                    "is_active": True,
                },
            )
        ModuleConfig.objects.update_or_create(
            name="mpr",
            defaults={
                "display_name": "Producción (MPR)",
                "description": "",
                "version": "1.0.0",
                "is_active": False,
            },
        )
        manager = ModuleManager()
        manager._refresh_active_modules_from_cache_or_db(force=True)
        self.assertFalse(manager.is_module_active("mpr"))
        ok, msg = manager.activate_module("mpr")
        self.assertTrue(ok, msg)
        self.assertTrue(manager.is_module_active("mpr"))
