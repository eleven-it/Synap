# -*- coding: utf-8 -*-
"""Tests del módulo SQL stock-existencias (sin MySQL)."""

import unittest

from reports.services.stock_existencias_query import (
    DEFAULT_PAGE_SIZE,
    FULL_FETCH_THRESHOLD,
    normalize_row,
    parse_stock_existencias_filters,
    _order_by_sql,
    _search_where_sql,
)
from reports.services.stock_existencias_query import StockExistenciasFilters


class TestParseStockExistenciasFilters(unittest.TestCase):
    def test_defaults(self):
        f = parse_stock_existencias_filters({})
        self.assertFalse(f.incluir_stock_cero)
        self.assertEqual(f.limit, DEFAULT_PAGE_SIZE)
        self.assertEqual(f.offset, 0)
        self.assertEqual(f.sort_col, "nombre")
        self.assertEqual(f.sort_dir, "asc")

    def test_agrupacion_fuerza_fetch_completo(self):
        f = parse_stock_existencias_filters({"agrupacion_activa": "si"}, payload_limit=150)
        self.assertTrue(f.agrupacion_activa)
        self.assertGreaterEqual(f.limit, FULL_FETCH_THRESHOLD)
        self.assertEqual(f.offset, 0)

    def test_busqueda_y_orden(self):
        f = parse_stock_existencias_filters(
            {"busqueda": "tornillo", "sort_col": "rubro_nombre", "sort_dir": "desc"},
            payload_limit=50,
            payload_offset=100,
        )
        self.assertEqual(f.busqueda, "tornillo")
        self.assertEqual(f.sort_col, "rubro_nombre")
        self.assertEqual(f.sort_dir, "desc")
        self.assertEqual(f.limit, 50)
        self.assertEqual(f.offset, 100)

    def test_sort_col_invalido_vuelve_a_nombre(self):
        f = parse_stock_existencias_filters({"sort_col": "DROP TABLE"})
        self.assertEqual(f.sort_col, "nombre")


class TestStockExistenciasSqlHelpers(unittest.TestCase):
    def test_search_minimo_dos_caracteres(self):
        sql, params = _search_where_sql("a")
        self.assertEqual(sql, "")
        self.assertEqual(params, [])

    def test_search_con_termino(self):
        sql, params = _search_where_sql("abc")
        self.assertIn("LIKE", sql)
        self.assertEqual(len(params), 7)

    def test_order_by_nombre(self):
        f = StockExistenciasFilters(sort_col="nombre", sort_dir="asc")
        self.assertIn("NombreArticulo", _order_by_sql(f))

    def test_normalize_codigo_barras_str(self):
        row = normalize_row(["codigo_barras", "stock"], ("013005", 1.5))
        self.assertEqual(row["codigo_barras"], "013005")
        self.assertEqual(row["stock"], 1.5)


class TestStockExistenciasRunnerContract(unittest.TestCase):
    def test_metodo_runner_definido(self):
        from reports.services.query_runner import QueryRunnerService

        self.assertTrue(hasattr(QueryRunnerService, "_run_stock_existencias"))
