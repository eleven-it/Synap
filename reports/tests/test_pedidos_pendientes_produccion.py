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
    build_viajante_sql,
    classify_depositos_stock_columns,
    compute_disponible_backorder,
    compute_mpr_pack_fields,
    enrich_articulo_row,
)
from reports.services.pedidos_pendientes_produccion_seed import (
    PEDIDOS_PENDIENTES_PRODUCCION_SLUG as SEED_SLUG,
)
from reports.services.query_runner import QueryRunnerService
from reports.views import SLUGS_VENTAS_CON_PUNTO_VENTA


class TestDisponibleBackorder(unittest.TestCase):
    def test_referencia_1478(self):
        d, b = compute_disponible_backorder(1500, 628)
        self.assertEqual(d, -872.0)
        self.assertEqual(b, 872.0)

    def test_referencia_262(self):
        d, b = compute_disponible_backorder(12, 1483)
        self.assertEqual(d, 1471.0)
        self.assertEqual(b, 0.0)

    def test_referencia_444(self):
        d, b = compute_disponible_backorder(120, 0)
        self.assertEqual(d, -120.0)
        self.assertEqual(b, 120.0)


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
