# -*- coding: utf-8 -*-
"""Tests catálogo y reglas de informes BestSox (Producción, Compras, Consignación)."""
from __future__ import annotations

from unittest.mock import MagicMock

from django.test import SimpleTestCase, TestCase

from reports.services.bestsox_marca_reports_seed import (
    COMPRAS_MARCA_SUPERART_SLUG,
    CONSIGNACION_STOCK_SLUG,
    PRODUCCION_MARCA_SUPERART_SLUG,
    seed_all_bestsox_marca_reports,
)
from reports.services.catalog_service import CatalogService


def _catalog_slugs(user) -> set[str]:
    return {e.slug for e in CatalogService(user).get_catalog(None)}


def _mock_user(*, permisos: set[str]):
    user = MagicMock(is_authenticated=True, is_superuser=False)

    def tiene_permiso(code):
        return code in permisos

    user.tiene_permiso.side_effect = tiene_permiso
    user.get_permisos_totales.return_value = permisos
    return user


class BestsoxMarcaReportsCatalogTests(TestCase):
    def setUp(self):
        from reports.models import ReportDefinition, ReportWidget

        seed_all_bestsox_marca_reports(ReportDefinition, ReportWidget)

    def test_report_definitions_exist_and_show_in_catalog(self):
        from reports.models import ReportDefinition

        for slug in (
            PRODUCCION_MARCA_SUPERART_SLUG,
            COMPRAS_MARCA_SUPERART_SLUG,
            CONSIGNACION_STOCK_SLUG,
        ):
            with self.subTest(slug=slug):
                rd = ReportDefinition.objects.get(slug=slug, empresa__isnull=True)
                self.assertTrue(rd.is_active)
                self.assertTrue(rd.is_visible)
                self.assertTrue(rd.show_in_catalog)
                self.assertEqual(rd.category, "operational")

    def test_catalog_lists_reports_for_operational_user(self):
        user = _mock_user(permisos={"reports.view_operational"})
        slugs = _catalog_slugs(user)
        for slug in (
            PRODUCCION_MARCA_SUPERART_SLUG,
            COMPRAS_MARCA_SUPERART_SLUG,
            CONSIGNACION_STOCK_SLUG,
        ):
            with self.subTest(slug=slug):
                self.assertIn(slug, slugs)

    def test_catalog_lists_reports_for_mpr_user_without_operational(self):
        """Misma puerta que Fabricados: mpr.reportes / mpr.ver + slug en catálogo operativo."""
        user = _mock_user(permisos={"mpr.reportes"})
        slugs = _catalog_slugs(user)
        for slug in (
            PRODUCCION_MARCA_SUPERART_SLUG,
            COMPRAS_MARCA_SUPERART_SLUG,
            CONSIGNACION_STOCK_SLUG,
        ):
            with self.subTest(slug=slug):
                self.assertIn(slug, slugs)

    def test_catalog_omits_without_report_permission(self):
        user = _mock_user(permisos={"reports.view_managerial"})
        slugs = _catalog_slugs(user)
        for slug in (
            PRODUCCION_MARCA_SUPERART_SLUG,
            COMPRAS_MARCA_SUPERART_SLUG,
            CONSIGNACION_STOCK_SLUG,
        ):
            with self.subTest(slug=slug):
                self.assertNotIn(slug, slugs)

    def test_catalog_legacy_listados_section(self):
        user = _mock_user(permisos={"reports.view_operational"})
        by_slug = {e.slug: e for e in CatalogService(user).get_catalog(None)}
        for slug in (
            PRODUCCION_MARCA_SUPERART_SLUG,
            COMPRAS_MARCA_SUPERART_SLUG,
            CONSIGNACION_STOCK_SLUG,
        ):
            with self.subTest(slug=slug):
                entry = by_slug[slug]
                self.assertEqual(entry.legacy_section, "listados")
                self.assertLess(entry.legacy_order, 999)


class BestsoxMarcaReportsMenuCatalogTests(SimpleTestCase):
    def test_mpr_menu_tiene_entradas_como_fabricados(self):
        from core.utils.utils import APPS_MENU

        mpr = next(m for m in APPS_MENU if m.get("id") == "mpr")
        reportes = next(s for s in mpr["submenus"] if "Reportes" in str(s.get("seccion", "")))
        by_id = {it.get("menu_item_id"): it for it in reportes["items"]}
        expected = (
            ("mpr_rep_produccion_marca_superart", PRODUCCION_MARCA_SUPERART_SLUG),
            ("mpr_rep_compras_marca_superart", COMPRAS_MARCA_SUPERART_SLUG),
            ("mpr_rep_consignacion_stock", CONSIGNACION_STOCK_SLUG),
        )
        for menu_id, slug in expected:
            with self.subTest(menu_id=menu_id):
                self.assertIn(menu_id, by_id)
                item = by_id[menu_id]
                self.assertEqual(item["url_kwargs"]["slug"], slug)
                perms = item.get("permission")
                if isinstance(perms, list):
                    self.assertIn("reports.view_operational", perms)
                    self.assertTrue({"mpr.reportes", "mpr.ver"} & set(perms))
