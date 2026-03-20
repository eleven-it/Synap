# Tests TDD para la vista Reportes MPR (tipos desperdicio, produccion_operario, opt_cerradas). ESPEC_MPR_*.md

from unittest.mock import MagicMock, patch

from django.test import TestCase

from mpr.views import ReportesMPRView


class TestReportesMprDesperdicio(TestCase):
    """ESPEC_MPR_DESPERDICIO: GET reportes?tipo=desperdicio."""

    def test_get_desperdicio_context_filas_y_titulo(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {"tipo": "desperdicio"}
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_desperdicio", return_value=[]):
                context = view.get_context_data()
        self.assertEqual(context["tipo_reporte"], "desperdicio")
        self.assertIsInstance(context["filas"], list)
        self.assertEqual(context["titulo_reporte"], "Desperdicio / Scrap")


class TestReportesMprProduccionOperario(TestCase):
    """ESPEC_MPR_PRODUCCION_OPERARIO: GET reportes?tipo=produccion_operario."""

    def test_get_produccion_operario_context_filas_y_titulo(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {"tipo": "produccion_operario"}
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_produccion_por_operario", return_value=[]):
                context = view.get_context_data()
        self.assertEqual(context["tipo_reporte"], "produccion_operario")
        self.assertIsInstance(context["filas"], list)
        self.assertEqual(context["titulo_reporte"], "Producción por operario")


class TestReportesMprOptCerradas(TestCase):
    """ESPEC_MPR_OPT_CERRADAS: GET reportes?tipo=opt_cerradas."""

    def test_get_opt_cerradas_context_filas_y_titulo(self):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = {"tipo": "opt_cerradas"}
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.reporte_mpr_opt_cerradas", return_value=[]):
                context = view.get_context_data()
        self.assertEqual(context["tipo_reporte"], "opt_cerradas")
        self.assertIsInstance(context["filas"], list)
        self.assertEqual(context["titulo_reporte"], "OPT cerradas")
