"""Catálogo: secciones legacy (comprobantes / listados)."""
from __future__ import annotations

from django.test import SimpleTestCase

from reports.services.catalog_service import CatalogEntry, split_legacy_catalog


class CatalogLegacySectionsTests(SimpleTestCase):
    def test_split_legacy_orders_by_legacy_order_then_name(self):
        entries = [
            CatalogEntry(
                slug="b",
                name="B",
                description="",
                category="operational",
                refresh_interval="Diario",
                version="1.0",
                tags=[],
                metrics=[],
                dimensions=[],
                legacy_section="listados",
                legacy_order=20,
            ),
            CatalogEntry(
                slug="a",
                name="A",
                description="",
                category="operational",
                refresh_interval="Diario",
                version="1.0",
                tags=[],
                metrics=[],
                dimensions=[],
                legacy_section="listados",
                legacy_order=10,
            ),
        ]
        _, listados = split_legacy_catalog(entries)
        self.assertEqual([e.slug for e in listados], ["a", "b"])

    def test_split_comprobantes_vs_listados(self):
        entries = [
            CatalogEntry(
                slug="pedidos-pendientes",
                name="Pedidos",
                description="",
                category="operational",
                refresh_interval="Diario",
                version="1.0",
                tags=[],
                metrics=[],
                dimensions=[],
                legacy_section="comprobantes",
                legacy_order=10,
            ),
            CatalogEntry(
                slug="ventas_netas",
                name="Ventas",
                description="",
                category="operational",
                refresh_interval="Diario",
                version="1.0",
                tags=[],
                metrics=[],
                dimensions=[],
                legacy_section="listados",
                legacy_order=10,
            ),
        ]
        comp, lst = split_legacy_catalog(entries)
        self.assertEqual([e.slug for e in comp], ["pedidos-pendientes"])
        self.assertEqual([e.slug for e in lst], ["ventas_netas"])
