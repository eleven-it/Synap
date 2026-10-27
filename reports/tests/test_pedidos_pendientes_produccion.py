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
    compute_reserva_reposicion,
    compute_stock_produccion_armable,
    enrich_articulo_row,
    es_tipo_art_fab_fabricado,
    formula_cantidad_por_unidad_terminado,
    sql_unidad_base_join,
    sql_unidad_base_select,
)
import reports.services.pedidos_pendientes_produccion_runner as ppp_runner_mod
from reports.services.pedidos_pendientes_produccion_armable import (
    fetch_stock_produccion_armable_map,
)
from reports.services.pedidos_pendientes_produccion_seed import (
    PEDIDOS_PENDIENTES_PRODUCCION_SLUG as SEED_SLUG,
    _report_defaults,
)
from reports.services.query_runner import QueryRunnerService
from reports.views import SLUGS_VENTAS_CON_PUNTO_VENTA


class TestStockProduccionArmable(unittest.TestCase):
    def test_sin_lineas_cero(self):
        self.assertEqual(compute_stock_produccion_armable([]), 0.0)

    def test_un_componente_cantidad_dos_saldo_cien(self):
        self.assertEqual(compute_stock_produccion_armable([(100.0, 2.0)]), 50.0)

    def test_varios_componentes_toma_minimo(self):
        lineas = [(100.0, 2.0), (30.0, 1.0), (200.0, 5.0)]
        self.assertEqual(compute_stock_produccion_armable(lineas), 30.0)

    def test_floor_hacia_abajo(self):
        self.assertEqual(compute_stock_produccion_armable([(99.0, 2.0)]), 49.0)

    def test_caso_verificacion_709_447(self):
        """Fórmula 371: componente 1641 qty 1, 278 en semi → 278 armables."""
        self.assertEqual(
            compute_stock_produccion_armable([(278.0, formula_cantidad_por_unidad_terminado(1, "Unidad"))]),
            278.0,
        )

    def test_es_fabricado_case_insensitive(self):
        self.assertTrue(es_tipo_art_fab_fabricado("Fabricado"))
        self.assertTrue(es_tipo_art_fab_fabricado("fabricado"))
        self.assertFalse(es_tipo_art_fab_fabricado("Terminado"))
        self.assertFalse(es_tipo_art_fab_fabricado(""))

    def test_runner_usa_armable_no_deposito_produccion(self):
        src = inspect.getsource(ppp_runner_mod)
        self.assertIn("fetch_stock_produccion_armable_map", src)
        self.assertNotIn("set_produccion", src)


class TestFetchStockProduccionArmableBulk(unittest.TestCase):
    @patch("reports.services.pedidos_pendientes_produccion_armable.get_deposito_semi_elaborado_mpr", return_value=3)
    def test_sin_receta_cero(self, _mock_dep):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [],  # articulo ensamblado
        ]
        out = fetch_stock_produccion_armable_map(cursor, "emp", [447])
        self.assertEqual(out[447], 0.0)

    @patch("reports.services.pedidos_pendientes_produccion_armable.get_deposito_semi_elaborado_mpr", return_value=3)
    def test_ignora_componentes_no_fabricados(self, _mock_dep):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [(100, 371)],
            [
                (371, 2001, 1, "Unidad", None, None, "Materia Prima"),
                (371, 2002, 1, "Unidad", None, None, "Fabricado"),
            ],
            [(2002, 40.0)],
        ]
        out = fetch_stock_produccion_armable_map(cursor, "emp", [100])
        self.assertEqual(out[100], 40.0)

    @patch("reports.services.pedidos_pendientes_produccion_armable.get_deposito_semi_elaborado_mpr", return_value=None)
    def test_sin_deposito_semi_todo_cero(self, _mock_dep):
        cursor = MagicMock()
        out = fetch_stock_produccion_armable_map(cursor, "emp", [1, 2])
        self.assertEqual(out, {1: 0.0, 2: 0.0})
        cursor.execute.assert_not_called()


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


class TestReservaReposicion(unittest.TestCase):
    def test_objetivo_es_stock_reserva(self):
        obj, disp, rep = compute_reserva_reposicion(10, 100, 25)
        self.assertEqual(obj, 25.0)
        self.assertEqual(disp, 25.0)
        self.assertEqual(rep, 0.0)


class TestInvarianteFabricar(unittest.TestCase):
    """A fabricar = backorder + reposición = max(0, P + R − terminado)."""

    def _assert_invariante(self, p: float, t: float, r: float):
        _, backorder = compute_disponible_backorder(p, t)
        mpr = compute_mpr_pack_fields(p, t, r)
        mpr.pop("_backorder_check", None)
        esperado = round(max(0.0, p + r - t), 4)
        self.assertEqual(mpr["mpr_cantidad_a_fabricar"], esperado)
        self.assertAlmostEqual(
            mpr["mpr_cantidad_a_fabricar"],
            round(backorder + mpr["reposicion_reserva"], 4),
        )

    def test_terminado_menor_pendiente(self):
        self._assert_invariante(100, 40, 20)

    def test_terminado_entre_pendiente_y_pendiente_mas_reserva(self):
        self._assert_invariante(100, 110, 30)

    def test_terminado_mayor_pendiente_mas_reserva(self):
        self._assert_invariante(50, 200, 10)

    def test_reserva_cero(self):
        self._assert_invariante(80, 30, 0)


class TestMprPackFields(unittest.TestCase):
    def test_a_fabricar_cero_con_stock_cubre(self):
        mpr = compute_mpr_pack_fields(100, 150, 10)
        self.assertEqual(mpr["mpr_demanda_pedido"], 100.0)
        self.assertEqual(mpr["mpr_cantidad_a_fabricar"], 0.0)
        self.assertEqual(mpr["reserva_objetivo"], 10.0)
        self.assertEqual(mpr["reserva_disponible"], 10.0)
        self.assertEqual(mpr["reposicion_reserva"], 0.0)

    def test_solo_backorder_sin_reserva(self):
        mpr = compute_mpr_pack_fields(100, 5, 0)
        self.assertEqual(mpr["mpr_cantidad_a_fabricar"], 95.0)
        self.assertEqual(mpr["reposicion_reserva"], 0.0)

    def test_enrich_articulo_row(self):
        art = {"pendiente_qty": 120, "stock_terminado": 0, "stock_produccion": 84}
        enrich_articulo_row(art, 0)
        self.assertEqual(art["backorder"], 120.0)
        self.assertEqual(art["mpr_cantidad_a_fabricar"], 120.0)
        self.assertIn("reserva_objetivo", art)


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

    def test_consignacion_suma_a_terminado(self):
        deps = [
            {"CodDeposito": 10, "tipo_mpr": "Terminado", "suma_stock": "Si", "anulado": "No"},
            {"CodDeposito": 11, "tipo_mpr": "Consignación", "suma_stock": "Si", "anulado": "No"},
        ]
        term, prod = classify_depositos_stock_columns(deps)
        self.assertEqual(sorted(term), [10, 11])
        self.assertEqual(prod, [])


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
    def test_totales_reserva_y_sin_brecha(self):
        arts = [
            {
                "pendiente_qty": 10,
                "stock_terminado": 0,
                "stock_produccion": 0,
                "disponible": 0,
                "backorder": 10,
                "importe_pendiente": 100,
                "mpr_demanda_pedido": 10,
                "reserva_objetivo": 5,
                "reserva_disponible": 0,
                "reposicion_reserva": 5,
                "mpr_cantidad_a_fabricar": 15,
            },
            {
                "pendiente_qty": 5,
                "stock_terminado": 100,
                "stock_produccion": 0,
                "disponible": 95,
                "backorder": 0,
                "importe_pendiente": 50,
                "mpr_demanda_pedido": 5,
                "reserva_objetivo": 8,
                "reserva_disponible": 8,
                "reposicion_reserva": 0,
                "mpr_cantidad_a_fabricar": 0,
            },
        ]
        t = aggregate_totals(arts)
        self.assertEqual(t["articulos_con_backorder"], 1)
        self.assertNotIn("total_mpr_brecha_vs_pendiente", t)
        self.assertEqual(t["total_backorder"], 10.0)
        self.assertEqual(t["total_reserva_objetivo"], 13.0)
        self.assertEqual(t["total_reposicion_reserva"], 5.0)
        self.assertEqual(t["total_mpr_cantidad_a_fabricar"], 15.0)
        self.assertEqual(t["total_importe_pendiente"], 150.0)


class TestReservaNula(unittest.TestCase):
    def test_stock_reserva_none_tratado_como_cero(self):
        mpr = compute_mpr_pack_fields(50, 40, None)
        self.assertEqual(mpr["reserva_objetivo"], 0.0)
        self.assertEqual(mpr["mpr_cantidad_a_fabricar"], 10.0)

    def test_enrich_sin_segundo_argumento(self):
        art = {"pendiente_qty": 1, "stock_terminado": 0}
        enrich_articulo_row(art)
        self.assertEqual(art["reserva_objetivo"], 0.0)


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
    def test_js_tabla_ppp_scroll_wrapper(self):
        from pathlib import Path

        js = (Path(__file__).resolve().parents[1] / "static" / "reports" / "js" / "pedidos_pendientes_produccion.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("ppp-table-scroll", js)
        self.assertIn("ppp-sort-th", js)
        self.assertIn("Reserva objetivo", js)
        self.assertNotIn("Brecha", js)
        self.assertNotIn("mpr_brecha", js)

    def test_css_tabla_nowrap_y_scroll_contenido(self):
        from pathlib import Path

        css = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "reports"
            / "css"
            / "pedidos_pendientes_produccion_layout.css"
        ).read_text(encoding="utf-8")
        self.assertIn("overflow-x: auto", css)
        self.assertIn("white-space: nowrap", css)
        self.assertIn("#ppp-report-dashboard .ppp-data-table", css)
        self.assertIn("position: sticky", css)
        self.assertIn("max-height: calc(100vh - 220px)", css)


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
