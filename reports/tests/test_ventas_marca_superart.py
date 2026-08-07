# -*- coding: utf-8 -*-
"""Tests informe ventas-marca-superart (árbol y export)."""
from unittest.mock import Mock

from django.test import SimpleTestCase

from reports.models import ReportDefinition
from reports.services.export_service import ExportService
from reports.services.ventas_marca_superart_runner import (
    _display_marca,
    _display_superart,
    _flatten_filas_marca_superart,
    _nest_marca_superart_articulo,
    _sort_arbol_marca_superart,
)


class VentasMarcaSuperartNestTests(SimpleTestCase):
    def test_sin_marca_display(self):
        cod, nom = _display_marca(0, "")
        self.assertEqual(cod, 0)
        self.assertEqual(nom, "Sin marca")

    def test_sin_superart_display(self):
        manual, nom = _display_superart("")
        self.assertEqual(manual, "")
        self.assertEqual(nom, "Sin SuperArt")

    def test_nest_marca_superart_articulo_rollups(self):
        filas = [
            {
                "codigo_marca": 1,
                "nombre_marca": "Marca A",
                "id_manual": "SA1",
                "id_art": 10,
                "nombre_articulo": "Art A",
                "packs": 12.0,
                "docenas": 1.0,
                "facturacion": 100.0,
            },
            {
                "codigo_marca": 1,
                "nombre_marca": "Marca A",
                "id_manual": "SA1",
                "id_art": 20,
                "nombre_articulo": "Art B",
                "packs": 6.0,
                "docenas": 1.0,
                "facturacion": 50.0,
            },
            {
                "codigo_marca": 1,
                "nombre_marca": "Marca A",
                "id_manual": "SA2",
                "id_art": 30,
                "nombre_articulo": "Art C",
                "packs": 2.0,
                "docenas": 2.0,
                "facturacion": 25.0,
            },
        ]
        arbol = _nest_marca_superart_articulo(filas)
        self.assertEqual(len(arbol), 1)
        marca = arbol[0]
        self.assertEqual(marca["tipo"], "marca")
        self.assertEqual(marca["packs"], 20.0)
        self.assertEqual(marca["docenas"], 4.0)
        self.assertEqual(marca["facturacion"], 175.0)
        self.assertEqual(len(marca["children"]), 2)
        sa1 = next(c for c in marca["children"] if c["id_manual"] == "SA1")
        self.assertEqual(sa1["packs"], 18.0)
        self.assertEqual(len(sa1["children"]), 2)

    def test_nest_fallbacks_sin_marca_sin_superart(self):
        filas = [
            {
                "codigo_marca": 0,
                "nombre_marca": "",
                "id_manual": "",
                "id_art": 1,
                "nombre_articulo": "X",
                "packs": 1.0,
                "docenas": 1.0,
                "facturacion": 10.0,
            }
        ]
        arbol = _nest_marca_superart_articulo(filas)
        self.assertEqual(arbol[0]["nombre_marca"], "Sin marca")
        self.assertEqual(arbol[0]["children"][0]["nombre_superart"], "Sin SuperArt")

    def test_flatten_filas(self):
        arbol = [
            {
                "tipo": "marca",
                "codigo_marca": 1,
                "nombre_marca": "M",
                "children": [
                    {
                        "tipo": "superart",
                        "id_manual": "SA",
                        "nombre_superart": "SA",
                        "children": [
                            {
                                "tipo": "articulo",
                                "id_art": 9,
                                "nombre_articulo": "Art",
                                "packs": 2.0,
                                "docenas": 0.5,
                                "facturacion": 10.0,
                            }
                        ],
                    }
                ],
            }
        ]
        flat = _flatten_filas_marca_superart(arbol)
        self.assertEqual(len(flat), 1)
        self.assertEqual(flat[0]["nombre_marca"], "M")
        self.assertEqual(flat[0]["nombre_superart"], "SA")
        self.assertEqual(flat[0]["nombre_articulo"], "Art")
        self.assertEqual(flat[0]["packs"], 2.0)

    def test_sort_arbol_por_facturacion_desc(self):
        arbol = [
            {
                "tipo": "marca",
                "codigo_marca": 1,
                "nombre_marca": "A",
                "facturacion": 10.0,
                "packs": 1.0,
                "docenas": 1.0,
                "children": [
                    {
                        "tipo": "superart",
                        "id_manual": "S",
                        "nombre_superart": "S",
                        "facturacion": 10.0,
                        "packs": 1.0,
                        "docenas": 1.0,
                        "children": [
                            {
                                "tipo": "articulo",
                                "id_art": 1,
                                "nombre_articulo": "Bajo",
                                "facturacion": 1.0,
                                "packs": 1.0,
                                "docenas": 1.0,
                            },
                            {
                                "tipo": "articulo",
                                "id_art": 2,
                                "nombre_articulo": "Alto",
                                "facturacion": 9.0,
                                "packs": 1.0,
                                "docenas": 1.0,
                            },
                        ],
                    }
                ],
            }
        ]
        sorted_arbol = _sort_arbol_marca_superart(arbol, "facturacion", "desc")
        arts = sorted_arbol[0]["children"][0]["children"]
        self.assertEqual(arts[0]["nombre_articulo"], "Alto")
        self.assertEqual(arts[1]["nombre_articulo"], "Bajo")


class VentasMarcaSuperartExportTests(SimpleTestCase):
    def test_export_headers(self):
        r = ReportDefinition(slug="ventas-marca-superart", config={})
        row = {
            "codigo_marca": 1,
            "nombre_marca": "Marca",
            "id_manual": "SA",
            "nombre_superart": "SA",
            "id_art": 10,
            "nombre_articulo": "Art",
            "packs": 3.0,
            "docenas": 0.25,
            "facturacion": 99.0,
        }
        svc = ExportService(Mock())
        h = svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "nombre_marca",
                "nombre_superart",
                "nombre_articulo",
                "packs",
                "docenas",
                "facturacion",
            ],
        )

    def test_export_filename(self):
        svc = ExportService(Mock())
        name = svc._resolve_export_filename(
            "ventas-marca-superart",
            {"filters": {"fecha_inicio_facturacion": "2026-01-01", "fecha_fin_facturacion": "2026-01-31"}},
            "20260101",
        )
        self.assertEqual(name, "Ventas_marca_superart_2026-01-01_2026-01-31.xlsx")
