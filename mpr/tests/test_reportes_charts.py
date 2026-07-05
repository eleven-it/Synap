"""Tests payloads de gráficos reportes MPR."""
from django.test import SimpleTestCase

from mpr.reportes_charts import build_charts_produccion, MAX_RANKED_BARS


class BuildChartsProduccionTest(SimpleTestCase):
    def test_operario_hbar_top_n(self):
        filas = [
            {"operario": f"Op {i}", "unidades": 100 - i}
            for i in range(20)
        ]
        charts = build_charts_produccion("operario", {"filas": filas})
        self.assertIsNotNone(charts)
        block = charts["blocks"][0]
        self.assertEqual(block["kind"], "hbar")
        self.assertEqual(len(block["labels"]), MAX_RANKED_BARS)

    def test_operario_vacio_sin_grafico(self):
        self.assertIsNone(build_charts_produccion("operario", {"filas": []}))

    def test_cadena_incluye_funnel_y_doughnut(self):
        filas = [
            {
                "estado": "falta_parte",
                "estado_label": "Falta parte",
                "gap_envio_parte": 10,
                "codigo_articulo": "1.1.1",
                "enviado": 10,
                "parte": 0,
                "clasificado": 0,
            },
            {
                "estado": "completo",
                "estado_label": "Completo",
                "gap_envio_parte": 0,
                "codigo_articulo": "1.1.2",
                "enviado": 5,
                "parte": 5,
                "clasificado": 5,
            },
        ]
        charts = build_charts_produccion(
            "cadena",
            {"filas": filas, "kpis": {"enviado": 15, "parte": 5, "clasificado": 5}},
        )
        kinds = [b["kind"] for b in charts["blocks"]]
        self.assertIn("grouped_bar", kinds)
        self.assertIn("doughnut", kinds)
        self.assertIn("hbar_grouped", kinds)

    def test_pendiente_colores_critico(self):
        filas = [
            {"codigo_manual": "A", "pendiente": 60, "critico": True},
            {"codigo_manual": "B", "pendiente": 10, "critico": False},
        ]
        charts = build_charts_produccion("pendiente", {"filas": filas})
        block = charts["blocks"][0]
        self.assertEqual(block["colors"][0], "#dc2626")
        self.assertEqual(block["colors"][1], "#d97706")

    def test_resumen_diario_lineas(self):
        dias = [
            {
                "fecha_display": "01/07/2026",
                "enviado": 1,
                "parte": 2,
                "clasificado": 3,
                "scrap": 0,
            }
        ]
        charts = build_charts_produccion("resumen_diario", {"dias": dias})
        self.assertEqual(charts["blocks"][0]["kind"], "line_multi")

    def test_reporte_desconocido_none(self):
        self.assertIsNone(build_charts_produccion("otro", {"filas": [1]}))
