"""Tests contexto UI migración."""

from django.test import TestCase

from odoo_migracion.models import MigrationEntityMapping, OdooConnection
from odoo_migracion.services.ui_context import build_migration_overview, build_domain_progress


class UiContextTests(TestCase):
    def setUp(self):
        self.conexion = OdooConnection.objects.create(
            nombre="UI Test",
            base_empresa="administranet_test",
            base_url="https://odoo.test",
        )

    def test_overview_sin_discovery(self):
        overview = build_migration_overview(conexion=self.conexion)
        self.assertEqual(overview.conexion, self.conexion)
        self.assertGreater(len(overview.dominios), 0)

    def test_dominio_con_mapping_ok(self):
        MigrationEntityMapping.objects.create(
            conexion=self.conexion,
            entity_type="rubro",
            adminet_id="1",
            external_id="adminet/rubro/1",
            odoo_model="product.category",
            odoo_id=10,
            sync_state=MigrationEntityMapping.SyncState.OK,
        )
        items = build_domain_progress(
            self.conexion,
            discovery_conteos={"rubro": 1},
        )
        rubro = next(i for i in items if i.key == "rubro")
        self.assertEqual(rubro.mappings_ok, 1)
        self.assertEqual(rubro.status, "completado")
        self.assertEqual(rubro.sync_progress_pct, 100)
