"""Contrato numérico mínimo del servicio de resumen ejecutivo (sin MySQL)."""
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from reports.executive_summary_api_views import _parse_puntos_venta_filtro
from reports.services.executive_sales_summary import (
    _cc_scope_sql,
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


class ExecutiveSummaryPuntoVentaTests(SimpleTestCase):
    """Oleada 4.A: filtro PV en alcance SQL, meta y API."""

    def test_cc_scope_sql_punto_venta(self):
        sql, params = _cc_scope_sql([2, 5], [10, 11])
        self.assertIn("cc.CodSucursal IN (%s,%s)", sql)
        self.assertIn("cc.id_pv IN (%s,%s)", sql)
        self.assertEqual(params, [2, 5, 10, 11])

    def test_cc_scope_sql_sin_punto_venta_no_clausula_pv(self):
        sql, params = _cc_scope_sql([2], None)
        self.assertIn("cc.CodSucursal IN (%s)", sql)
        self.assertNotIn("id_pv", sql)
        self.assertEqual(params, [2])

    def test_executive_summary_meta_punto_venta_filtrados(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(0.0, 0.0))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(
            cursor,
            date(2026, 4, 1),
            [1],
            [2],
            puntos_venta_filtro=[10, 11],
        )
        self.assertEqual(out["meta"].get("punto_venta_filtrados"), [10, 11])

    def test_executive_summary_sin_pv_meta_null(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(0.0, 0.0))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(cursor, date(2026, 4, 1), [1], [2])
        self.assertIsNone(out["meta"].get("punto_venta_filtrados"))

    def test_executive_summary_api_parse_puntos_venta(self):
        class Q:
            def getlist(self, key):
                return {"punto_venta": ["10", "11", "x"]}.get(key, [])

            def get(self, key, default=None):
                return None

        self.assertEqual(_parse_puntos_venta_filtro(Q()), [10, 11])

    def test_template_executive_summary_tags_punto_venta(self):
        tpl_path = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "reports"
            / "executive_summary.html"
        )
        html = tpl_path.read_text(encoding="utf-8")
        self.assertIn('id="exec_sucursales"', html)
        self.assertIn('id="exec_punto_venta"', html)
        self.assertIn('id="exec-scope-sucursal-pv"', html)

    def test_integration_executive_pv_within_sucursales(self):
        """PV recorta KPIs dentro del alcance de sucursales clasificadas (intersección)."""
        cursor = MagicMock()
        executed: list[tuple[str, list]] = []

        def capture_execute(sql, params=None):
            executed.append((sql, list(params or [])))

        cursor.execute = MagicMock(side_effect=capture_execute)
        cursor.fetchone = MagicMock(return_value=(100.0, 60.0))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(
            cursor,
            date(2026, 4, 1),
            mayorista_sucursales=[10, 20],
            minorista_sucursales=[30],
            sucursales_filtro=[10],
            puntos_venta_filtro=[5, 6],
        )

        joined_sql = "\n".join(sql for sql, _ in executed)
        self.assertIn("cc.CodSucursal IN", joined_sql)
        self.assertIn("cc.id_pv IN", joined_sql)
        scope_params = [
            p
            for sql, ps in executed
            if "cc.CodSucursal IN" in sql and "cc.id_pv IN" in sql
            for p in ps
            if isinstance(p, int)
        ]
        self.assertIn(10, scope_params)
        self.assertIn(5, scope_params)
        self.assertIn(6, scope_params)
        self.assertNotIn(20, scope_params)
        self.assertNotIn(30, scope_params)
        self.assertEqual(out["meta"].get("punto_venta_filtrados"), [5, 6])
        may_scope, min_scope, cons_scope = resolve_executive_scope(
            [10, 20], [30], [10]
        )
        self.assertEqual(may_scope, [10])
        self.assertEqual(min_scope, [])
        self.assertEqual(cons_scope, [10])

    def test_executive_summary_js_punto_venta_qs(self):
        js_path = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "reports"
            / "js"
            / "executive_summary.js"
        )
        content = js_path.read_text(encoding="utf-8")
        self.assertIn("FILTERS_API_URL", content)
        self.assertIn("?type=puntos_venta", content)
        self.assertIn('append("punto_venta"', content)


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
