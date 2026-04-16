from django.test import SimpleTestCase

from ia.services.date_range_service import DateRangeService
from ia.services.policy_gate import PolicyContext
from ia.services.report_tools import ReportToolsService


class DateRangeServiceTests(SimpleTestCase):
    def test_resuelve_este_mes(self):
        result = DateRangeService.resolve_from_text("Cuánto vendimos este mes", require_period=True)
        self.assertEqual(result.range_type, "calendar_month_current")
        self.assertIsNotNone(result.start_date)
        self.assertIsNotNone(result.end_date)
        self.assertFalse(result.requires_clarification)

    def test_pide_aclaracion_si_falta_periodo(self):
        result = DateRangeService.resolve_from_text("Cuánto vendimos", require_period=True)
        self.assertTrue(result.requires_clarification)
        self.assertIn("período", result.clarification_question.lower())


class ReportToolsServiceTests(SimpleTestCase):
    def setUp(self):
        self.policy_context = PolicyContext(
            user=None,
            owner_user=None,
            empresa=None,
            legacy_user_id=None,
            legacy_user_code="",
            base_empresa="",
            timezone="America/Argentina/Buenos_Aires",
            locale="es",
            permissions=set(),
        )

    def test_interpreta_consulta_de_ventas(self):
        interpreted = ReportToolsService.interpret_query("Compará las ventas de este mes contra el anterior", self.policy_context)
        self.assertEqual(interpreted.report_slug, "sales_summary")
        self.assertEqual(interpreted.intent, "comparative_analysis")
        self.assertFalse(interpreted.requires_clarification)

    def test_interpreta_consulta_de_pedidos_pendientes(self):
        interpreted = ReportToolsService.interpret_query("Qué pedidos pendientes tenemos este mes", self.policy_context)
        self.assertEqual(interpreted.report_slug, "pedidos-pendientes")
        self.assertEqual(interpreted.intent, "status_query")

    def test_pide_aclaracion_cuando_no_detecta_reporte(self):
        interpreted = ReportToolsService.interpret_query("Cómo va el negocio", self.policy_context)
        self.assertTrue(interpreted.requires_clarification)
        self.assertIsNone(interpreted.report_slug)
