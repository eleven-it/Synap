# -*- coding: utf-8 -*-
"""fabricados-superart: por defecto todas las marcas/superarts + resumen por marca."""
from pathlib import Path
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from mpr.reportes_presentacion import preparar_fabricados_superart_presentacion
from mpr.reportes_transicion_lote_sql import fetch_fabricado_primera_por_articulo_mes
from mpr.services_fabricados_superart import agrupar_fabricados_por_superart
from reports.services.fabricados_superart_calcs import parse_filters_from_payload

ROWS = [
    {"id_articulo": 1, "id_manual": "100-01", "codigo_marca": 7, "ym": "2026-10", "cantidad": 24},
    {"id_articulo": 2, "id_manual": "200-01", "codigo_marca": 8, "ym": "2026-10", "cantidad": 12},
    {"id_articulo": 3, "id_manual": "200-02", "codigo_marca": 8, "ym": "2026-10", "cantidad": 36},
    {"id_articulo": 4, "id_manual": "300-01", "codigo_marca": None, "ym": "2026-10", "cantidad": 6},
]


class TestDefaultTodas(SimpleTestCase):
    def test_sin_filtros_no_restringe(self):
        f = parse_filters_from_payload({"desde": "2026-10-01", "hasta": "2026-10-31"})
        self.assertEqual(f["marcas_incluidos"], [])
        self.assertEqual(f["superarts_incluidos"], [])

    def test_resumen_todas_las_marcas_ordenado(self):
        out = agrupar_fabricados_por_superart(ROWS, ["2026-10"], {}, marcas_nombres={7: "ALFA", 8: "BETA"})
        marcas = out["filas_marca"]
        self.assertEqual([m["nombre_marca"] for m in marcas], ["BETA", "ALFA", "Sin marca"])
        self.assertEqual(marcas[0]["total"], 48)
        self.assertEqual(sum(m["total"] for m in marcas), out["total_general"])
        self.assertEqual(out["kpis"]["marcas_con_produccion"], 3)
        self.assertEqual(len(out["filas_superart"]), 4)

    def test_resumen_respeta_filtro_superart(self):
        out = agrupar_fabricados_por_superart(ROWS, ["2026-10"], {}, superarts_incluidos=["100"])
        self.assertEqual([m["codigo_marca"] for m in out["filas_marca"]], [7])
        self.assertEqual(out["filas_marca"][0]["nombre_marca"], "Marca 7")

    def test_presentacion_display_marcas(self):
        out = agrupar_fabricados_por_superart(ROWS, ["2026-10"], {})
        ctx = preparar_fabricados_superart_presentacion(out, "docenas")
        self.assertTrue(ctx["filas_marca"][0]["total_display"])
        self.assertEqual(len(ctx["filas_marca"][0]["columnas_mes"]), 1)

    def test_sql_incluye_marca_sin_filtro(self):
        cur = MagicMock()
        cur.fetchall.return_value = []
        fetch_fabricado_primera_por_articulo_mes(cur, ["2026-10"])
        sql = cur.execute.call_args[0][0]
        self.assertIn("a.CodigoMarca AS codigo_marca", sql)
        self.assertNotIn("CodigoMarca IN", sql)

    def test_js_renderiza_resumen_marcas(self):
        js = (Path(__file__).resolve().parents[1] / "static/reports/js/fabricados_superart.js").read_text()
        self.assertIn("renderMarcasResumen", js)
        self.assertIn("Totales por marca", js)
