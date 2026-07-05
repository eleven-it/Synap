# Tests vista Reportes MPR (hub flujo MPR diario). ESPEC_MPR_*.md

from unittest.mock import MagicMock, patch

from django.test import TestCase

from mpr.views import ReportesMPRView


class TestReportesMprProduccionOperario(TestCase):
    """ESPEC_MPR_PRODUCCION_OPERARIO: tipo=produccion_operario → operario desde parte."""

    def test_get_produccion_operario_moderno(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {"tipo": "produccion_operario"}
        payload = {"kpis": {}, "filas": []}
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_operario_parte", return_value=payload):
                context = view.get_context_data()
        self.assertEqual(context["grupo"], "produccion")
        self.assertEqual(context["reporte"], "operario")
        self.assertEqual(context["titulo_reporte"], "Por operario")


class TestReportesMprStockDemanda(TestCase):
    def test_tipo_stock_redirige_demanda(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {"tipo": "stock"}
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_stock", return_value=[]):
                context = view.get_context_data()
        self.assertEqual(context["grupo"], "demanda")
        self.assertEqual(context["reporte"], "stock")
