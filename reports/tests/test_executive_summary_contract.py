"""Contrato numérico mínimo del servicio de resumen ejecutivo (sin MySQL)."""
from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.executive_sales_summary import (
    _fecha_anio_anterior,
    resolve_executive_scope,
    run_executive_summary,
)


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
        self.assertIn("ventas_anio_anterior_monto", out["kpis"])
        self.assertIn("fecha_comparacion_anio_anterior", out["kpis"])
        split = out["split_mayorista_minorista"]
        self.assertIn("mayorista", split)
        self.assertIn("minorista", split)
        self.assertIn("consolidado", split)
        self.assertNotIn("sin_asignar", split)
        self.assertIn("top_productos", out)
        self.assertIsInstance(out["top_productos"], list)
        self.assertIn("sucursales_disponibles", out)
        self.assertIn("gap_vs_ayer_monto", out["kpis"])
        self.assertEqual(out["meta"].get("top_productos_criterio"), "importe_neto_linea")
        self.assertEqual(out["meta"].get("definicion"), "executive-sales-v4-secciones")
        self.assertTrue(out["meta"].get("sin_sucursales_clasificadas"))
        self.assertIn("secciones", out)
        for clave in ("consolidado", "mayorista", "minorista"):
            self.assertIn(clave, out["secciones"])
            self.assertIn("kpis", out["secciones"][clave])
            self.assertIn("pct_vs_anio_anterior", out["secciones"][clave]["kpis"])
            sk = out["secciones"][clave]["kpis"]
            self.assertIn("ventas_anio_anterior_monto", sk)
        self.assertIn("fecha_comparacion_anio_anterior_aplicada", out["meta"])

    def test_run_executive_summary_propaga_filtro_sucursales_y_orden_top(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(100.0, 50.0))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(
            cursor,
            date(2026, 4, 1),
            [1, 2],
            [3],
            sucursales_filtro=[2],
            top_productos_orden="unidades",
        )
        self.assertEqual(out["meta"].get("sucursales_filtro"), [2])
        self.assertEqual(out["meta"].get("top_productos_orden"), "unidades")
        self.assertFalse(out["meta"].get("sin_sucursales_clasificadas"))

    def test_fecha_comparacion_anio_personalizada(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(0.0, 0.0))
        cursor.fetchall = MagicMock(return_value=[])

        ref = date(2026, 6, 2)
        comp = date(2025, 11, 24)
        out = run_executive_summary(
            cursor, ref, [1], [2], fecha_comparacion_anio=comp
        )
        self.assertEqual(
            out["meta"]["fecha_comparacion_anio_anterior_aplicada"], comp.isoformat()
        )
        self.assertEqual(
            out["secciones"]["consolidado"]["kpis"]["fecha_comparacion_anio_anterior"],
            comp.isoformat(),
        )

    def test_fecha_anio_anterior_29_feb(self):
        self.assertEqual(_fecha_anio_anterior(date(2024, 2, 29)), date(2023, 2, 28))

    def test_margen_estructura_con_sucursales_clasificadas(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(100.0, 60.0))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(cursor, date(2026, 4, 1), [10], [20])
        mb = out["margen_bruto"]
        self.assertIn("venta_neta_lineas", mb)
        self.assertIn("pct_sobre_venta_lineas", mb)
        self.assertFalse(out["meta"]["sin_sucursales_clasificadas"])


class ResolveExecutiveScopeTests(SimpleTestCase):
    def test_interseccion_filtro_ui(self):
        may, mino, all_scope = resolve_executive_scope([1, 2], [3], [2, 99])
        self.assertEqual(may, [2])
        self.assertEqual(mino, [])
        self.assertEqual(all_scope, [2])

    def test_sin_clasificadas_vacio(self):
        may, mino, all_scope = resolve_executive_scope([], [], None)
        self.assertEqual(may, [])
        self.assertEqual(mino, [])
        self.assertEqual(all_scope, [])
