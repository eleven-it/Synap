"""Tests hub reportes MPR — shell, redirects, CSV."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from mpr.export import filas_a_csv
from mpr.reportes_hub import parse_periodo, resolver_grupo_reporte
from mpr.views import ReportesMPRView


class TestReportesHubHelpers(SimpleTestCase):
    def test_parse_periodo_default_7_dias(self):
        p = parse_periodo(None, None)
        self.assertEqual((p["fecha_hasta"] - p["fecha_desde"]).days, 6)

    def test_resolver_default_produccion_resumen(self):
        g, r = resolver_grupo_reporte({})
        self.assertEqual(g, "produccion")
        self.assertEqual(r, "resumen_diario")

    def test_tipo_antiguo_pendiente_opt_cae_en_default(self):
        g, r = resolver_grupo_reporte({"tipo": "pendiente"})
        self.assertEqual(g, "produccion")
        self.assertEqual(r, "resumen_diario")

    def test_tipo_produccion_operario_redirige_moderno(self):
        g, r = resolver_grupo_reporte({"tipo": "produccion_operario"})
        self.assertEqual(g, "produccion")
        self.assertEqual(r, "operario")

    def test_filas_a_csv_bom(self):
        data = filas_a_csv([{"a": 1}], [("a", "Col A")])
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertIn(b"Col A", data)


class TestReportesMprViewHub(TestCase):
    def test_default_context_resumen_diario(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {}
        payload = {
            "kpis": {"enviado": 0, "parte": 0, "clasificado": 0, "scrap_pct": 0},
            "dias": [],
            "totales": {},
        }
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_resumen_diario", return_value=payload):
                ctx = view.get_context_data()
        self.assertEqual(ctx["grupo"], "produccion")
        self.assertEqual(ctx["reporte"], "resumen_diario")

    def test_csv_resumen_diario(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {"format": "csv", "grupo": "produccion", "reporte": "resumen_diario"}
        payload = {
            "kpis": {},
            "dias": [{"fecha_display": "01/07/2026", "enviado": 10, "parte": 8, "clasificado": 7, "scrap": 1, "scrap_pct": 14.3, "gap_envio_parte": 2}],
            "totales": {},
        }
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_resumen_diario", return_value=payload):
                resp = view.get(view.request)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])

    def test_tipo_opt_cerradas_no_expone_legacy(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {"tipo": "opt_cerradas"}
        payload = {"kpis": {}, "dias": [], "totales": {}}
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_resumen_diario", return_value=payload):
                ctx = view.get_context_data()
        self.assertEqual(ctx["grupo"], "produccion")
        self.assertEqual(ctx["reporte"], "resumen_diario")
