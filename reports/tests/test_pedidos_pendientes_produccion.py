# -*- coding: utf-8 -*-
"""Tests informe pedidos-pendientes-produccion (sin MySQL)."""
import inspect
import unittest
from unittest.mock import MagicMock, patch

from reports.permissions import (
    PEDIDOS_PENDIENTES_PRODUCCION_SLUG,
    user_can_access_pedidos_pendientes_produccion,
)
from reports.services.pedidos_pendientes_produccion_runner import (
    CRITERIO_BACKORDER,
    classify_depositos_columns,
    criterio_estados_sql,
    merge_mpr_into_articulos,
    qty_expression_for_criterio,
    resolve_criterio_pendiente,
)
from reports.services.pedidos_pendientes_produccion_seed import (
    PEDIDOS_PENDIENTES_PRODUCCION_SLUG as SEED_SLUG,
)
from reports.services.query_runner import QueryRunnerService


class TestCriterioPendiente(unittest.TestCase):
    def test_default_backorder(self):
        self.assertEqual(resolve_criterio_pendiente(None), CRITERIO_BACKORDER)
        self.assertEqual(resolve_criterio_pendiente("invalid"), CRITERIO_BACKORDER)

    def test_estados_backorder(self):
        sql, _ = criterio_estados_sql(CRITERIO_BACKORDER)
        self.assertIn("Pendiente", sql)
        self.assertNotIn("Parcial", sql)

    def test_qty_backorder_usa_cantidad(self):
        self.assertIn("Cantidad", qty_expression_for_criterio(CRITERIO_BACKORDER))

    def test_qty_saldo_usa_pendiente(self):
        expr = qty_expression_for_criterio("en_preparacion")
        self.assertIn("cantidad_pendiente", expr)


class TestClasificacionDepositos(unittest.TestCase):
    def test_clasifica_terminado_produccion_y_otros(self):
        deps = [
            {"CodDeposito": 1, "NombreDeposito": "Term", "tipo_mpr": "Terminado", "suma_stock": "Si"},
            {"CodDeposito": 2, "NombreDeposito": "Fab", "tipo_mpr": "Produccion", "suma_stock": "Si"},
            {"CodDeposito": 3, "NombreDeposito": "Semi", "tipo_mpr": "SemiElaborado", "suma_stock": "Si"},
            {"CodDeposito": 4, "NombreDeposito": "No suma", "tipo_mpr": "", "suma_stock": "No"},
        ]
        term, prod, otros = classify_depositos_columns(deps)
        self.assertEqual(term, [1])
        self.assertEqual(prod, [2])
        self.assertEqual(len(otros), 1)
        self.assertEqual(otros[0]["id_deposito"], 3)


class TestMergeMpr(unittest.TestCase):
    def test_merge_calcula_brecha(self):
        arts = [{"id_art": 10, "pendiente_qty": 100.0}]
        mpr = [
            {
                "id_articulo": 10,
                "cantidad_pedida_pedido": 80,
                "stock_terminado": 5,
                "stock_reserva": 0,
                "cantidad_a_fabricar": 75,
            }
        ]
        merge_mpr_into_articulos(arts, mpr)
        self.assertEqual(arts[0]["mpr_cantidad_a_fabricar"], 75.0)
        self.assertEqual(arts[0]["mpr_brecha_vs_pendiente"], 25.0)


class TestBoOriginalSinCambios(unittest.TestCase):
    def test_slug_bo_sigue_en_runner_dedicado(self):
        src = inspect.getsource(QueryRunnerService.run)
        self.assertIn('report.slug == "bo-stock-facturacion"', src)
        self.assertIn("_run_backorder_vs_stock_vs_facturacion", src)
        self.assertNotIn("pedidos-pendientes-produccion", inspect.getsource(
            QueryRunnerService._run_backorder_vs_stock_vs_facturacion
        ))

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

    def test_runner_registrado_en_query_runner(self):
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
