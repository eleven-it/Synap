# -*- coding: utf-8 -*-
"""Tests servicio inventario tabla MPR."""
from django.test import SimpleTestCase

from stock.services.inventario_tabla import (
    InventarioTablaFiltros,
    build_inventario_query_string,
    codigo_compuesto_articulo,
    parse_inventario_filtros,
    parse_presentacion,
)


class CodigoCompuestoTest(SimpleTestCase):
    def test_manual_y_prov(self):
        self.assertEqual(codigo_compuesto_articulo("12A", "PRV-88"), "12A - PRV-88")

    def test_solo_manual(self):
        self.assertEqual(codigo_compuesto_articulo("12A", ""), "12A")
        self.assertEqual(codigo_compuesto_articulo("12A", None), "12A")


class ParseFiltrosTest(SimpleTestCase):
    def test_default(self):
        f = parse_inventario_filtros({})
        self.assertFalse(f.incluir_ceros)
        self.assertEqual(f.presentacion, "unidades")
        self.assertEqual(f.page, 1)

    def test_marcas_multi(self):
        class Q:
            def get(self, k, d=None):
                return d

            def getlist(self, k):
                return ["3", "7"]

        f = parse_inventario_filtros(Q(), marcas_getlist=["3", "7"])
        self.assertEqual(f.marcas_incluidos, [3, 7])

    def test_incluir_ceros(self):
        f = parse_inventario_filtros({"incluir_ceros": "1"})
        self.assertTrue(f.incluir_ceros)


class QueryStringTest(SimpleTestCase):
    def test_paginacion_y_marcas(self):
        f = InventarioTablaFiltros(marcas_incluidos=[3], incluir_ceros=True, page=2)
        qs = build_inventario_query_string(f, page=3)
        self.assertIn("marcas_incluidos=3", qs)
        self.assertIn("incluir_ceros=1", qs)
        self.assertIn("page=3", qs)


class ParsePresentacionTest(SimpleTestCase):
    def test_docenas(self):
        self.assertEqual(parse_presentacion("docenas"), "docenas")

    def test_invalido(self):
        self.assertEqual(parse_presentacion("x"), "unidades")
