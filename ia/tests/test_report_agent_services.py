from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from ia.forms import AgentQuickSetupForm
from ia.models import AgentDefinition, LlmProviderConfig, ProviderKind
from ia.services.date_range_service import DateRangeService
from ia.services.llm_gateway import LlmGatewayService
from ia.services.policy_gate import PolicyContext
from ia.services.report_agent_service import ReportAgentService
from ia.services.report_intent_refinement_service import ReportIntentHints, ReportIntentRefinementService
from ia.services.report_tools import InterpretedReportQuery, ReportToolsService
from unittest.mock import patch


class LlmGatewayOpenAiTokenParamTests(SimpleTestCase):
    def test_gpt5_usa_max_completion_tokens(self):
        self.assertEqual(
            LlmGatewayService._openai_chat_completion_token_key("gpt-5.4"),
            "max_completion_tokens",
        )

    def test_gpt4_usa_max_tokens(self):
        self.assertEqual(
            LlmGatewayService._openai_chat_completion_token_key("gpt-4.1"),
            "max_tokens",
        )


class DateRangeServiceTests(SimpleTestCase):
    def test_resuelve_este_mes(self):
        result = DateRangeService.resolve_from_text("Cuánto vendimos este mes", require_period=True)
        self.assertEqual(result.range_type, "calendar_month_current")
        self.assertIsNotNone(result.start_date)
        self.assertIsNotNone(result.end_date)
        self.assertFalse(result.requires_clarification)

    @patch("ia.services.date_range_service.date")
    def test_desde_mes_a_hoy_no_es_solo_el_dia_actual(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        result = DateRangeService.resolve_from_text(
            "Hola, necesito un ranking de ventas mensuales desde febrero a hoy",
            require_period=True,
        )
        self.assertEqual(result.range_type, "since_month_until_today")
        self.assertEqual(result.start_date, "2026-02-01")
        self.assertEqual(result.end_date, "2026-04-20")
        self.assertFalse(result.requires_clarification)

    @patch("ia.services.date_range_service.date")
    def test_desde_febrero_2025_hasta_hoy_respeta_ano_explicito(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        result = DateRangeService.resolve_from_text(
            "necesito un ranking de ventas mensuales desde febrero 2025 hasta hoy.",
            require_period=True,
        )
        self.assertEqual(result.range_type, "since_month_until_today")
        self.assertEqual(result.start_date, "2025-02-01")
        self.assertEqual(result.end_date, "2026-04-20")

    @patch("ia.services.date_range_service.date")
    def test_entre_abril_de_2025_y_hoy_no_es_solo_abril_2025(self, mock_date):
        """«entre abril de 2025 y hoy» debe ir hasta la fecha actual, no al 30/04/2025."""
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        result = DateRangeService.resolve_from_text(
            "dame un informe de ventas netas entre abril de 2025 y hoy",
            require_period=True,
        )
        self.assertEqual(result.range_type, "since_month_until_today")
        self.assertEqual(result.start_date, "2025-04-01")
        self.assertEqual(result.end_date, "2026-04-20")

    @patch("ia.services.date_range_service.date")
    def test_desde_febrero_de_2025_a_hoy(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        result = DateRangeService.resolve_from_text(
            "desde febrero de 2025 a hoy",
            require_period=True,
        )
        self.assertEqual(result.start_date, "2025-02-01")
        self.assertEqual(result.end_date, "2026-04-20")

    def test_rango_explicito_dd_mm_yyyy(self):
        result = DateRangeService.resolve_from_text("01-01-2026 y 31-01-2026", require_period=False)
        self.assertEqual(result.range_type, "explicit_calendar_range")
        self.assertEqual(result.start_date, "2026-01-01")
        self.assertEqual(result.end_date, "2026-01-31")

    def test_mes_nominal_con_anio_es_mes_calendario_completo(self):
        result = DateRangeService.resolve_from_text(
            "¿Cuál es la cantidad de facturas en el mes de febrero 2026?",
            require_period=False,
        )
        self.assertEqual(result.range_type, "calendar_month_named_year")
        self.assertEqual(result.start_date, "2026-02-01")
        self.assertEqual(result.end_date, "2026-02-28")

    def test_entre_dos_meses_nominales_con_anio(self):
        result = DateRangeService.resolve_from_text(
            "facturas entre enero 2025 y febrero 2026 en Casa Matriz",
            require_period=False,
        )
        self.assertEqual(result.range_type, "calendar_month_range_named")
        self.assertEqual(result.start_date, "2025-01-01")
        self.assertEqual(result.end_date, "2026-02-28")

    def test_entre_enero_y_diciembre_mismo_anio(self):
        result = DateRangeService.resolve_from_text(
            "cantidad de facturas entre enero y diciembre de 2025",
            require_period=False,
        )
        self.assertEqual(result.range_type, "calendar_month_range_same_year")
        self.assertEqual(result.start_date, "2025-01-01")
        self.assertEqual(result.end_date, "2025-12-31")

    @patch("ia.services.date_range_service.date")
    def test_hoy_sin_desde_sigue_siendo_un_dia(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        result = DateRangeService.resolve_from_text("Ventas de hoy", require_period=True)
        self.assertEqual(result.range_type, "calendar_day")
        self.assertEqual(result.start_date, "2026-04-20")
        self.assertEqual(result.end_date, "2026-04-20")

    @patch("ia.services.date_range_service.date")
    def test_desde_febrero_a_marzo_no_asume_hasta_hoy(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        result = DateRangeService.resolve_from_text("Ventas desde febrero a marzo", require_period=True)
        self.assertTrue(result.requires_clarification)

    @patch("ia.services.date_range_service.date")
    def test_mes_sin_anio_inferior_anio_actual(self, mock_date):
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        result = DateRangeService.resolve_from_text(
            "cuantos pedidos tenemos pendientes en abril?",
            require_period=True,
        )
        self.assertFalse(result.requires_clarification)
        self.assertEqual(result.range_type, "calendar_month_named_implicit_year")
        self.assertEqual(result.start_date, "2026-04-01")
        self.assertEqual(result.end_date, "2026-04-30")

    def test_mes_con_anio_explicito_no_usa_solo_inferencia(self):
        result = DateRangeService.resolve_from_text(
            "cuantos pedidos en abril 2025",
            require_period=True,
        )
        self.assertEqual(result.range_type, "calendar_month_named_year")
        self.assertEqual(result.start_date, "2025-04-01")
        self.assertEqual(result.end_date, "2025-04-30")

    def test_pide_aclaracion_si_falta_periodo(self):
        result = DateRangeService.resolve_from_text("Cuánto vendimos", require_period=True)
        self.assertTrue(result.requires_clarification)
        self.assertIn("período", result.clarification_question.lower())

    @patch("ia.services.date_range_service.date")
    def test_transcript_incluye_periodo_de_turnos_anteriores(self, mock_date):
        """Seguimientos sin fechas («Incluye PUIG») resuelven el rango si el transcript trae el período ya dicho."""
        mock_date.today.return_value = date(2026, 4, 20)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        combined = (
            "Usuario: dame un informe de ventas netas entre abril de 2025 y hoy. No incluyas al cliente PUIG\n"
            "Usuario: Incluye PUIG"
        )
        result = DateRangeService.resolve_from_text(combined, require_period=True)
        self.assertFalse(result.requires_clarification)
        self.assertEqual(result.start_date, "2025-04-01")
        self.assertEqual(result.end_date, "2026-04-20")


class ReportToolsClienteExclusionTests(SimpleTestCase):
    def setUp(self):
        self.policy = PolicyContext(
            user=None,
            owner_user=None,
            empresa=None,
            legacy_user_id=None,
            legacy_user_code="",
            base_empresa="empresa_demo",
            timezone="America/Argentina/Buenos_Aires",
            locale="es",
            permissions=set(),
        )

    @patch.object(ReportToolsService, "_buscar_clientes_por_nombre_fragmento")
    def test_varios_clientes_coinciden_pide_elegir(self, mock_buscar):
        mock_buscar.return_value = [
            {"id": 10, "label": "PUIG ARGENTINA S A"},
            {"id": 20, "label": "OTRO PUIG SRL"},
        ]
        q = ReportToolsService.interpret_query(
            "ventas netas este mes no incluyas al cliente puig",
            self.policy,
        )
        self.assertTrue(q.requires_clarification)
        self.assertIn("más de un cliente", (q.clarification_question or "").lower())
        self.assertIn("1.", q.clarification_question or "")

    @patch.object(ReportToolsService, "_buscar_clientes_por_nombre_fragmento")
    def test_un_cliente_aplica_clientes_excluidos(self, mock_buscar):
        mock_buscar.return_value = [{"id": 99, "label": "UNICO PUIG SA"}]
        q = ReportToolsService.interpret_query(
            "ventas netas este mes excepto el cliente puig unico",
            self.policy,
        )
        self.assertFalse(q.requires_clarification)
        self.assertEqual(q.filters.get("clientes_excluidos"), [99])
        self.assertEqual(q.metadata.get("clientes_excluidos_etiquetas"), ["UNICO PUIG SA"])


class ReportAgentPedidosDeterministicTextTests(SimpleTestCase):
    def test_pedidos_muestra_periodo_dd_mm_yyyy(self):
        policy = PolicyContext(
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
        svc = ReportAgentService(
            agent=SimpleNamespace(),
            policy_context=policy,
            selected_model=SimpleNamespace(),
        )
        report = SimpleNamespace(slug="pedidos-pendientes")
        result = SimpleNamespace(notes=[], data=[], totals={"total_subtotal_desc": 0.0})
        interpreted = SimpleNamespace(metadata={})
        date_range = SimpleNamespace(start_date="2025-04-01", end_date="2025-04-30")
        text = svc._build_deterministic_answer(
            message_text="",
            report=report,
            result=result,
            interpreted=interpreted,
            date_range=date_range,
        )
        self.assertIn("01/04/2025", text)
        self.assertIn("30/04/2025", text)
        self.assertNotIn("2025-04-01", text)


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

    def test_ranking_ventas_desde_mes_no_pide_periodo(self):
        interpreted = ReportToolsService.interpret_query(
            "Ranking de ventas mensuales desde febrero a hoy",
            self.policy_context,
        )
        self.assertEqual(interpreted.report_slug, "ventas_netas")
        self.assertEqual(interpreted.intent, "ranking")
        self.assertTrue(interpreted.metadata.get("ventas_netas_monthly_company_totals"))
        self.assertFalse(interpreted.requires_clarification)

    def test_interpreta_total_por_tipo_comprobantes(self):
        interpreted = ReportToolsService.interpret_query(
            "Dame el total por tipo de comprobantes y la cantidad de cada uno",
            self.policy_context,
        )
        self.assertEqual(interpreted.report_slug, "ventas_netas")
        self.assertTrue(interpreted.metadata.get("ventas_por_tipo_comprobante"))
        self.assertFalse(interpreted.requires_clarification)

    def test_multiturno_ventas_y_fechas_en_snippet(self):
        snippet = (
            "Usuario: Dame el total por tipo de comprobantes y la cantidad de cada uno\n"
            "Asistente: ¿Querés consultar ventas, pedidos, remitos o stock?\n"
            "Usuario: ventas\n"
            "Asistente: ¿Sobre qué período querés hacer la consulta?\n"
            "Usuario: 01-01-2026 y 31-01-2026"
        )
        interpreted = ReportToolsService.interpret_query(
            "01-01-2026 y 31-01-2026",
            self.policy_context,
            conversation_snippet=snippet,
        )
        self.assertEqual(interpreted.report_slug, "ventas_netas")
        self.assertTrue(interpreted.metadata.get("ventas_por_tipo_comprobante"))

    def test_snippet_por_tipo_no_anula_consulta_actual_de_cantidad_facturas(self):
        snippet = (
            "Usuario: Dame el total por tipo de comprobantes y la cantidad de cada uno\n"
            "Asistente: (respuesta previa)\n"
        )
        interpreted = ReportToolsService.interpret_query(
            "¿Cuál es la cantidad de facturas emitidas en febrero 2026? Dame el total por punto de venta.",
            self.policy_context,
            conversation_snippet=snippet,
        )
        self.assertEqual(interpreted.report_slug, "ventas_netas")
        self.assertTrue(interpreted.metadata.get("invoice_count_fa_fm"))
        self.assertTrue(interpreted.metadata.get("invoice_count_by_punto_venta"))
        self.assertFalse(interpreted.metadata.get("ventas_por_tipo_comprobante"))

    def test_facturas_por_pv_mes_x_mes_activa_desglose_mensual(self):
        interpreted = ReportToolsService.interpret_query(
            "¿Cuál es la cantidad de facturas en Casa Matriz en febrero 2026? Total por punto de venta mes x mes.",
            self.policy_context,
        )
        self.assertTrue(interpreted.metadata.get("invoice_count_by_punto_venta"))
        self.assertTrue(interpreted.metadata.get("invoice_count_by_punto_venta_mensual"))

    def test_total_de_ventas_comprobantes_x_mes_usa_report_ventas_netas_mensual(self):
        interpreted = ReportToolsService.interpret_query(
            "¿Cuál es el total de ventas en la sucursal casa matriz entre enero y diciembre de 2025 por comprobantes x mes?",
            self.policy_context,
        )
        self.assertTrue(interpreted.metadata.get("ventas_netas_monthly_company_totals"))
        self.assertFalse(interpreted.metadata.get("invoice_count_fa_fm_mensual"))
        self.assertFalse(interpreted.metadata.get("invoice_count_fa_fm"))

    @patch(
        "ia.services.report_tools.ReportToolsService._match_sucursal_from_text",
        return_value={"id": 1, "label": "Casa Matriz"},
    )
    def test_comprobantes_x_mes_sin_pv_activa_mensual_por_tipo(self, _mock_suc):
        interpreted = ReportToolsService.interpret_query(
            "¿Cuál es la cantidad de facturas emitidas en la sucursal casa matriz entre enero y diciembre de 2025 por comprobantes x mes",
            self.policy_context,
        )
        self.assertTrue(interpreted.metadata.get("invoice_count_fa_fm_mensual"))
        self.assertFalse(interpreted.metadata.get("invoice_count_by_punto_venta"))

    @patch(
        "ia.services.report_tools.ReportToolsService._match_sucursal_from_text",
        return_value={"id": 1, "label": "Casa Central"},
    )
    def test_interpreta_cantidad_facturas_por_sucursal(self, _mock_suc):
        interpreted = ReportToolsService.interpret_query(
            "¿Cuál es la cantidad de facturas emitidas en la sucursal Casa Central?",
            self.policy_context,
        )
        self.assertEqual(interpreted.report_slug, "ventas_netas")
        self.assertTrue(interpreted.metadata.get("invoice_count_fa_fm"))
        self.assertFalse(interpreted.requires_clarification)
        self.assertEqual(interpreted.filters.get("sucursales"), [1])

    def test_interpreta_cantidad_facturas_con_periodo_sin_sucursal(self):
        interpreted = ReportToolsService.interpret_query(
            "¿Cuál es la cantidad de facturas emitidas este mes?",
            self.policy_context,
        )
        self.assertEqual(interpreted.report_slug, "ventas_netas")
        self.assertTrue(interpreted.metadata.get("invoice_count_fa_fm"))
        self.assertFalse(interpreted.requires_clarification)

    def test_facturas_sucursal_no_encontrada_pide_aclaracion(self):
        interpreted = ReportToolsService.interpret_query(
            "¿Cuál es la cantidad de facturas emitidas en la sucursal XyzInexistente999?",
            self.policy_context,
        )
        self.assertTrue(interpreted.requires_clarification)
        self.assertIsNone(interpreted.report_slug)

    def test_interpreta_consulta_de_pedidos_pendientes(self):
        interpreted = ReportToolsService.interpret_query("Qué pedidos pendientes tenemos este mes", self.policy_context)
        self.assertEqual(interpreted.report_slug, "pedidos-pendientes")
        self.assertEqual(interpreted.intent, "status_query")

    def test_mpr_pedidos_usa_reporte_mpr_no_pedidos_deposito(self):
        interpreted = ReportToolsService.interpret_query(
            "Cuantos pedidos tenemos pendientes en MPR?",
            self.policy_context,
        )
        self.assertEqual(interpreted.report_slug, "mpr-pedidos-estado")
        self.assertTrue(interpreted.metadata.get("mpr_pedidos_por_estado"))
        self.assertFalse(interpreted.requires_clarification)

    def test_logistica_entregas_pendientes_usa_comprobantes_rutas(self):
        interpreted = ReportToolsService.interpret_query(
            "que entregas tenemos pendientes en logistica?",
            self.policy_context,
        )
        self.assertEqual(interpreted.report_slug, "comprobantes-rutas")
        self.assertEqual(interpreted.filters.get("logistica_estado_entrega"), "No")
        self.assertTrue(interpreted.metadata.get("logistica_lista_comprobantes_rutas"))

    def test_snippet_ventas_no_pisa_intencion_logistica(self):
        snippet = (
            "Usuario: ventas netas casa matriz\n"
            "Asistente: Ventas netas 16.454.168.579,39 entre 01/04/2025 y 20/04/2026.\n"
        )
        interpreted = ReportToolsService.interpret_query(
            "que entregas tenemos pendientes en logistica?",
            self.policy_context,
            conversation_snippet=snippet,
        )
        self.assertEqual(interpreted.report_slug, "comprobantes-rutas")
        self.assertNotEqual(interpreted.report_slug, "ventas_netas")

    def test_pide_aclaracion_cuando_no_detecta_reporte(self):
        interpreted = ReportToolsService.interpret_query("Cómo va el negocio", self.policy_context)
        self.assertTrue(interpreted.requires_clarification)
        self.assertIsNone(interpreted.report_slug)

    def test_detecta_saludo_como_chat_general(self):
        interpreted = ReportToolsService.interpret_query("Hola", self.policy_context)
        self.assertEqual(interpreted.intent, "general_chat")
        self.assertFalse(interpreted.requires_clarification)
        self.assertTrue(interpreted.metadata.get("general_chat"))

    @patch("ia.services.report_tools.ReportToolsService.list_authorized_reports")
    def test_resuelve_slug_real_desde_alias(self, mock_catalog):
        class Entry:
            def __init__(self, slug):
                self.slug = slug

        mock_catalog.return_value = [Entry("ventas-netas"), Entry("pedidos-pendientes")]
        resolved = ReportToolsService.resolve_actual_report_slug("ventas_netas", self.policy_context)
        self.assertEqual(resolved, "ventas-netas")


class ReportAgentServiceFacturasPvTextTests(SimpleTestCase):
    def test_sin_datos_mensaje_natural(self):
        text = ReportAgentService._texto_facturas_por_punto_venta(
            [],
            start_iso="2025-01-01",
            end_iso="2025-01-31",
            sucursal_label="Casa Central",
            locale="es",
            used_default_month=False,
        )
        self.assertIn("No hay facturas", text)

    def test_formato_por_pv_y_letras_sin_ceros(self):
        rows = [
            {"id_punto_venta": 1, "nro_punto_venta": 2, "tipo_comprobante": "FA", "cantidad": 2},
            {"id_punto_venta": 1, "nro_punto_venta": 2, "tipo_comprobante": "FB", "cantidad": 3},
            {"id_punto_venta": 1, "nro_punto_venta": 2, "tipo_comprobante": "FC", "cantidad": 10},
        ]
        text = ReportAgentService._texto_facturas_por_punto_venta(
            rows,
            start_iso="2026-01-01",
            end_iso="2026-01-31",
            sucursal_label="Casa Central",
            locale="es",
            used_default_month=False,
        )
        self.assertIn("Facturas de ventas", text)
        self.assertIn("Del 01/01/2026 al 31/01/2026", text)
        self.assertIn("Sucursal: Casa Central", text)
        self.assertIn("Punto de venta 2:", text)
        self.assertIn("FA: 2", text)
        self.assertIn("FB: 3", text)
        self.assertIn("FC: 10", text)
        self.assertNotIn("CodigoMovimiento", text)
        self.assertNotIn("FE:", text)
        self.assertNotIn("FM:", text)

    def test_fechas_locale_en_us(self):
        rows = [
            {"id_punto_venta": 1, "nro_punto_venta": 1, "tipo_comprobante": "FA", "cantidad": 1},
        ]
        text = ReportAgentService._texto_facturas_por_punto_venta(
            rows,
            start_iso="2026-02-01",
            end_iso="2026-02-28",
            sucursal_label=None,
            locale="en",
            used_default_month=False,
        )
        self.assertIn("02/01/2026", text)
        self.assertIn("02/28/2026", text)

    def test_mensual_un_solo_mes_muestra_titulo_mes(self):
        rows = [
            {
                "anio_mes": "2026-02",
                "id_punto_venta": 1,
                "nro_punto_venta": 2,
                "tipo_comprobante": "FA",
                "cantidad": 639,
            },
        ]
        text = ReportAgentService._texto_facturas_por_punto_venta_mensual(
            rows,
            sucursal_label="Casa Matriz",
            locale="es",
            used_default_month=False,
        )
        self.assertIn("Febrero 2026", text)
        self.assertIn("Del 01/02/2026 al 28/02/2026", text)
        self.assertIn("Punto de venta 2:", text)
        self.assertIn("FA: 639", text)

    def test_texto_mensual_por_tipo(self):
        rows = [
            {"anio_mes": "2025-01", "tipo_comprobante": "FA", "cantidad": 100},
            {"anio_mes": "2025-02", "tipo_comprobante": "FA", "cantidad": 50},
        ]
        text = ReportAgentService._texto_facturas_mensual_por_tipo(
            rows,
            sucursal_label="Casa Matriz",
            locale="es",
            used_default_month=False,
        )
        self.assertIn("Enero 2025", text)
        self.assertIn("Febrero 2025", text)
        self.assertIn("FA: 100", text)
        self.assertIn("Sucursal: Casa Matriz", text)

    def test_mensual_dos_meses_en_orden(self):
        rows = [
            {
                "anio_mes": "2026-01",
                "id_punto_venta": 1,
                "nro_punto_venta": 2,
                "tipo_comprobante": "FA",
                "cantidad": 10,
            },
            {
                "anio_mes": "2026-02",
                "id_punto_venta": 1,
                "nro_punto_venta": 2,
                "tipo_comprobante": "FA",
                "cantidad": 5,
            },
        ]
        text = ReportAgentService._texto_facturas_por_punto_venta_mensual(
            rows,
            sucursal_label=None,
            locale="es",
            used_default_month=False,
        )
        pos_enero = text.find("Enero 2026")
        pos_febrero = text.find("Febrero 2026")
        self.assertNotEqual(pos_enero, -1)
        self.assertNotEqual(pos_febrero, -1)
        self.assertLess(pos_enero, pos_febrero)


class ReportAgentServiceRollupTests(SimpleTestCase):
    def test_agrupa_meses_y_ordena_por_monto_desc(self):
        rows = [
            {"mes": "2026-01", "mes_formato": "01/2026", "ventas_netas": 100.0},
            {"mes": "2026-01", "mes_formato": "01/2026", "ventas_netas": 50.0},
            {"mes": "2026-02", "mes_formato": "02/2026", "ventas_netas": 300.0},
        ]
        rolled = ReportAgentService._rollup_ventas_netas_monthly(rows)
        self.assertEqual(len(rolled), 2)
        self.assertEqual(rolled[0]["mes"], "2026-02")
        self.assertEqual(rolled[0]["ventas_netas"], 300.0)
        self.assertEqual(rolled[1]["ventas_netas"], 150.0)

    def test_texto_mensual_ventas_netas_fechas_dd_mm_yyyy_y_bloques(self):
        policy = PolicyContext(
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
        svc = ReportAgentService(
            agent=SimpleNamespace(),
            policy_context=policy,
            selected_model=SimpleNamespace(),
        )
        report = SimpleNamespace(slug="ventas_netas")
        result = SimpleNamespace(notes=[], data=[], totals={"ventas_netas": 0})
        interpreted = SimpleNamespace(metadata={"sucursal_match": "Casa Matriz"})
        date_range = SimpleNamespace(start_date="2025-01-01", end_date="2025-12-31")
        monthly = [{"mes": "2025-10", "mes_formato": "10/2025", "ventas_netas": 100.0}]
        text = svc._build_deterministic_answer(
            message_text="",
            report=report,
            result=result,
            interpreted=interpreted,
            date_range=date_range,
            monthly_rollup=monthly,
        )
        self.assertIn("01/01/2025", text)
        self.assertIn("31/12/2025", text)
        self.assertIn("(sucursal: Casa Matriz)", text)
        self.assertIn("Total:", text)
        self.assertNotIn("2025-01-01", text)
        self.assertIn(":\n\n1.", text)
        self.assertRegex(text, r"Total: \$100\.00\.\s*$")


class ReportIntentRefinementUnitTests(SimpleTestCase):
    def test_parse_hints_extrae_json_en_bloque(self):
        raw = (
            'Aquí va:\n```json\n{"metrica": "importes_ventas", "desglose_mensual": true, '
            '"desglose_por_punto_venta": false, "confianza": 0.95}\n```'
        )
        h = ReportIntentRefinementService._parse_hints(raw)
        self.assertIsNotNone(h)
        self.assertEqual(h.metrica, "importes_ventas")
        self.assertTrue(h.desglose_mensual)
        self.assertFalse(h.desglose_por_punto_venta)

    def test_apply_hints_importes_mensual_quita_conteo(self):
        interpreted = InterpretedReportQuery(
            intent="status_query",
            report_slug="ventas_netas",
            requires_clarification=False,
            clarification_question=None,
            filters={},
            metadata={
                "invoice_count_fa_fm": True,
                "invoice_count_fa_fm_mensual": True,
            },
        )
        hints = ReportIntentHints(
            metrica="importes_ventas",
            desglose_mensual=True,
            desglose_por_punto_venta=False,
            confianza=0.92,
        )
        out = ReportToolsService.apply_llm_intent_hints(interpreted, hints)
        self.assertTrue(out.metadata.get("ventas_netas_monthly_company_totals"))
        self.assertNotIn("invoice_count_fa_fm", out.metadata)
        self.assertEqual(out.report_slug, "ventas_netas")

    def test_apply_hints_no_toca_pedidos(self):
        interpreted = InterpretedReportQuery(
            intent="status_query",
            report_slug="pedidos-pendientes",
            requires_clarification=False,
            clarification_question=None,
            filters={},
            metadata={},
        )
        hints = ReportIntentHints(
            metrica="importes_ventas",
            desglose_mensual=True,
            desglose_por_punto_venta=False,
            confianza=0.99,
        )
        out = ReportToolsService.apply_llm_intent_hints(interpreted, hints)
        self.assertEqual(out.report_slug, "pedidos-pendientes")
        self.assertEqual(out.metadata, {})


class AgentQuickSetupFormTests(TestCase):
    def test_autocompleta_configuracion_del_agente(self):
        provider, _created = LlmProviderConfig.objects.get_or_create(
            name="OpenAI Test Quick Setup",
            defaults={
                "provider_kind": ProviderKind.OPENAI,
                "is_active": True,
            },
        )
        agent = AgentDefinition.objects.create(
            slug="asistente-reportes-test",
            name="Asistente de Reportes Test",
            domain="reportes",
            is_active=False,
        )

        form = AgentQuickSetupForm(
            data={
                "default_provider": provider.id,
                "api_key_plain": "sk-test-12345678",
                "selected_model_name": "gpt-4.1",
            },
            agent=agent,
        )
        self.assertTrue(form.is_valid(), form.errors)
        agent = form.save()
        provider.refresh_from_db()
        agent.refresh_from_db()

        self.assertTrue(provider.is_configured)
        self.assertEqual(agent.default_provider_id, provider.id)
        self.assertEqual(agent.default_model_name, "gpt-4.1")
        self.assertEqual(agent.tool_use_model_name, "gpt-4.1")
        self.assertEqual(agent.memory_write_model_name, "gpt-4.1")
        self.assertTrue(agent.is_active)
