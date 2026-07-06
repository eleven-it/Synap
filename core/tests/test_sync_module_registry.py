"""Sincronización MODULE_CONFIGS → ModuleConfig."""

from django.test import TestCase

from core.models import ModuleConfig
from core.module_manager import ModuleManager
from core.module_registry import MODULE_CONFIGS


class SyncModuleRegistryTest(TestCase):
    def test_sync_crea_odoo_migracion_si_falta(self):
        ModuleConfig.objects.filter(name="odoo_migracion").delete()
        self.assertFalse(ModuleConfig.objects.filter(name="odoo_migracion").exists())

        manager = ModuleManager()
        created, updated = manager.sync_registry_to_db()

        self.assertTrue(ModuleConfig.objects.filter(name="odoo_migracion").exists())
        cfg = MODULE_CONFIGS["odoo_migracion"]
        row = ModuleConfig.objects.get(name="odoo_migracion")
        self.assertEqual(row.display_name, cfg["display_name"])
        self.assertGreaterEqual(created + updated, 1)

    def test_sync_no_pisa_is_active(self):
        ModuleConfig.objects.update_or_create(
            name="odoo_migracion",
            defaults={
                "display_name": "Legacy",
                "description": "",
                "version": "0.0.1",
                "is_active": True,
            },
        )
        manager = ModuleManager()
        manager.sync_registry_to_db()
        row = ModuleConfig.objects.get(name="odoo_migracion")
        self.assertTrue(row.is_active)
        self.assertEqual(row.display_name, MODULE_CONFIGS["odoo_migracion"]["display_name"])
