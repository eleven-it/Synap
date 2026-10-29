# -*- coding: utf-8 -*-
"""Agrupación anidada (Cliente/Marca/Artículo) en pedidos-pendientes-produccion."""
import inspect
import unittest
from pathlib import Path

from reports.services import pedidos_pendientes_produccion_runner as ppp_runner_mod
from reports.services.pedidos_pendientes_produccion_calcs import attach_clientes_detalle

BASE = Path(__file__).resolve().parents[1]
JS_DIR = BASE / "static" / "reports" / "js"
TEMPLATE = BASE / "templates" / "reports" / "dashboard_detail.html"


class TestAttachClientesDetalle(unittest.TestCase):
    def test_desglose_y_nombre_cliente(self):
        arts = [{"id_art": 1}, {"id_art": 2}, {"id_art": 3}]
        rows = [
            (1, 10, "Alfa", 2, 100.0),
            (1, 11, "Beta", 5, 250.555),
            (2, 12, "", 1, 10),
        ]
        attach_clientes_detalle(arts, rows)
        self.assertEqual([d["cliente"] for d in arts[0]["clientes_detalle"]], ["Beta", "Alfa"])
        self.assertEqual(arts[0]["cliente"], "Beta, Alfa")
        self.assertEqual(arts[0]["clientes_detalle"][0]["importe_pendiente"], 250.56)
        self.assertEqual(arts[1]["cliente"], "Cliente 12")
        self.assertEqual(arts[2]["clientes_detalle"], [])
        self.assertEqual(arts[2]["cliente"], "")

    def test_runner_desglosa_por_cliente(self):
        src = inspect.getsource(ppp_runner_mod)
        self.assertIn("GROUP BY sp.IDArt, cp.Codigo", src)
        self.assertIn("LEFT JOIN cliente cli ON cli.Codigo = cp.Codigo", src)
        self.assertIn("attach_clientes_detalle", src)


class TestFrontAgrupacionCompartida(unittest.TestCase):
    def test_modulo_compartido_expone_api(self):
        js = (JS_DIR / "reports_nested_grouping.js").read_text(encoding="utf-8")
        for name in (
            "initializeGroupByUI",
            "groupTableDataGeneric",
            "renderGroupedTableRows",
            "attachGroupToggleListeners",
            "filterBySearch",
            "getGroupByFieldsInSelectionOrder",
        ):
            self.assertIn(name + ":", js)

    def test_bo_y_ppp_usan_modulo_compartido(self):
        bo = (JS_DIR / "bo_stock_facturacion.js").read_text(encoding="utf-8")
        ppp = (JS_DIR / "pedidos_pendientes_produccion.js").read_text(encoding="utf-8")
        self.assertIn("window.ReportsNestedGrouping", bo)
        self.assertNotIn("function initializeBoGroupByUI", bo)
        self.assertIn("window.ReportsNestedGrouping", ppp)
        for key in ('"cliente"', '"marca"', '"articulo"'):
            self.assertIn("key: " + key, ppp)

    def test_template_toolbar_y_orden_scripts(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('id="ppp-group-by"', html)
        self.assertIn('id="ppp-group-by_search"', html)
        self.assertIn('id="ppp-search-slot"', html)
        idx_shared = html.index("reports/js/reports_nested_grouping.js")
        self.assertLess(idx_shared, html.index("reports/js/bo_stock_facturacion.js"))
        self.assertLess(
            html.rindex("reports/js/reports_nested_grouping.js"),
            html.index("reports/js/pedidos_pendientes_produccion.js"),
        )
