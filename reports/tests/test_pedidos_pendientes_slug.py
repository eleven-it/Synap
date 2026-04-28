# Tests: slug canónico pedidos-pendientes y redirección desde pending_orders.

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase
from django.urls import resolve

from reports.models import ReportDefinition
from reports.services.query_runner import QueryResult, QueryRunnerService
from reports.services.schema_service import DefaultWidgetSchema, DimensionSchema, ReportSchemaService


def _reporte_pedidos_pendientes(config=None):
    report = MagicMock(spec=ReportDefinition)
    report.slug = "pedidos-pendientes"
    report.name = "Pedidos pendientes"
    report.category = "operational"
    report.version = "1.0.0"
    report.config = config if config is not None else {}
    return report


class TestPedidosPendientesQueryRunner(TestCase):
    """El runner legacy debe enrutar solo slug pedidos-pendientes a _run_pending_orders."""

    def test_slug_pedidos_pendientes_llama_run_pending_orders(self):
        report = _reporte_pedidos_pendientes()
        payload = {"filters": {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-31", "base_empresa": "test_db"}}
        user = MagicMock()
        user.base_empresa = None
        fake = QueryResult(
            meta={"slug": "pedidos-pendientes"},
            data=[{"fecha": "01/01/2026", "subtotal_desc": 1.0}],
            totals={"total_subtotal_desc": 1.0},
            notes=["ok"],
        )
        with patch.object(QueryRunnerService, "_run_pending_orders", return_value=fake) as mock_run:
            result = QueryRunnerService(user).run(report, payload)
        mock_run.assert_called_once()
        self.assertEqual(result.data[0]["subtotal_desc"], 1.0)

    def test_slug_pending_orders_no_ejecuta_run_pending_orders_en_runner(self):
        """API y vistas ya no usan este slug; el runner cae en datos de muestra vacíos."""
        report = MagicMock(spec=ReportDefinition)
        report.slug = "pending_orders"
        report.name = "Legacy"
        report.category = "operational"
        report.version = "1.0.0"
        report.config = {}
        payload = {"filters": {}}
        result = QueryRunnerService(MagicMock()).run(report, payload)
        self.assertEqual(result.data, [])
        self.assertTrue(any("not implemented" in n.lower() for n in result.notes))

    def test_cache_ttl_incluye_pedidos_pendientes(self):
        runner = QueryRunnerService(MagicMock())
        ttl = runner._get_cache_ttl("pedidos-pendientes", {})
        self.assertEqual(ttl, 300)


class TestPedidosPendientesSchemaAgrupacion(TestCase):
    """Schema API: sin agrupación precargada para pedidos-pendientes."""

    def test_quita_agrupacion_inicial_en_tabla(self):
        svc = ReportSchemaService()
        w = DefaultWidgetSchema(
            id="widget_1",
            kind="table",
            title="Tabla",
            options={
                "grouping": {
                    "enabled": True,
                    "fields": ["fecha"],
                    "collapsed_by_default": True,
                    "show_totals": True,
                }
            },
        )
        out = svc._pedidos_pendientes_sin_agrupacion_inicial("pedidos-pendientes", [w])
        self.assertEqual(len(out), 1)
        g = out[0].options.get("grouping") or {}
        self.assertFalse(g.get("enabled"))
        self.assertEqual(g.get("fields"), ["fecha"])

    def test_no_modifica_otros_slugs(self):
        svc = ReportSchemaService()
        w = DefaultWidgetSchema(
            id="widget_1",
            kind="table",
            title="Tabla",
            options={"grouping": {"enabled": True, "fields": ["fecha"]}},
        )
        out = svc._pedidos_pendientes_sin_agrupacion_inicial("remitos-no-facturados", [w])
        self.assertTrue(out[0].options["grouping"]["enabled"])
        self.assertEqual(out[0].options["grouping"]["fields"], ["fecha"])


class TestPedidosPendientesSchemaColumnasOcultas(TestCase):
    """Schema: sin dimensiones ni filas de tabla para tipo_comprobante / estado."""

    def test_quita_tipo_y_estado_dimensiones_y_filas_legacy(self):
        svc = ReportSchemaService()
        dims = [
            DimensionSchema("fecha", "Fecha", "", "date", "time", None),
            DimensionSchema("tipo_comprobante", "Tipo", "", "category", None, None),
            DimensionSchema("estado", "Estado", "", "category", None, None),
            DimensionSchema("nro_comprobante", "N°", "", "string", None, None),
        ]
        w = DefaultWidgetSchema(
            id="widget_1",
            kind="table",
            title="Tabla",
            options={
                "legacy_config": {
                    "rows": ["fecha", "tipo_comprobante", "nro_comprobante", "estado"],
                },
                "table_dimensions": [
                    "fecha",
                    "tipo_comprobante",
                    "nro_comprobante",
                    "estado",
                ],
            },
        )
        d2, w2 = svc._pedidos_pendientes_sin_columnas_tipo_y_estado("pedidos-pendientes", dims, [w])
        self.assertEqual([d.name for d in d2], ["fecha", "nro_comprobante"])
        self.assertEqual(
            w2[0].options["legacy_config"]["rows"],
            ["fecha", "nro_comprobante"],
        )
        self.assertEqual(
            w2[0].options["table_dimensions"],
            ["fecha", "nro_comprobante"],
        )

    def test_no_toca_otros_slugs(self):
        svc = ReportSchemaService()
        dims = [
            DimensionSchema("tipo_comprobante", "Tipo", "", "category", None, None),
        ]
        w = DefaultWidgetSchema(
            id="w1",
            kind="table",
            title="T",
            options={"legacy_config": {"rows": ["tipo_comprobante"]}},
        )
        d2, w2 = svc._pedidos_pendientes_sin_columnas_tipo_y_estado("remitos-no-facturados", dims, [w])
        self.assertEqual(len(d2), 1)
        self.assertEqual(w2[0].options["legacy_config"]["rows"], ["tipo_comprobante"])


class TestPendingOrdersRedirect(TestCase):
    """Ruta histórica /reports/dashboard/pending_orders/ redirige al slug canónico."""

    def test_redirect_permanente_a_pedidos_pendientes(self):
        # Sin pasar por ModuleMiddleware (el cliente HTTP puede devolver 302 si el módulo reports está inactivo).
        rf = RequestFactory()
        request = rf.get("/reports/dashboard/pending_orders/")
        match = resolve("/reports/dashboard/pending_orders/")
        response = match.func(request)
        self.assertEqual(response.status_code, 301)
        loc = response.get("Location", "")
        self.assertIn("pedidos-pendientes", loc)
        self.assertIn("/reports/dashboard/", loc)
