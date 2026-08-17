# -*- coding: utf-8 -*-
"""Contrato catálogo Inventario por depósito (slug inventario-deposito-articulo)."""
from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from reports.permissions import (
    INVENTARIO_DEPOSITO_SLUG,
    InventarioDepositoCatalogPermission,
    user_can_access_inventario_deposito,
)
from reports.services.inventario_deposito_runner import (
    _parse_filtros_from_payload,
    run_inventario_deposito,
)
from reports.services.inventario_deposito_seed import INVENTARIO_DEPOSITO_SLUG as SEED_SLUG


class InventarioDepositoPermisosTest(SimpleTestCase):
    def test_slug_canonico(self):
        self.assertEqual(INVENTARIO_DEPOSITO_SLUG, "inventario-deposito-articulo")
        self.assertEqual(SEED_SLUG, INVENTARIO_DEPOSITO_SLUG)

    def test_acceso_con_operacional(self):
        user = MagicMock()
        user.is_authenticated = True
        user.is_superuser = False
        user.tiene_permiso = MagicMock(
            side_effect=lambda c: c == "reports.view_operational"
        )
        self.assertTrue(user_can_access_inventario_deposito(user))

    def test_acceso_con_mpr_reportes(self):
        user = MagicMock()
        user.is_authenticated = True
        user.is_superuser = False
        user.tiene_permiso = MagicMock(side_effect=lambda c: c == "mpr.reportes")
        self.assertTrue(user_can_access_inventario_deposito(user))

    def test_sin_permiso(self):
        user = MagicMock()
        user.is_authenticated = True
        user.is_superuser = False
        user.tiene_permiso = MagicMock(return_value=False)
        user.get_permisos_totales = MagicMock(return_value=set())
        self.assertFalse(user_can_access_inventario_deposito(user))

    def test_api_permission_mpr_solo_slug_inventario(self):
        perm = InventarioDepositoCatalogPermission()
        user = MagicMock()
        user.is_authenticated = True
        user.is_superuser = False
        user.tiene_permiso = MagicMock(side_effect=lambda c: c == "mpr.reportes")

        request = MagicMock()
        request.user = user
        request.data = {"slug": INVENTARIO_DEPOSITO_SLUG}
        self.assertTrue(perm.has_permission(request, None))

        request.data = {"slug": "ventas-marcas-mensual"}
        self.assertFalse(perm.has_permission(request, None))


class InventarioDepositoRunnerFiltrosTest(SimpleTestCase):
    def test_parse_filtros_defaults(self):
        filtros = _parse_filtros_from_payload({"filters": {}})
        self.assertFalse(filtros.incluir_2da)
        self.assertEqual(filtros.fecha_corte, date.today())
        self.assertEqual(filtros.depositos, [])

    def test_parse_filtros_incluir_2da_bool(self):
        filtros = _parse_filtros_from_payload(
            {"filters": {"incluir_2da": True, "fecha_corte": "2026-08-10"}}
        )
        self.assertTrue(filtros.incluir_2da)
        self.assertEqual(filtros.fecha_corte, date(2026, 8, 10))

    @patch("reports.services.inventario_deposito_runner.consultar_inventario_deposito")
    def test_runner_envuelve_consulta(self, mock_consultar):
        mock_consultar.return_value = {
            "filas": [{"id_articulo": 1, "docenas": 1.5}],
            "depositos_jerarquia": [{"nombre_deposito": "Producción", "marcas": []}],
            "total_docenas": 1.5,
            "kpis": {"total_docenas": 1.5, "depositos": 1, "filas": 1},
            "fecha_corte": date(2026, 8, 17),
            "usa_stock_deposito": True,
        }
        report = MagicMock()
        report.slug = INVENTARIO_DEPOSITO_SLUG
        report.name = "Inventario por depósito"
        report.category = "operational"
        report.version = "1.0.0"
        result = run_inventario_deposito(
            report,
            {"filters": {"base_empresa": "administranet1", "incluir_2da": "0"}},
            user=None,
        )
        self.assertEqual(result.totals["total_docenas"], 1.5)
        self.assertEqual(len(result.meta["depositos_jerarquia"]), 1)
        self.assertEqual(result.meta["fecha_corte_display"], "17/08/2026")
        mock_consultar.assert_called_once()


@override_settings(ROOT_URLCONF="django_project.urls")
class InventarioDepositoRedirectHubTest(TestCase):
    """Redirect hub MPR → catálogo (requiere sesión; se mockea mixin vía client anónimo)."""

    def test_url_atajo_resuelve(self):
        url = reverse("reports:reports_inventario_deposito_short_redirect")
        self.assertIn("inventario-deposito-articulo", url)

    def test_dashboard_detail_name(self):
        url = reverse(
            "reports:dashboard_detail",
            kwargs={"slug": "inventario-deposito-articulo"},
        )
        self.assertTrue(url.endswith("/inventario-deposito-articulo/"))
