# -*- coding: utf-8 -*-
"""Tests reporte fabricados_superart (agrupación y SQL helper)."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.reportes_transicion_lote_sql import (
    fetch_fabricado_primera_por_articulo_mes,
    normalizar_meses_yyyy_mm,
)
from mpr.services_fabricados_superart import (
    SIN_SUPERART_LABEL,
    agrupar_fabricados_por_superart,
    parse_filtros_fabricados_superart,
    reporte_mpr_fabricados_superart,
    superart_desde_id_manual,
)


class TestNormalizarMeses(SimpleTestCase):
    def test_meses_no_contiguos(self):
        self.assertEqual(
            normalizar_meses_yyyy_mm(["2025-11", "2026-02", "bad", "2025-11"]),
            ["2025-11", "2026-02"],
        )


class TestAgrupacionFabricados(SimpleTestCase):
    def _agrupar(self, filas, meses, busqueda=""):
        desc = {
            1: ("ART-1", "Artículo uno"),
            2: ("ART-2", "Artículo dos"),
            3: ("ART-3", "Sin manual"),
        }
        return agrupar_fabricados_por_superart(
            filas,
            meses,
            desc,
            busqueda_superart=busqueda,
        )

    def test_agrupa_por_superart_y_suma_meses(self):
        filas = [
            {"id_articulo": 1, "id_manual": "SA-100", "ym": "2026-01", "cantidad": 10},
            {"id_articulo": 2, "id_manual": "SA-100", "ym": "2026-03", "cantidad": 5},
            {"id_articulo": 1, "id_manual": "SA-100", "ym": "2026-03", "cantidad": 2},
        ]
        r = self._agrupar(filas, ["2026-01", "2026-03"])
        self.assertEqual(len(r["filas_superart"]), 1)
        sa = r["filas_superart"][0]
        self.assertEqual(sa["total"], 17.0)
        self.assertEqual(sa["por_mes"]["2026-01"], 10.0)
        self.assertEqual(sa["por_mes"]["2026-03"], 7.0)
        self.assertEqual(len(sa["articulos"]), 2)

    def test_sin_superart(self):
        filas = [{"id_articulo": 3, "id_manual": "", "ym": "2026-01", "cantidad": 4}]
        r = self._agrupar(filas, ["2026-01"])
        self.assertEqual(r["filas_superart"][0]["descripcion_superart"], SIN_SUPERART_LABEL)

    def test_excluye_segunda_via_fetch_sql_params(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        fetch_fabricado_primera_por_articulo_mes(mock_cursor, ["2026-01"])
        sql = mock_cursor.execute.call_args[0][0]
        params = mock_cursor.execute.call_args[0][1]
        self.assertIn("tipo_origen = %s", sql)
        self.assertIn("tipo_destino = %s", sql)
        self.assertEqual(params[0], "Produccion")
        self.assertEqual(params[1], "SemiElaborado")
        self.assertNotIn("2daSeleccion", sql)

    def test_sql_date_format_escapado_para_mysqldb_params(self):
        """MySQLdb formatea la query con %; DATE_FORMAT debe usar %%Y-%%m."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        fetch_fabricado_primera_por_articulo_mes(mock_cursor, ["2026-10"], marcas_ids=[7])
        sql = mock_cursor.execute.call_args[0][0]
        params = list(mock_cursor.execute.call_args[0][1])
        self.assertIn("DATE_FORMAT(t.creado_en, '%%Y-%%m')", sql)
        self.assertNotIn("'%Y-%m'", sql)
        try:
            formatted = sql % tuple(params)
        except (TypeError, ValueError) as exc:
            self.fail(f"query % params no debe fallar con DATE_FORMAT: {exc}")
        self.assertIn("DATE_FORMAT(t.creado_en, '%Y-%m')", formatted)
        self.assertIn("2026-10", formatted)
        self.assertIn("CodigoMarca IN (7)", formatted)

    def test_totales_y_mes_pico(self):
        filas = [
            {"id_articulo": 1, "id_manual": "A", "ym": "2026-01", "cantidad": 3},
            {"id_articulo": 1, "id_manual": "A", "ym": "2026-02", "cantidad": 9},
        ]
        r = self._agrupar(filas, ["2026-01", "2026-02"])
        self.assertEqual(r["total_general"], 12.0)
        self.assertEqual(r["kpis"]["mes_pico"], "2026-02")
        self.assertEqual(r["kpis"]["mes_pico_cantidad"], 9.0)

    def test_sin_limite_filas(self):
        filas = [
            {"id_articulo": i, "id_manual": f"SA-{i}", "ym": "2026-01", "cantidad": 1}
            for i in range(1, 301)
        ]
        r = self._agrupar(filas, ["2026-01"])
        self.assertEqual(len(r["filas_superart"]), 300)

    def test_busqueda_superart(self):
        filas = [
            {"id_articulo": 1, "id_manual": "ALPHA", "ym": "2026-01", "cantidad": 1},
            {"id_articulo": 2, "id_manual": "BETA", "ym": "2026-01", "cantidad": 1},
        ]
        r = self._agrupar(filas, ["2026-01"], busqueda="beta")
        self.assertEqual(len(r["filas_superart"]), 1)
        self.assertEqual(r["filas_superart"][0]["codigo_superart"], "BETA")

    def test_orden_por_total_desc(self):
        filas = [
            {"id_articulo": 1, "id_manual": "LOW", "ym": "2026-01", "cantidad": 1},
            {"id_articulo": 2, "id_manual": "HIGH", "ym": "2026-01", "cantidad": 50},
        ]
        r = self._agrupar(filas, ["2026-01"])
        self.assertEqual(r["filas_superart"][0]["codigo_superart"], "HIGH")


class TestParseFiltros(SimpleTestCase):
    def test_default_mes_actual(self):
        from mpr.services_fabricados_superart import mes_actual_yyyy_mm

        class Q:
            def get(self, k, d=""):
                return d

            def getlist(self, k):
                return []

        f = parse_filtros_fabricados_superart(Q(), hoy=date(2026, 10, 15))
        self.assertEqual(f["meses"], [mes_actual_yyyy_mm(date(2026, 10, 15))])
        self.assertEqual(f["desde_iso"], "2026-10-01")
        self.assertEqual(f["hasta_iso"], "2026-10-15")


class TestReporteIntegracion(SimpleTestCase):
    @patch("mpr.services_fabricados_superart._fetch_descripciones_articulo")
    @patch("mpr.services_fabricados_superart.mysql_cursor")
    def test_reporte_llama_fetch_primera(self, mock_ctx, mock_desc):
        mock_desc.return_value = {10: ("C10", "Desc")}
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id_articulo": 10, "id_manual": "SA1", "ym": "2026-01", "cantidad": 7},
        ]
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        r = reporte_mpr_fabricados_superart("emp", meses=["2026-01"])
        self.assertEqual(r["total_general"], 7.0)
        self.assertEqual(len(r["filas_superart"]), 1)


class TestSuperartDesdeIdManual(SimpleTestCase):
    def test_vacio(self):
        _, _, label = superart_desde_id_manual("")
        self.assertEqual(label, SIN_SUPERART_LABEL)


class TestExportExcelDosHojas(SimpleTestCase):
    def test_xlsx_dos_hojas(self):
        from mpr.export import exportar_fabricados_superart_xlsx

        ctx = {
            "meses_columnas": [{"ym": "2026-01", "label": "Ene 2026"}],
            "filas_superart": [
                {
                    "codigo_superart": "SA1",
                    "descripcion_superart": "Super 1",
                    "columnas_mes": [{"ym": "2026-01", "display": "10"}],
                    "total_display": "10",
                    "articulos": [
                        {
                            "codigo_articulo": "A1",
                            "descripcion_articulo": "Art 1",
                            "columnas_mes": [{"ym": "2026-01", "display": "10"}],
                            "total_display": "10",
                        }
                    ],
                }
            ],
            "totales_columnas": [{"ym": "2026-01", "display": "10"}],
            "total_general_display": "10",
        }
        resp = exportar_fabricados_superart_xlsx(ctx)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("spreadsheetml", resp["Content-Type"])
        import openpyxl
        from io import BytesIO

        wb = openpyxl.load_workbook(BytesIO(resp.content))
        self.assertEqual(wb.sheetnames, ["Por superartículo", "Detalle por artículo"])
