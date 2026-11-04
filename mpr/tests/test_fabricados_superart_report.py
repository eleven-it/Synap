# -*- coding: utf-8 -*-
"""Tests reporte fabricados_superart (agrupación y SQL helper)."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.reportes_transicion_lote_sql import (
    FASON_DEPOSITO_DESTINO_SEMI_ELABORADO,
    FASON_DETALLE_LIKE_PREFIX,
    FASON_MOTIVO_MOVIMIENTO,
    FASON_MOVIMIENTO_ANULADO_NO,
    FASON_STOCK_TIPO_COMP,
    fetch_fabricado_primera_por_articulo_mes,
    fetch_fason_tejeduria_por_articulo_mes,
    normalizar_meses_yyyy_mm,
)
from mpr.services_fabricados_superart import (
    SIN_SUPERART_LABEL,
    agrupar_fabricados_por_superart,
    merge_filas_fabricado_y_fason,
    parse_filtros_fabricados_superart,
    parse_superarts_incluidos_desde_get,
    reporte_mpr_fabricados_superart,
    superart_desde_id_manual,
)


class TestMergeFabricadoFason(SimpleTestCase):
    def test_suma_mismo_articulo_mes(self):
        mpr = [{"id_articulo": 1, "id_manual": "SA", "ym": "2026-10", "cantidad": 10}]
        fason = [{"id_articulo": 1, "id_manual": "SA", "ym": "2026-10", "cantidad": 5}]
        out = merge_filas_fabricado_y_fason(mpr, fason)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["cantidad"], 15.0)

    def test_articulo_solo_fason(self):
        fason = [{"id_articulo": 99, "id_manual": "", "ym": "2026-10", "cantidad": 3}]
        out = merge_filas_fabricado_y_fason([], fason)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id_articulo"], 99)

    def test_articulo_solo_mpr_sin_cambios(self):
        mpr = [{"id_articulo": 2, "id_manual": "X", "ym": "2026-09", "cantidad": 7}]
        out = merge_filas_fabricado_y_fason(mpr, [])
        self.assertEqual(out, mpr)


class TestFetchFasonSql(SimpleTestCase):
    def test_sql_predicados_fason(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        fetch_fason_tejeduria_por_articulo_mes(mock_cursor, ["2026-08", "2026-10"], marcas_ids=[1])
        sql = mock_cursor.execute.call_args[0][0]
        params = list(mock_cursor.execute.call_args[0][1])
        self.assertIn("movimiento_stock", sql)
        self.assertIn("deposito_destino", sql)
        self.assertIn("detalle LIKE", sql)
        self.assertIn("ms.fecha >=", sql)
        self.assertIn("ms.fecha <", sql)
        self.assertNotIn("detalle = ''", sql)
        self.assertIn(FASON_STOCK_TIPO_COMP, params)
        self.assertIn(FASON_MOTIVO_MOVIMIENTO, params)
        self.assertIn(FASON_DEPOSITO_DESTINO_SEMI_ELABORADO, params)
        self.assertIn(FASON_MOVIMIENTO_ANULADO_NO, params)
        self.assertIn(FASON_DETALLE_LIKE_PREFIX, params)
        self.assertIn("2026-08", params)
        self.assertIn("2026-10", params)
        self.assertIn(1, params)


class TestNormalizarMeses(SimpleTestCase):
    def test_meses_no_contiguos(self):
        self.assertEqual(
            normalizar_meses_yyyy_mm(["2025-11", "2026-02", "bad", "2025-11"]),
            ["2025-11", "2026-02"],
        )


class TestAgrupacionFabricados(SimpleTestCase):
    def _agrupar(self, filas, meses, superarts=None, busqueda=""):
        desc = {
            1: ("ART-1", "Artículo uno"),
            2: ("ART-2", "Artículo dos"),
            3: ("ART-3", ""),
        }
        kwargs = {}
        if superarts is not None:
            kwargs["superarts_incluidos"] = superarts
        else:
            kwargs["busqueda_superart"] = busqueda
        return agrupar_fabricados_por_superart(
            filas,
            meses,
            desc,
            **kwargs,
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

    def test_busqueda_superart_un_valor_legacy(self):
        filas = [
            {"id_articulo": 1, "id_manual": "ALPHA", "ym": "2026-01", "cantidad": 1},
            {"id_articulo": 2, "id_manual": "BETA", "ym": "2026-01", "cantidad": 1},
        ]
        r = self._agrupar(filas, ["2026-01"], busqueda="beta")
        self.assertEqual(len(r["filas_superart"]), 1)
        self.assertEqual(r["filas_superart"][0]["codigo_superart"], "BETA")

    def test_filtro_varios_superarts_or(self):
        filas = [
            {"id_articulo": 1, "id_manual": "ALPHA", "ym": "2026-01", "cantidad": 1},
            {"id_articulo": 2, "id_manual": "BETA", "ym": "2026-01", "cantidad": 2},
            {"id_articulo": 3, "id_manual": "GAMMA", "ym": "2026-01", "cantidad": 3},
        ]
        r = self._agrupar(filas, ["2026-01"], superarts=["ALPHA", "GAMMA"])
        codes = {row["codigo_superart"] for row in r["filas_superart"]}
        self.assertEqual(codes, {"ALPHA", "GAMMA"})

    def test_orden_por_total_desc(self):
        filas = [
            {"id_articulo": 1, "id_manual": "LOW", "ym": "2026-01", "cantidad": 1},
            {"id_articulo": 2, "id_manual": "HIGH", "ym": "2026-01", "cantidad": 50},
        ]
        r = self._agrupar(filas, ["2026-01"])
        self.assertEqual(r["filas_superart"][0]["codigo_superart"], "HIGH")


class TestParseSuperarts(SimpleTestCase):
    def test_getlist_repetido(self):
        from django.http import QueryDict

        q = QueryDict("q_superart=SA1&q_superart=SA2")
        self.assertEqual(parse_superarts_incluidos_desde_get(q), ["SA1", "SA2"])

    def test_coma_y_valor_unico(self):
        from django.http import QueryDict

        self.assertEqual(
            parse_superarts_incluidos_desde_get(QueryDict("q_superart=ALPHA,BETA")),
            ["ALPHA", "BETA"],
        )
        self.assertEqual(
            parse_superarts_incluidos_desde_get(QueryDict("q_superart=BETA")),
            ["BETA"],
        )


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
    @patch("mpr.services_fabricados_superart.fetch_fason_tejeduria_por_articulo_mes")
    @patch("mpr.services_fabricados_superart.fetch_fabricado_primera_por_articulo_mes")
    @patch("mpr.services_fabricados_superart._fetch_descripciones_articulo")
    @patch("mpr.services_fabricados_superart.mysql_cursor")
    def test_reporte_llama_fetch_primera(self, mock_ctx, mock_desc, mock_mpr, mock_fason):
        mock_fason.return_value = []
        mock_desc.return_value = {10: ("C10", "Desc")}
        mock_mpr.return_value = [
            {"id_articulo": 10, "id_manual": "SA1", "ym": "2026-01", "cantidad": 7},
        ]
        mock_ctx.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        r = reporte_mpr_fabricados_superart("emp", meses=["2026-01"])
        self.assertEqual(r["total_general"], 7.0)
        self.assertEqual(len(r["filas_superart"]), 1)
        mock_fason.assert_called_once()


class TestSuperartDesdeIdManual(SimpleTestCase):
    def test_vacio(self):
        _, _, label = superart_desde_id_manual("")
        self.assertEqual(label, SIN_SUPERART_LABEL)


class TestExportExcelDosHojas(SimpleTestCase):
    def test_xlsx_dos_hojas(self):
        from mpr.export import exportar_fabricados_superart_xlsx

        ctx = {
            "filtros_fabricados_superart": {"superarts_incluidos": ["SA1", "SA2"]},
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
