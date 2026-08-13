from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from ia.services.policy_gate import PolicyContext
from ia.services.report_agent_service import ReportAgentService
from ia.services.report_tools import ReportToolsService


def _policy(*, permissions=None, base_empresa="empresa_demo"):
    perms = {"mpr.ver"} if permissions is None else set(permissions)
    return PolicyContext(
        user=SimpleNamespace(is_authenticated=True),
        owner_user=None,
        empresa=None,
        legacy_user_id=1,
        legacy_user_code="test",
        base_empresa=base_empresa,
        timezone="America/Argentina/Buenos_Aires",
        locale="es",
        permissions=perms,
    )


class ReportToolsKardexIntentTests(SimpleTestCase):
    def setUp(self):
        self.policy = _policy()

    def test_trazabilidad_pack_semi_resuelve_kardex(self):
        interpreted = ReportToolsService.interpret_query(
            "trazabilidad del pack 907944-02 en Semi",
            self.policy,
        )
        self.assertEqual(interpreted.report_slug, "mpr-kardex-articulo")
        self.assertTrue(interpreted.metadata.get("mpr_kardex_articulo"))
        self.assertNotEqual(interpreted.report_slug, "stock-existencias")
        self.assertEqual(interpreted.filters.get("codigo_articulo"), "907944-02")

    def test_kardex_articulo_resuelve_kardex(self):
        interpreted = ReportToolsService.interpret_query(
            "kardex artículo",
            self.policy,
        )
        self.assertEqual(interpreted.report_slug, "mpr-kardex-articulo")
        self.assertTrue(interpreted.metadata.get("mpr_kardex_articulo"))

    def test_saldo_semi_no_usa_stock_existencias(self):
        interpreted = ReportToolsService.interpret_query(
            "saldo semi",
            self.policy,
        )
        self.assertEqual(interpreted.report_slug, "mpr-kardex-articulo")
        self.assertNotEqual(interpreted.report_slug, "stock-existencias")
        self.assertTrue(interpreted.metadata.get("deposito_hint_semi"))


class ExecuteKardexArticuloTests(SimpleTestCase):
    def setUp(self):
        self.policy = _policy()
        self.kardex_payload = {
            "articulo": {
                "id": 615,
                "codigo": "907944-02",
                "descripcion": "Pack prueba",
                "es_pack": True,
                "id_en_abm": 24,
            },
            "bom": {
                "componentes": [
                    {"id_articulo": 963, "codigo": "963", "cantidad": 2},
                ],
            },
            "deposito": {"id": 3, "nombre": "Semi Elaborado"},
            "movimientos": [
                {
                    "fecha_display": "01/03/2026",
                    "tipo_mov": "OPP",
                    "entrada": 10,
                    "salida": 0,
                    "saldo_corrido": 10,
                    "nro_comprobante": "MST-001",
                },
            ],
            "kpis": {
                "saldo_final": 362,
                "total_entradas": 400,
                "total_salidas": 38,
                "max_packs": 181,
            },
            "advertencias": [],
        }

    @patch("ia.services.mpr_kardex_tools.construir_kardex_articulo")
    @patch("ia.services.mpr_kardex_tools.get_deposito_semi_elaborado_mpr", return_value=3)
    @patch("ia.services.mpr_kardex_tools.buscar_articulos")
    def test_execute_resuelve_codigo_y_devuelve_saldo(
        self, mock_buscar, _mock_semi, mock_construir
    ):
        from ia.services.mpr_kardex_tools import execute_kardex_articulo

        mock_buscar.return_value = [
            {"id_articulo": 615, "codigo_manual": "907944-02", "descripcion_articulo": "Pack prueba"},
        ]
        mock_construir.return_value = self.kardex_payload

        result = execute_kardex_articulo(
            self.policy,
            {
                "codigo_articulo": "907944-02",
                "fecha_desde": "2026-03-01",
                "fecha_hasta": "2026-03-31",
            },
        )

        self.assertFalse(result.get("requires_clarification"))
        self.assertEqual(result["status"], "success")
        mock_construir.assert_called_once()
        call_kw = mock_construir.call_args
        self.assertEqual(call_kw[0][1], 615)
        self.assertEqual(call_kw[1]["id_deposito"], 3)
        answer = result["answer"]
        self.assertIn("362", answer)
        self.assertIn("181", answer)
        self.assertIn("01/03/2026", answer)
        self.assertNotIn("2026-03-01", answer)
        payload = result["payload"]
        self.assertEqual(payload["kpis"]["saldo_final"], 362)
        self.assertLessEqual(len(payload["movimientos_recientes"]), 20)

    @patch("ia.services.mpr_kardex_tools.buscar_articulos")
    def test_articulo_ambiguo_pide_clarificacion_sin_sql(self, mock_buscar):
        from ia.services.mpr_kardex_tools import execute_kardex_articulo

        mock_buscar.return_value = [
            {"id_articulo": 1, "codigo_manual": "907944-01", "descripcion_articulo": "Pack A"},
            {"id_articulo": 2, "codigo_manual": "907944-02", "descripcion_articulo": "Pack B"},
        ]

        result = execute_kardex_articulo(
            self.policy,
            {"codigo_articulo": "907944"},
        )

        self.assertTrue(result["requires_clarification"])
        self.assertIn("artículo", (result["clarification_question"] or "").lower())
        self.assertEqual(result["status"], "partial")

    def test_sin_permiso_mpr_deniega_en_espanol(self):
        from ia.services.mpr_kardex_tools import execute_kardex_articulo

        policy = _policy(permissions=set())
        result = execute_kardex_articulo(
            policy,
            {"codigo_articulo": "907944-02"},
        )

        self.assertTrue(result["requires_clarification"])
        self.assertIn("permiso", (result["clarification_question"] or "").lower())
        self.assertEqual(result["status"], "partial")


class ReportAgentKardexEarlyBranchTests(SimpleTestCase):
    @patch("ia.services.report_agent_service.execute_kardex_articulo")
    @patch("ia.services.report_tools.ReportToolsService.resolve_actual_report_slug")
    @patch("ia.services.report_tools.ReportToolsService.get_report_definition")
    def test_handle_query_kardex_sin_report_definition(
        self, mock_get_report, mock_resolve, mock_execute
    ):
        mock_resolve.return_value = None
        mock_execute.return_value = {
            "answer": "Kardex del pack 907944-02 en Semi: saldo 362, max_packs 181.",
            "payload": {"kpis": {"saldo_final": 362, "max_packs": 181}},
            "requires_clarification": False,
            "status": "success",
        }

        policy = _policy()
        svc = ReportAgentService(
            agent=SimpleNamespace(),
            policy_context=policy,
            selected_model=SimpleNamespace(),
        )
        result = svc.handle_query("trazabilidad del pack 907944-02 en Semi")

        self.assertEqual(result.execution_status, "success")
        self.assertEqual(result.used_report_slug, "mpr-kardex-articulo")
        self.assertIn("362", result.answer)
        mock_get_report.assert_not_called()
        mock_execute.assert_called_once()
