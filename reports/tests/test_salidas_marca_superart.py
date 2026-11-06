# -*- coding: utf-8 -*-
"""Tests informe salidas-marca-superart."""
import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from reports.permissions import (
    SALIDAS_MARCA_SUPERART_SLUG,
    user_can_access_salidas_marca_superart,
)
from reports.salidas_marca_superart_api_views import (
    SalidasMarcaSuperartMarcasBuscarAPIView,
    SalidasMarcaSuperartSuperartBuscarAPIView,
)
from reports.services.compras_marca_superart_calcs import superart_desde_articulo_compras, unidades_nu_desde_nombre
from reports.services.query_runner import QueryRunnerService
from reports.services.salidas_marca_superart_calcs import (
    VIA_FACTURA_DIRECTA,
    VIA_NCA,
    VIA_REM_FACTURADO,
    build_totals_planos,
    parse_filters_from_payload,
    sql_packs_netos_salidas,
    sql_via_trazabilidad_salidas,
)
from reports.services.salidas_marca_superart_query import (
    _fetch_mstock_kpi_informativo,
    _fetch_salidas_cliente_terminado,
)
from reports.services.salidas_marca_superart_seed import SALIDAS_MARCA_SUPERART_SLUG as SEED_SLUG


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
    "total_packs": 26605.0,
    "total_prendas": 32261.0,
    "total_docenas": round(32261.0 / 12.0, 4),
    "articulos_con_salida": 412,
    "packs_por_marca": {
        "LB": 5607.0,
        "PUS": 7386.0,
        "PUW": 12492.0,
        "RW": 1120.0,
    },
    "packs_por_via": {
        VIA_REM_FACTURADO: 18000.0,
        "rem_sin_facturar": 4200.0,
        "rem_consignacion": 900.0,
        VIA_FACTURA_DIRECTA: 4100.0,
        VIA_NCA: -595.0,
    },
    "filas_marca": [],
    "totales_por_mes": {},
    "mes_labels": {},
}


class TestSlugYPermisos(SimpleTestCase):
    def test_slug_consistente(self):
        self.assertEqual(SALIDAS_MARCA_SUPERART_SLUG, SEED_SLUG)

    def test_permiso_operativo(self):
        user = _mock_user_reportes("reports.view_operational")
        self.assertTrue(user_can_access_salidas_marca_superart(user))


class TestCalcsSuperartNu(SimpleTestCase):
    def test_superart_id_manual(self):
        _sk, cod, _desc = superart_desde_articulo_compras("888869", "Puma Boxer 888869 2U")
        self.assertEqual(cod, "888869")

    def test_unidades_nu(self):
        self.assertEqual(unidades_nu_desde_nombre("Calcetin 2U pack"), 2)


class TestValidacionAgoOct2026(SimpleTestCase):
    def test_totals_planos_validacion(self):
        totals = build_totals_planos(VALIDACION_AGO_OCT_2026)
        self.assertAlmostEqual(totals["packs"], 26605.0, places=2)
        self.assertAlmostEqual(totals["prendas"], 32261.0, places=2)
        self.assertAlmostEqual(totals["docenas"], round(32261.0 / 12.0, 4), places=2)
        self.assertAlmostEqual(totals["packs_LB"], 5607.0, places=2)
        self.assertAlmostEqual(totals["packs_PUS"], 7386.0, places=2)
        self.assertAlmostEqual(totals["packs_PUW"], 12492.0, places=2)
        self.assertAlmostEqual(totals["packs_RW"], 1120.0, places=2)
        self.assertAlmostEqual(totals["packs_via_factura_directa"], 4100.0, places=2)

    @patch("reports.services.salidas_marca_superart_runner.reporte_salidas_marca_superart")
    @patch("reports.services.salidas_marca_superart_runner.preparar_salidas_marca_superart_presentacion")
    def test_runner_validacion_fixture(self, mock_prep, mock_reporte):
        from reports.models import ReportDefinition
        from reports.services.salidas_marca_superart_runner import run_salidas_marca_superart

        mock_reporte.return_value = dict(VALIDACION_AGO_OCT_2026)
        mock_prep.side_effect = lambda d: d
        report = ReportDefinition(slug=SALIDAS_MARCA_SUPERART_SLUG, name="T", category="operational")
        result = run_salidas_marca_superart(
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
        self.assertAlmostEqual(result.totals["packs"], 26605.0, places=2)
        self.assertAlmostEqual(result.totals["prendas"], 32261.0, places=2)


class TestSqlSalidas(SimpleTestCase):
    def _assert_sql_params_format_ok(self, cur):
        sql, params = cur.execute.call_args[0]
        self.assertIn("%%Y-%%m", sql)
        try:
            sql % tuple(params)
        except (TypeError, ValueError) as exc:
            self.fail(f"SQL % params falló (%% sin escapar?): {exc}")

    def test_salidas_sql_clausulas_negocio(self):
        cur = MagicMock()
        cur.fetchall.return_value = []
        _fetch_salidas_cliente_terminado(cur, "2026-08-01", "2026-10-31", None, None)
        sql = cur.execute.call_args[0][0]
        self.assertIn("Remito Salida", sql)
        self.assertIn("Devol - Cliente", sql)
        self.assertIn("codmov_remito", sql)
        self.assertIn("modalidad_remit", sql)
        self.assertIn("Anul Remito", sql)
        self.assertIn("CodDeposito = 6", sql)
        self.assertIn("Tipo", sql)
        self.assertIn("Comprobante, '') <> 'MSTOCK'", sql)
        self._assert_sql_params_format_ok(cur)

    def test_salidas_sql_percent_format(self):
        cur = MagicMock()
        cur.fetchall.return_value = []
        _fetch_salidas_cliente_terminado(cur, "2026-08-01", "2026-10-31", None, None)
        self._assert_sql_params_format_ok(cur)

    def test_mstock_kpi_mismas_marcas_y_sin_gasto(self):
        cur = MagicMock()
        cur.fetchone.return_value = (0.0,)
        _fetch_mstock_kpi_informativo(cur, "2026-08-01", "2026-10-31", None, None)
        sql = cur.execute.call_args[0][0]
        self.assertIn("MSTOCK", sql)
        self.assertIn("tipo_art", sql)
        self.assertIn("NombreMarca", sql)
        self._assert_sql_params_format_ok(cur)

    def test_mstock_kpi_filtros_marca_en_params(self):
        cur = MagicMock()
        cur.fetchone.return_value = (1.0,)
        _fetch_mstock_kpi_informativo(cur, "2026-08-01", "2026-10-31", [3, 4], [9])
        self._assert_sql_params_format_ok(cur)
        _, params = cur.execute.call_args[0]
        self.assertEqual(params[0], "2026-08-01")
        self.assertEqual(params[1], "2026-10-31")
        self.assertEqual(params[2:], [3, 4, 9])

    def test_expresiones_via_contienen_like_escapado(self):
        via = sql_via_trazabilidad_salidas()
        self.assertIn("%%CONSIG%%", via)
        packs = sql_packs_netos_salidas()
        self.assertIn("Remito Salida", packs)


class TestRunnerRegistrado(SimpleTestCase):
    def test_query_runner_tiene_slug(self):
        src = inspect.getsource(QueryRunnerService.run)
        self.assertIn('"salidas-marca-superart"', src)


class TestDashboardTemplate(SimpleTestCase):
    def test_dashboard_incluye_smsa(self):
        html = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "reports"
            / "dashboard_detail.html"
        ).read_text(encoding="utf-8")
        self.assertIn("filters_salidas_marca_superart.html", html)
        self.assertIn('id="smsa-section"', html)
        self.assertIn("salidas_marca_superart.js", html)


class TestReportsPredictivoAPI(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    @patch("reports.services.salidas_marca_superart_query.buscar_marcas_salidas_predictivo")
    def test_api_marcas_json(self, mock_buscar):
        mock_buscar.return_value = [{"value": 3, "label": "LB"}]
        req = self.rf.get("/api/reports/salidas-marca-superart/marcas/buscar/?q=lb")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("reports.view_operational")
        resp = SalidasMarcaSuperartMarcasBuscarAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["marcas"][0]["label"], "LB")

    @patch("reports.services.salidas_marca_superart_query.buscar_superart_salidas_predictivo")
    def test_api_superart_json(self, mock_buscar):
        mock_buscar.return_value = [{"codigo": "888869", "descripcion": "888869"}]
        req = self.rf.get("/api/reports/salidas-marca-superart/superart/buscar/?q=888")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("reports.view_operational")
        resp = SalidasMarcaSuperartSuperartBuscarAPIView.as_view()(req)
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
