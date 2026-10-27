# -*- coding: utf-8 -*-
"""Tests informe pedidos-pendientes-produccion (sin MySQL)."""
import inspect
import unittest
from unittest.mock import MagicMock, patch

from reports.permissions import (
    PEDIDOS_PENDIENTES_PRODUCCION_SLUG,
    user_can_access_pedidos_pendientes_produccion,
)
from reports.services.pedidos_pendientes_produccion_calcs import (
    aggregate_totals,
    build_viajante_sql,
    classify_depositos_stock_columns,
    compute_disponible_backorder,
    compute_mpr_pack_fields,
    enrich_articulo_row,
    sql_unidad_base_join,
    sql_unidad_base_select,
)
import reports.services.pedidos_pendientes_produccion_runner as ppp_runner_mod
from reports.services.pedidos_pendientes_produccion_seed import (
    PEDIDOS_PENDIENTES_PRODUCCION_SLUG as SEED_SLUG,
    _report_defaults,
)
from reports.services.query_runner import QueryRunnerService
from reports.views import SLUGS_VENTAS_CON_PUNTO_VENTA


class TestDisponibleBackorder(unittest.TestCase):
    def test_referencia_1478(self):
        d, b = compute_disponible_backorder(1500, 628)
        self.assertEqual(d, 0.0)
        self.assertEqual(b, 872.0)

    def test_referencia_262(self):
        d, b = compute_disponible_backorder(12, 1483)
        self.assertEqual(d, 1471.0)
        self.assertEqual(b, 0.0)

    def test_referencia_444(self):
        d, b = compute_disponible_backorder(120, 0)
        self.assertEqual(d, 0.0)
        self.assertEqual(b, 120.0)

    def test_pendiente_mayor_que_terminado_disponible_cero(self):
        d, b = compute_disponible_backorder(100, 40)
        self.assertEqual(d, 0.0)
        self.assertEqual(b, 60.0)
        self.assertGreaterEqual(d, 0.0)

    def test_enrich_nunca_disponible_negativo(self):
        art = {"pendiente_qty": 500, "stock_terminado": 10}
        enrich_articulo_row(art)
        self.assertEqual(art["disponible"], 0.0)
        self.assertEqual(art["backorder"], 490.0)


class TestMprPackFields(unittest.TestCase):
    def test_a_fabricar_cero_muestra_demanda_y_ceros(self):
        mpr = compute_mpr_pack_fields(100, 150, 10)
        self.assertEqual(mpr["mpr_demanda_pedido"], 100.0)
        self.assertEqual(mpr["mpr_cantidad_a_fabricar"], 0.0)
        self.assertEqual(mpr["mpr_stock_terminado"], 150.0)
        self.assertEqual(mpr["mpr_stock_reserva"], 10.0)
        self.assertEqual(mpr["mpr_brecha_vs_pendiente"], 100.0)

    def test_brecha_con_fabricar(self):
        mpr = compute_mpr_pack_fields(100, 5, 0)
        self.assertEqual(mpr["mpr_cantidad_a_fabricar"], 95.0)
        self.assertEqual(mpr["mpr_brecha_vs_pendiente"], 5.0)

    def test_enrich_articulo_sin_fila_mpr_externa(self):
        art = {"pendiente_qty": 120, "stock_terminado": 0, "stock_produccion": 84}
        enrich_articulo_row(art, 0)
        self.assertEqual(art["backorder"], 120.0)
        self.assertEqual(art["mpr_cantidad_a_fabricar"], 120.0)
        self.assertIsNotNone(art["mpr_demanda_pedido"])


class TestClasificacionDepositos(unittest.TestCase):
    def test_solo_suma_stock_activos(self):
        deps = [
            {"CodDeposito": 1, "tipo_mpr": "Terminado", "suma_stock": "Si", "anulado": "No"},
            {"CodDeposito": 2, "tipo_mpr": "Produccion", "suma_stock": "Si", "anulado": "No"},
            {"CodDeposito": 3, "tipo_mpr": "Terminado", "suma_stock": "No", "anulado": "No"},
            {"CodDeposito": 4, "tipo_mpr": "Terminado", "suma_stock": "Si", "anulado": "Si"},
        ]
        term, prod = classify_depositos_stock_columns(deps)
        self.assertEqual(term, [1])
        self.assertEqual(prod, [2])


class TestUnidadBaseSql(unittest.TestCase):
    def test_join_unidmed_en_helpers(self):
        self.assertIn("unidmed", sql_unidad_base_join())
        self.assertIn("id_unimed", sql_unidad_base_join())
        self.assertIn("nombre_unimed", sql_unidad_base_select())

    def test_runner_no_usa_tipo_unidad_stockp(self):
        src = inspect.getsource(ppp_runner_mod)
        self.assertIn("sql_unidad_base_join", src)
        self.assertNotIn("sp.tipo_unidad", src)


class TestAggregateTotals(unittest.TestCase):
    def test_sin_total_brecha_y_articulos_con_backorder(self):
        arts = [
            {
                "pendiente_qty": 10,
                "stock_terminado": 0,
                "stock_produccion": 0,
                "disponible": -10,
                "backorder": 10,
                "importe_pendiente": 100,
                "mpr_demanda_pedido": 10,
                "mpr_cantidad_a_fabricar": 10,
                "mpr_brecha_vs_pendiente": 0,
            },
            {
                "pendiente_qty": 5,
                "stock_terminado": 100,
                "stock_produccion": 0,
                "disponible": 95,
                "backorder": 0,
                "importe_pendiente": 50,
                "mpr_demanda_pedido": 5,
                "mpr_cantidad_a_fabricar": 0,
                "mpr_brecha_vs_pendiente": 5,
            },
        ]
        t = aggregate_totals(arts)
        self.assertEqual(t["articulos_con_backorder"], 1)
        self.assertNotIn("total_mpr_brecha_vs_pendiente", t)
        self.assertEqual(t["total_backorder"], 10.0)
        self.assertEqual(t["total_importe_pendiente"], 150.0)


class TestReservaNula(unittest.TestCase):
    def test_stock_reserva_none_tratado_como_cero(self):
        mpr = compute_mpr_pack_fields(50, 40, None)
        self.assertEqual(mpr["mpr_stock_reserva"], 0.0)
        self.assertEqual(mpr["mpr_cantidad_a_fabricar"], 10.0)

    def test_enrich_sin_segundo_argumento(self):
        art = {"pendiente_qty": 1, "stock_terminado": 0}
        enrich_articulo_row(art)
        self.assertEqual(art["mpr_stock_reserva"], 0.0)


class TestVendedorSql(unittest.TestCase):
    def test_incluir_cod_viajante(self):
        sql, params = build_viajante_sql([3, 7], [])
        self.assertIn("cp.CodViajante IN", sql)
        self.assertEqual(params, [3, 7])

    def test_excluir_si_no_hay_incluir(self):
        sql, params = build_viajante_sql([], [9])
        self.assertIn("NOT IN", sql)
        self.assertEqual(params, [9])


class TestBoOriginalSinCambios(unittest.TestCase):
    def test_slug_bo_sigue_en_runner_dedicado(self):
        src = inspect.getsource(QueryRunnerService.run)
        self.assertIn('report.slug == "bo-stock-facturacion"', src)
        self.assertIn("_run_backorder_vs_stock_vs_facturacion", src)
        self.assertNotIn(
            "pedidos-pendientes-produccion",
            inspect.getsource(QueryRunnerService._run_backorder_vs_stock_vs_facturacion),
        )

    def test_bo_no_aplica_clientes_incluir_en_sql(self):
        body = inspect.getsource(QueryRunnerService._run_backorder_vs_stock_vs_facturacion)
        self.assertNotIn("clientes_incluir", body)


class TestTablaEncabezadosUnaLinea(unittest.TestCase):
    def test_js_tabla_ppp_nowrap_y_scroll(self):
        from pathlib import Path

        js = (Path(__file__).resolve().parents[1] / "static" / "reports" / "js" / "pedidos_pendientes_produccion.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("ppp-table-scroll", js)
        self.assertIn("white-space: nowrap", js)
        self.assertIn("#ppp-section .ppp-data-table", js)


class TestSeedSinMetricasGenerico(unittest.TestCase):
    def test_defaults_sin_metrics(self):
        cfg = _report_defaults()["config"]
        self.assertEqual(cfg.get("metrics"), [])

    def test_dashboard_oculta_resumen_generico_ppp(self):
        from pathlib import Path

        js = (Path(__file__).resolve().parents[1] / "static" / "reports" / "js" / "dashboard.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("isPedidosPendientesProduccionSlug(reportSlug)", js)
        idx = js.find("pedidos-pendientes-produccion: KPIs solo en la sección clara")
        self.assertGreater(idx, 0)
        block = js[idx : idx + 400]
        self.assertIn("summaryContainer.classList.add(\"hidden\")", block)


class TestPermisosYSlug(unittest.TestCase):
    def test_slug_consistente(self):
        self.assertEqual(PEDIDOS_PENDIENTES_PRODUCCION_SLUG, SEED_SLUG)

    def test_permiso_mpr_o_operativo(self):
        user = MagicMock()
        user.is_authenticated = True
        user.is_superuser = False
        user.tiene_permiso = lambda code: code == "mpr.reportes"
        self.assertTrue(user_can_access_pedidos_pendientes_produccion(user))

    def test_pv_visible_en_slug(self):
        self.assertIn(PEDIDOS_PENDIENTES_PRODUCCION_SLUG, SLUGS_VENTAS_CON_PUNTO_VENTA)

    def test_runner_registrado_sin_mysql(self):
        from reports.models import ReportDefinition

        report = ReportDefinition(slug=PEDIDOS_PENDIENTES_PRODUCCION_SLUG, name="T", category="operational")
        user = MagicMock(base_empresa=None)
        svc = QueryRunnerService(user)
        with patch.object(
            QueryRunnerService,
            "_resolve_period_dates",
            return_value=(None, None),
        ):
            result = svc.run(report, {"filters": {}})
        self.assertTrue(any("fecha" in n.lower() for n in result.notes))


if __name__ == "__main__":
    unittest.main()
