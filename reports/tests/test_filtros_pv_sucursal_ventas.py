# -*- coding: utf-8 -*-
"""Oleada 1 + Fase 8: whitelist PV y regresión sin filtros sucursal/PV."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from reports.services.ventas_mensuales_licenciatarios_query import build_anet_sales_sql
from reports.services.ventas_netas import get_ventas_netas
from reports.views import DashboardDetailView, SLUGS_VENTAS_CON_PUNTO_VENTA

WHITELIST_VENTAS_PV = frozenset(
    {
        "ventas-objetivos-vs-bo",
        "ventas-por-vendedor",
        "ventas-por-articulo",
        "ventas-marca-superart",
        "ventas-bom-docenas",
        "ventas-marcas-mensual",
    }
)

BO_FILTERS_TEMPLATE = (
    "reports/includes/filters_bo_punto_venta_sucursales_depositos_clientes.html"
)
DASHBOARD_JS_PATH = (
    Path(__file__).resolve().parents[1] / "static" / "reports" / "js" / "dashboard.js"
)


def _render_bo_filters(slug: str, *, mostrar_filtro_punto_venta: bool) -> str:
    report = MagicMock()
    report.slug = slug
    return render_to_string(
        BO_FILTERS_TEMPLATE,
        {"report": report, "mostrar_filtro_punto_venta": mostrar_filtro_punto_venta},
    )


class TestOleada1Whitelist(SimpleTestCase):
    """Contrato Oleada 1: PV visible en ventas BO; ausente en bo-stock-facturacion."""

    def test_whitelist_slugs_ventas_con_pv_exists(self):
        self.assertIsInstance(SLUGS_VENTAS_CON_PUNTO_VENTA, frozenset)
        self.assertEqual(SLUGS_VENTAS_CON_PUNTO_VENTA, WHITELIST_VENTAS_PV)
        self.assertNotIn("bo-stock-facturacion", SLUGS_VENTAS_CON_PUNTO_VENTA)

    @patch.object(DashboardDetailView, "get_report")
    def test_dashboard_detail_context_mostrar_pv_true_for_ventas_slugs(self, mock_get_report):
        view = DashboardDetailView()
        view.request = MagicMock()
        view.kwargs = {}

        for slug in WHITELIST_VENTAS_PV:
            with self.subTest(slug=slug):
                report = MagicMock()
                report.slug = slug
                report.config = {}
                report.widgets.all.return_value = []
                mock_get_report.return_value = report

                context = view.get_context_data()
                self.assertTrue(
                    context["mostrar_filtro_punto_venta"],
                    msg=f"Se esperaba mostrar_filtro_punto_venta=True para {slug}",
                )

    def test_template_bo_muestra_punto_venta_para_ventas_slugs(self):
        for slug in WHITELIST_VENTAS_PV:
            with self.subTest(slug=slug):
                html = _render_bo_filters(slug, mostrar_filtro_punto_venta=True)
                self.assertIn('id="punto_venta"', html)
                self.assertIn("Vacío = todos los puntos de venta", html)
                self.assertIn("sm:col-span-2 lg:col-span-6", html)

    def test_bo_stock_facturacion_no_muestra_punto_venta(self):
        html = _render_bo_filters(
            "bo-stock-facturacion",
            mostrar_filtro_punto_venta=False,
        )
        self.assertNotIn('id="punto_venta"', html)

    def test_dashboard_js_gate_punto_venta_ventas_slugs(self):
        content = DASHBOARD_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("const SLUGS_VENTAS_PV = new Set([", content)
        for slug in WHITELIST_VENTAS_PV:
            self.assertIn(f'"{slug}"', content)
        self.assertNotIn('"bo-stock-facturacion"', content.split("SLUGS_VENTAS_PV")[1].split(");")[0])
        self.assertIn(
            "loadPuntoVentaOptions = !isBoReport || isVentasMarcasMensualSlug(reportSlug) || SLUGS_VENTAS_PV.has(reportSlug)",
            content,
        )

    def test_smoke_whitelist_todos_slugs_muestran_punto_venta(self):
        """Fase 8.6: sustituto smoke browser — cada slug whitelist renderiza PV."""
        for slug in WHITELIST_VENTAS_PV:
            with self.subTest(slug=slug):
                html = _render_bo_filters(slug, mostrar_filtro_punto_venta=True)
                self.assertIn('id="punto_venta"', html)


def _extract_js_block(content: str, start_marker: str, end_marker: str) -> str:
    start = content.index(start_marker)
    end = content.index(end_marker, start)
    return content[start:end]


class TestFase8Regresion(SimpleTestCase):
    """Fase 8: regresión payload filtros y slugs excluidos de sucursal/PV."""

    def test_regression_no_filters_totals_unchanged(self):
        """Sin selección, sucursales/PV no se envían y SQL no agrega cláusulas IN."""
        content = DASHBOARD_JS_PATH.read_text(encoding="utf-8")
        bo_block = _extract_js_block(
            content,
            "} else if (isInformeBoDualPeriodo(currentReportSlug)) {",
            '} else if (currentReportSlug === "stock-existencias") {',
        )
        self.assertIn(
            "if (selectedPVs.length > 0) filters.punto_venta = selectedPVs",
            bo_block,
        )
        self.assertIn(
            "if (selectedSucursales.length > 0) filters.sucursales = selectedSucursales",
            bo_block,
        )

        sql_anet = build_anet_sales_sql(sucursales=None, puntos_venta=None)
        self.assertNotIn("cc.CodSucursal IN", sql_anet)
        self.assertNotIn("cc.id_pv IN", sql_anet)

        mock_cm = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cm.__enter__.return_value = mock_conn
        mock_cm.__exit__.return_value = False
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.description = [
            ("periodo",),
            ("periodo_etiqueta",),
            ("ventas_netas",),
        ]
        mock_cursor.fetchall.return_value = []

        with patch("reports.services.ventas_netas.get_mysql_pool") as mock_pool:
            mock_pool.return_value.get_connection.return_value = mock_cm
            get_ventas_netas(
                base_empresa="emp_test",
                fecha_desde=date(2026, 1, 1),
                fecha_hasta=date(2026, 1, 31),
                vendedor_id=None,
            )
        sql_vn, _params = mock_cursor.execute.call_args[0]
        self.assertNotIn("cc.CodSucursal IN", sql_vn)
        self.assertNotIn("cc.id_pv IN", sql_vn)

    def test_regression_pedidos_remitos_sin_filtros_pv(self):
        """pedidos-pendientes y remitos-no-facturados no agregan sucursales/PV al payload."""
        content = DASHBOARD_JS_PATH.read_text(encoding="utf-8")
        get_filters_body = content.split("window.getFilters = () => {", 1)[1]

        ped_block = _extract_js_block(
            get_filters_body,
            "} else if (isPedidosPendientesSlug(currentReportSlug)) {",
            "} else if (isLogisticaListaComprobantesRutasSlug(currentReportSlug)) {",
        )
        self.assertNotIn("filters.sucursales", ped_block)
        self.assertNotIn("filters.punto_venta", ped_block)

        self.assertNotIn('currentReportSlug === "remitos-no-facturados"', get_filters_body)
        self.assertIn('currentReportSlug === "uninvoiced_remitos"', get_filters_body)


class TestAlcanceSucursalPvVisible(SimpleTestCase):
    """Informes y Excel declaran sucursales/PV por nombre (vacío = Todas/Todos)."""

    def test_tags_filter_expone_helper_de_alcance(self):
        tags_path = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "reports"
            / "js"
            / "tags_filter.mjs"
        )
        content = tags_path.read_text(encoding="utf-8")
        self.assertIn("export function formatSucursalPvScopeText", content)
        self.assertIn("Sucursales:", content)
        self.assertIn("Puntos de venta:", content)

    def test_dashboard_js_concatena_alcance_en_resumen(self):
        content = DASHBOARD_JS_PATH.read_text(encoding="utf-8")
        self.assertIn("withSucursalPvScope", content)
        self.assertIn("formatSucursalPvScopeText", content)
        self.assertNotIn(
            "formatSucursalPvScopeText } from",
            content,
            msg="dashboard.js no debe importar formatSucursalPvScopeText: rompe si tags_filter.mjs está en caché vieja",
        )
