"""Contrato numérico mínimo del servicio de resumen ejecutivo (sin MySQL)."""
from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.executive_sales_summary import run_executive_summary


class ExecutiveSummaryContractTests(SimpleTestCase):
    def test_run_executive_summary_con_cursor_vacio_devuelve_estructura(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(0.0, 0.0))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(cursor, date(2026, 4, 1), [], [])

        self.assertIn("fecha_referencia", out)
        self.assertIn("kpis", out)
        self.assertIn("serie_horaria", out)
        self.assertEqual(len(out["serie_horaria"]), 24)
        self.assertIn("serie_7_dias", out)
        self.assertEqual(len(out["serie_7_dias"]), 7)
        self.assertIn("split_mayorista_minorista", out)
        self.assertIn("top_productos", out)
        self.assertIsInstance(out["top_productos"], list)
        self.assertIn("sucursales_disponibles", out)
        self.assertIsInstance(out["sucursales_disponibles"], list)
        self.assertIn("gap_vs_ayer_monto", out["kpis"])
        self.assertEqual(out["meta"].get("top_productos_criterio"), "importe_neto_linea")
        self.assertIsNone(out["meta"].get("cod_sucursal_filtro"))
        self.assertEqual(out["meta"].get("top_productos_orden"), "importe_neto")
        self.assertEqual(out["meta"].get("definicion"), "executive-sales-v2")
        self.assertEqual(out["meta"].get("margen_costo_criterio"), "precio_costoxr_linea")
        self.assertEqual(out["meta"].get("margen_venta_criterio"), "precio_netoxr_linea")
        self.assertIn("nota_venta_neta_lineas_vs_comprobante", out["meta"])
        self.assertIn("margen_bruto", out)
        mb = out["margen_bruto"]
        self.assertIn("venta_neta_lineas", mb)
        self.assertIn("costo_neto_lineas", mb)
        self.assertIn("margen_absoluto", mb)
        self.assertIsNone(mb.get("pct_sobre_venta_lineas"))
        self.assertIsInstance(out["margen_por_rubro"], list)
        self.assertIsInstance(out["margen_por_subrubro"], list)

    def test_run_executive_summary_propaga_filtro_sucursal_y_orden_top(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(0.0, 0.0))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(
            cursor,
            date(2026, 4, 1),
            [],
            [],
            cod_sucursal=12,
            top_productos_orden="unidades",
        )
        self.assertEqual(out["meta"].get("cod_sucursal_filtro"), 12)
        self.assertEqual(out["meta"].get("top_productos_orden"), "unidades")
        self.assertEqual(out["meta"].get("definicion"), "executive-sales-v2")

    def test_margen_pct_sobre_venta_lineas_cuando_hay_venta(self):
        """El 7.º fetchone corresponde a totales de margen (tras 6 lecturas de comprobante/unidades/split)."""
        seq = [(0.0, 0.0)] * 6 + [(100.0, 60.0)]
        it = iter(seq)

        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=lambda: next(it, (0.0, 0.0)))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(cursor, date(2026, 4, 1), [], [])
        mb = out["margen_bruto"]
        self.assertEqual(mb["venta_neta_lineas"], 100.0)
        self.assertEqual(mb["costo_neto_lineas"], 60.0)
        self.assertEqual(mb["margen_absoluto"], 40.0)
        self.assertEqual(mb["pct_sobre_venta_lineas"], 40.0)
