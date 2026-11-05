# -*- coding: utf-8 -*-
"""Tests informe compras-marca-superart."""
import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from reports.compras_marca_superart_api_views import (
    ComprasMarcaSuperartMarcasBuscarAPIView,
    ComprasMarcaSuperartSuperartBuscarAPIView,
)
from reports.permissions import (
    COMPRAS_MARCA_SUPERART_SLUG,
    user_can_access_compras_marca_superart,
)
from reports.services.compras_marca_superart_calcs import (
    build_totals_planos,
    parse_filters_from_payload,
    superart_desde_articulo_compras,
    unidades_nu_desde_nombre,
)
from reports.services.compras_marca_superart_query import _fetch_via_mstock, _fetch_via_proveedor
from reports.services.compras_marca_superart_seed import COMPRAS_MARCA_SUPERART_SLUG as SEED_SLUG
from reports.services.query_runner import QueryRunnerService


def _mock_user_reportes(*permisos: str):
    user = MagicMock(is_authenticated=True)
    user.is_superuser = False
    perm_set = set(permisos)

    def tiene_permiso(p):
        return p in perm_set

    user.tiene_permiso.side_effect = tiene_permiso
    user.get_permisos_totales.return_value = perm_set
    return user


VALIDACION_AGO_OCT_2026 = {
    "meses": ["2026-08", "2026-09", "2026-10"],
    "total_packs": 51232.0,
    "total_prendas": 62998.0,
    "total_docenas": round(62998.0 / 12.0, 4),
    "articulos_con_compra": 125,
    "packs_por_marca": {
        "LB": 11766.0,
        "PUS": 13649.0,
        "PUW": 24180.0,
        "RW": 1637.0,
    },
    "packs_por_marca_mes": {
        "LB": {"2026-08": 3698.0, "2026-09": 5422.0, "2026-10": 2646.0},
        "PUS": {"2026-08": 1144.0, "2026-09": 4683.0, "2026-10": 7822.0},
        "PUW": {"2026-08": 1806.0, "2026-09": 2667.0, "2026-10": 19707.0},
        "RW": {"2026-08": 0.0, "2026-09": 764.0, "2026-10": 873.0},
    },
    "filas_marca": [],
    "totales_por_mes": {},
    "mes_labels": {},
}


class TestSlugYPermisos(SimpleTestCase):
    def test_slug_consistente(self):
        self.assertEqual(COMPRAS_MARCA_SUPERART_SLUG, SEED_SLUG)

    def test_permiso_operativo_o_compras(self):
        user = _mock_user_reportes("compras.reportes")
        self.assertTrue(user_can_access_compras_marca_superart(user))


class TestCalcsSuperartNu(SimpleTestCase):
    def test_superart_id_manual_puma_boxer(self):
        sk, cod, _desc = superart_desde_articulo_compras("888869", "Puma Boxer 888869 2U")
        self.assertEqual(cod, "888869")

    def test_superart_desde_nombre_sin_manual(self):
        _, cod, _ = superart_desde_articulo_compras("", "888869-Puma Boxer 2U")
        self.assertEqual(cod, "888869")

    def test_unidades_nu(self):
        self.assertEqual(unidades_nu_desde_nombre("Calcetin 2U pack"), 2)
        self.assertEqual(unidades_nu_desde_nombre("Simple"), 1)


class TestValidacionAgoOct2026(SimpleTestCase):
    def test_totals_planos_validacion(self):
        totals = build_totals_planos(VALIDACION_AGO_OCT_2026)
        self.assertAlmostEqual(totals["packs"], 51232.0, places=2)
        self.assertAlmostEqual(totals["prendas"], 62998.0, places=2)
        self.assertEqual(totals["articulos"], 125.0)
        self.assertAlmostEqual(totals["packs_LB"], 11766.0, places=2)
        self.assertAlmostEqual(totals["packs_LB_2026-08"], 3698.0, places=2)
        self.assertAlmostEqual(totals["packs_PUS_2026-10"], 7822.0, places=2)
        self.assertAlmostEqual(totals["packs_RW_2026-09"], 764.0, places=2)

    @patch("reports.services.compras_marca_superart_runner.reporte_compras_marca_superart")
    @patch("reports.services.compras_marca_superart_runner.preparar_compras_marca_superart_presentacion")
    def test_runner_validacion_fixture(self, mock_prep, mock_reporte):
        from reports.models import ReportDefinition
        from reports.services.compras_marca_superart_runner import run_compras_marca_superart

        mock_reporte.return_value = dict(VALIDACION_AGO_OCT_2026)
        mock_prep.side_effect = lambda d: d
        report = ReportDefinition(slug=COMPRAS_MARCA_SUPERART_SLUG, name="T", category="operational")
        result = run_compras_marca_superart(
            report,
            {
                "filters": {
                    "base_empresa": "emp1",
                    "desde": "2026-08-01",
                    "hasta": "2026-10-31",
                }
            },
            MagicMock(base_empresa="emp1"),
        )
        self.assertAlmostEqual(result.totals["packs"], 51232.0, places=2)
        self.assertAlmostEqual(result.totals["prendas"], 62998.0, places=2)


class TestSqlCompras(SimpleTestCase):
    def test_via_proveedor_sql_clausulas(self):
        cur = MagicMock()
        cur.fetchall.return_value = []
        _fetch_via_proveedor(cur, "2026-08-01", "2026-10-31", None, None)
        sql = cur.execute.call_args[0][0]
        self.assertIn("Remito Entrada", sql)
        self.assertIn("TipoComprobante IN ('FA', 'FC', 'FM')", sql)
        self.assertIn("COALESCE(st.Entrada, 0) > 0", sql)
        self.assertIn("tipo_art_fab", sql)

    def test_via_mstock_excluye_cutover_y_motivos(self):
        cur = MagicMock()
        cur.fetchall.return_value = []
        _fetch_via_mstock(cur, "2026-08-01", "2026-10-31", None, None)
        sql = cur.execute.call_args[0][0]
        self.assertIn("MSTOCK", sql)
        self.assertIn("cutover", sql.lower())
        self.assertIn("Ajuste de saldo", sql)
        self.assertIn("Stock Inicial", sql)
        self.assertIn("deposito_origen", sql)


class TestRunnerRegistrado(SimpleTestCase):
    def test_query_runner_tiene_slug(self):
        src = inspect.getsource(QueryRunnerService.run)
        self.assertIn('"compras-marca-superart"', src)


class TestDashboardTemplate(SimpleTestCase):
    def test_dashboard_incluye_cmsa(self):
        html = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "reports"
            / "dashboard_detail.html"
        ).read_text(encoding="utf-8")
        self.assertIn("filters_compras_marca_superart.html", html)
        self.assertIn('id="cmsa-section"', html)
        self.assertIn("compras_marca_superart.js", html)


class TestReportsPredictivoAPI(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    @patch("reports.services.compras_marca_superart_query.buscar_marcas_compras_predictivo")
    def test_api_marcas_json(self, mock_buscar):
        mock_buscar.return_value = [{"value": 3, "label": "LB"}]
        req = self.rf.get("/api/reports/compras-marca-superart/marcas/buscar/?q=lb")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("reports.view_operational")
        resp = ComprasMarcaSuperartMarcasBuscarAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["marcas"][0]["label"], "LB")

    @patch("reports.services.compras_marca_superart_query.buscar_superart_compras_predictivo")
    def test_api_superart_json(self, mock_buscar):
        mock_buscar.return_value = [{"codigo": "888869", "descripcion": "888869"}]
        req = self.rf.get("/api/reports/compras-marca-superart/superart/buscar/?q=888")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("reports.view_operational")
        resp = ComprasMarcaSuperartSuperartBuscarAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["superarts"][0]["codigo"], "888869")


class TestParseFilters(SimpleTestCase):
    def test_desde_hasta_meses(self):
        f = parse_filters_from_payload(
            {"desde": "2026-08-01", "hasta": "2026-10-31", "q_superart": ["888869"]}
        )
        self.assertEqual(f["meses"], ["2026-08", "2026-09", "2026-10"])
        self.assertEqual(f["superarts_incluidos"], ["888869"])
