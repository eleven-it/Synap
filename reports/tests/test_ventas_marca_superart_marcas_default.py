# -*- coding: utf-8 -*-
"""ventas-marca-superart: resumen por marca arriba + marcas expandidas por defecto."""
from pathlib import Path

from django.test import SimpleTestCase

from reports.services.ventas_marca_superart_runner import (
    _nest_marca_superart_articulo,
    _resumen_por_marca,
)

BASE = Path(__file__).resolve().parents[1]
ROWS = [
    {"codigo_marca": 1, "nombre_marca": "ALFA", "id_manual": "100", "id_art": 1, "nombre_articulo": "A1", "packs": 10, "docenas": 1, "facturacion": 100},
    {"codigo_marca": 1, "nombre_marca": "ALFA", "id_manual": "101", "id_art": 2, "nombre_articulo": "A2", "packs": 5, "docenas": 0.5, "facturacion": 50},
    {"codigo_marca": 2, "nombre_marca": "BETA", "id_manual": "200", "id_art": 3, "nombre_articulo": "B1", "packs": 24, "docenas": 2, "facturacion": 300},
]


class TestResumenMarcas(SimpleTestCase):
    def test_todas_las_marcas_con_totales(self):
        res = _resumen_por_marca(_nest_marca_superart_articulo(ROWS))
        by = {r["nombre_marca"]: r for r in res}
        self.assertEqual(set(by), {"ALFA", "BETA"})
        self.assertEqual(by["ALFA"]["facturacion"], 150)
        self.assertEqual(by["ALFA"]["superarts"], 2)
        self.assertEqual(by["BETA"]["packs"], 24)
        self.assertNotIn("children", by["ALFA"])

    def test_vacio(self):
        self.assertEqual(_resumen_por_marca([]), [])

    def test_runner_expone_marcas_resumen(self):
        src = (BASE / "services/ventas_marca_superart_runner.py").read_text()
        self.assertIn('"marcas_resumen": _resumen_por_marca(arbol)', src)


class TestFrontend(SimpleTestCase):
    def test_js_expandido_por_defecto_y_resumen(self):
        js = (BASE / "static/reports/js/ventas_marca_superart.js").read_text()
        self.assertIn('!== false', js)
        self.assertIn("renderMarcasResumen", js)
        self.assertIn("Totales por marca", js)

    def test_template_contenedor_y_version(self):
        html = (BASE / "templates/reports/dashboard_detail.html").read_text()
        self.assertIn('id="vmsa-marcas-resumen"', html)
        self.assertIn("ventas_marca_superart.js' %}?v=20261102a", html)
