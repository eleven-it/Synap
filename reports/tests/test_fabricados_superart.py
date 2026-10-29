# -*- coding: utf-8 -*-
"""Tests informe fabricados-superart standalone (reports app)."""
import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from reports.fabricados_superart_api_views import (
    FabricadosSuperartMarcasBuscarAPIView,
    FabricadosSuperartSuperartBuscarAPIView,
)
from reports.permissions import (
    FABRICADOS_SUPERART_SLUG,
    user_can_access_fabricados_superart,
)
from reports.services.fabricados_superart_calcs import parse_filters_from_payload
from reports.services.fabricados_superart_seed import FABRICADOS_SUPERART_SLUG as SEED_SLUG
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


class TestSlugYPermisos(SimpleTestCase):
    def test_slug_consistente(self):
        self.assertEqual(FABRICADOS_SUPERART_SLUG, SEED_SLUG)

    def test_permiso_mpr_o_operativo(self):
        user = _mock_user_reportes("mpr.reportes")
        self.assertTrue(user_can_access_fabricados_superart(user))


class TestParseFiltersPayload(SimpleTestCase):
    def test_desde_hasta_y_superarts(self):
        f = parse_filters_from_payload(
            {
                "desde": "2026-10-01",
                "hasta": "2026-10-31",
                "marcas_incluidos": ["1"],
                "q_superart": ["SA1", "SA2"],
            }
        )
        self.assertEqual(f["meses"], ["2026-10"])
        self.assertEqual(f["superarts_incluidos"], ["SA1", "SA2"])


    def test_excluidos_marcas_y_superarts(self):
        f = parse_filters_from_payload(
            {
                "desde": "2026-10-01",
                "hasta": "2026-10-31",
                "marcas_excluidos": ["7", "8"],
                "superarts_excluidos": ["SAX"],
            }
        )
        self.assertEqual(f["marcas_excluidos"], [7, 8])
        self.assertEqual(f["superarts_excluidos"], ["SAX"])


class TestExcluidosBackend(SimpleTestCase):
    def test_agrupar_excluye_superart(self):
        from mpr.services_fabricados_superart import agrupar_fabricados_por_superart, superart_desde_id_manual

        rows = [
            {"id_articulo": 1, "id_manual": "AAA-01", "ym": "2026-10", "cantidad": 10},
            {"id_articulo": 2, "id_manual": "BBB-01", "ym": "2026-10", "cantidad": 5},
        ]
        cod_a = superart_desde_id_manual("AAA-01")[1]
        base = agrupar_fabricados_por_superart(rows, ["2026-10"], {})
        self.assertEqual(len(base["filas_superart"]), 2)
        res = agrupar_fabricados_por_superart(rows, ["2026-10"], {}, superarts_excluidos=[cod_a])
        codigos = [r["codigo_superart"] for r in res["filas_superart"]]
        self.assertNotIn(cod_a, codigos)
        self.assertEqual(res["total_general"], 5)

    def test_sql_marcas_excluidas_not_in(self):
        from mpr.reportes_transicion_lote_sql import fetch_fabricado_primera_por_articulo_mes

        cur = MagicMock()
        cur.fetchall.return_value = []
        fetch_fabricado_primera_por_articulo_mes(cur, ["2026-10"], marcas_excluidos_ids=[3, 4])
        sql, params = cur.execute.call_args[0]
        self.assertIn("NOT IN", sql)
        self.assertEqual(params[-2:], [3, 4])

    @patch("mpr.services_fabricados_superart.reporte_mpr_fabricados_superart")
    @patch("mpr.reportes_presentacion.preparar_fabricados_superart_presentacion")
    def test_runner_pasa_excluidos(self, mock_prep, mock_reporte):
        from reports.models import ReportDefinition
        from reports.services.fabricados_superart_runner import run_fabricados_superart

        mock_reporte.return_value = {"filas_superart": [], "kpis": {}}
        mock_prep.return_value = {"filas_superart": [], "kpis": {}, "total_general": 0}
        report = ReportDefinition(slug=FABRICADOS_SUPERART_SLUG, name="T", category="operational")
        run_fabricados_superart(
            report,
            {"filters": {"base_empresa": "emp1", "marcas_excluidos": ["9"], "superarts_excluidos": ["SAZ"]}},
            MagicMock(base_empresa="emp1"),
        )
        kwargs = mock_reporte.call_args.kwargs
        self.assertEqual(kwargs["marcas_excluidos"], [9])
        self.assertEqual(kwargs["superarts_excluidos"], ["SAZ"])


class TestRunnerRegistrado(SimpleTestCase):
    def test_query_runner_tiene_slug(self):
        src = inspect.getsource(QueryRunnerService.run)
        self.assertIn('"fabricados-superart"', src)

    @patch("mpr.services_fabricados_superart.reporte_mpr_fabricados_superart")
    @patch("mpr.reportes_presentacion.preparar_fabricados_superart_presentacion")
    def test_run_sin_mysql(self, mock_prep, mock_reporte):
        from reports.models import ReportDefinition

        mock_reporte.return_value = {"filas_superart": [], "kpis": {}}
        mock_prep.return_value = {"filas_superart": [], "kpis": {}, "total_general": 0}
        report = ReportDefinition(slug=FABRICADOS_SUPERART_SLUG, name="T", category="operational")
        user = MagicMock(base_empresa="emp1")
        svc = QueryRunnerService(user)
        result = svc.run(
            report,
            {"filters": {"desde": "2026-01-01", "hasta": "2026-01-31", "base_empresa": "emp1"}},
        )
        self.assertIn("fabricados", result.meta.get("extra", {}))


class TestMenuYTemplate(SimpleTestCase):
    def test_menu_mpr_tiene_entrada(self):
        from core.utils.utils import APPS_MENU

        mpr = next(m for m in APPS_MENU if m.get("id") == "mpr")
        reportes = next(s for s in mpr["submenus"] if "Reportes" in str(s.get("seccion", "")))
        ids = [it.get("menu_item_id") for it in reportes["items"]]
        self.assertIn("mpr_rep_fabricados_superart", ids)
        item = next(it for it in reportes["items"] if it.get("menu_item_id") == "mpr_rep_fabricados_superart")
        self.assertEqual(item["url_kwargs"]["slug"], FABRICADOS_SUPERART_SLUG)

    def test_dashboard_incluye_fsa(self):
        html = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "reports"
            / "dashboard_detail.html"
        ).read_text(encoding="utf-8")
        self.assertIn("filters_fabricados_superart.html", html)
        self.assertIn('id="fsa-section"', html)
        self.assertIn("fabricados_superart.js", html)
        self.assertNotIn("dashboard.js' %}?v=20261008a", html)

    def test_filtros_estandar(self):
        inc = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "reports"
            / "includes"
            / "filters_fabricados_superart.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("fsa-toggle-panel", inc)
        self.assertNotIn("refresh-interval-buttons", inc)
        for _id in ("marcas_incluidos", "marcas_excluidos", "superarts_incluidos", "superarts_excluidos"):
            self.assertIn(f'id="{_id}"', inc)


class TestDashboardJs(SimpleTestCase):
    def test_slug_en_dashboard_js(self):
        js = (Path(__file__).resolve().parents[1] / "static" / "reports" / "js" / "dashboard.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("isFabricadosSuperartSlug", js)
        self.assertIn("fabricados-superart", js)
        self.assertIn('"fabricados-superart": {', js)  # etiquetas modal de carga


class TestReportsPredictivoAPI(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    @patch("mpr.services_fabricados_superart.buscar_marcas_predictivo")
    def test_api_marcas_json(self, mock_buscar):
        mock_buscar.return_value = [{"value": 3, "label": "Marca"}]
        req = self.rf.get("/api/reports/fabricados-superart/marcas/buscar/?q=mar")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("mpr.reportes")
        resp = FabricadosSuperartMarcasBuscarAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["marcas"][0]["label"], "Marca")

    @patch("mpr.services_fabricados_superart.buscar_superart_predictivo")
    def test_api_superart_json(self, mock_buscar):
        mock_buscar.return_value = [{"codigo": "X", "descripcion": "X"}]
        req = self.rf.get("/api/reports/fabricados-superart/superart/buscar/?q=x")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("mpr.reportes")
        resp = FabricadosSuperartSuperartBuscarAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(data["superarts"][0]["codigo"], "X")


class TestMprRedirect(SimpleTestCase):
    @patch("mpr.views._get_base_empresa", return_value="empresa92")
    def test_url_vieja_redirige_a_reports(self, _base):
        from mpr.views import ReportesMPRView

        rf = RequestFactory()
        req = rf.get(
            "/mpr/reportes/?grupo=produccion&reporte=fabricados_superart"
            "&desde=2026-10-01&hasta=2026-10-31"
        )
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("mpr.reportes")
        resp = ReportesMPRView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("fabricados-superart", resp.url)
        self.assertIn("desde=2026-10-01", resp.url)
