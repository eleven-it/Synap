# -*- coding: utf-8 -*-
"""Tests informe ventas-por-articulo (árbol y export)."""
from unittest.mock import Mock

from django.test import SimpleTestCase

from reports.models import ReportDefinition
from reports.services.export_service import ExportService
from reports.services.ventas_objetivos_bo_runner import (
    _flatten_filas_ventas_por_articulo,
    _nest_articulo_proveedor_cliente,
    _nombre_proveedor_display,
)


class VentasPorArticuloNestTests(SimpleTestCase):
    def test_sin_proveedor_display(self):
        self.assertEqual(_nombre_proveedor_display(0, ""), "Sin proveedor")

    def test_nest_articulo_proveedor_cliente_rollups(self):
        filas = [
            {
                "id_art": 10,
                "nombre_articulo": "Art A",
                "codigo_proveedor": 5,
                "nombre_proveedor": "Prov X",
                "codigo_cliente": 100,
                "nombre_cliente": "Cliente Uno",
                "facturacion": 100.0,
                "cantidades_vendidas": 2.0,
            },
            {
                "id_art": 10,
                "nombre_articulo": "Art A",
                "codigo_proveedor": 5,
                "nombre_proveedor": "Prov X",
                "codigo_cliente": 200,
                "nombre_cliente": "Cliente Dos",
                "facturacion": 50.0,
                "cantidades_vendidas": 1.0,
            },
        ]
        arbol = _nest_articulo_proveedor_cliente(filas)
        self.assertEqual(len(arbol), 1)
        art = arbol[0]
        self.assertEqual(art["facturacion"], 150.0)
        self.assertEqual(art["cantidades_vendidas"], 3.0)
        self.assertEqual(len(art["children"]), 1)
        prov = art["children"][0]
        self.assertEqual(prov["nombre_proveedor"], "Prov X")
        self.assertEqual(len(prov["children"]), 2)

    def test_flatten_filas(self):
        arbol = [
            {
                "tipo": "articulo",
                "id_art": 1,
                "nombre_articulo": "Z",
                "children": [
                    {
                        "tipo": "proveedor",
                        "codigo_proveedor": 0,
                        "nombre_proveedor": "Sin proveedor",
                        "children": [
                            {
                                "tipo": "cliente",
                                "codigo_cliente": 9,
                                "nombre_cliente": "C",
                                "facturacion": 10.0,
                                "cantidades_vendidas": 1.0,
                            }
                        ],
                    }
                ],
            }
        ]
        flat = _flatten_filas_ventas_por_articulo(arbol)
        self.assertEqual(len(flat), 1)
        self.assertEqual(flat[0]["nombre_proveedor"], "Sin proveedor")


class VentasPorArticuloExportTests(SimpleTestCase):
    def test_export_headers(self):
        r = ReportDefinition(slug="ventas-por-articulo", config={})
        row = {
            "id_art": 1,
            "nombre_articulo": "Art",
            "codigo_proveedor": 0,
            "nombre_proveedor": "Sin proveedor",
            "codigo_cliente": 10,
            "nombre_cliente": "Cli",
            "cantidades_vendidas": 3.0,
            "facturacion": 99.0,
        }
        svc = ExportService(Mock())
        h = svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "id_art",
                "nombre_articulo",
                "codigo_proveedor",
                "nombre_proveedor",
                "codigo_cliente",
                "nombre_cliente",
                "cantidades_vendidas",
                "facturacion",
            ],
        )
