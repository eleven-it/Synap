# -*- coding: utf-8 -*-
"""Tests filtros UX, APIs predictivas y rango → meses (fabricados_superart)."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import SimpleTestCase

from mpr.services_fabricados_superart import (
    buscar_marcas_predictivo,
    buscar_superart_predictivo,
    meses_en_rango,
    parse_filtros_fabricados_superart,
    primer_dia_mes_calendario,
)


class MesesEnRangoTest(SimpleTestCase):
    def test_mes_unico(self):
        self.assertEqual(
            meses_en_rango(date(2026, 10, 1), date(2026, 10, 31)),
            ["2026-10"],
        )

    def test_varios_meses(self):
        self.assertEqual(
            meses_en_rango(date(2026, 8, 15), date(2026, 10, 3)),
            ["2026-08", "2026-09", "2026-10"],
        )

    def test_invierte_si_hasta_antes(self):
        self.assertEqual(
            meses_en_rango(date(2026, 12, 1), date(2026, 1, 31)),
            ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06",
             "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"],
        )


class ParseFiltrosRangoTest(SimpleTestCase):
    def test_desde_hasta_deriva_meses(self):
        q = QueryDict("desde=2026-10-01&hasta=2026-11-15")
        f = parse_filtros_fabricados_superart(q, hoy=date(2026, 11, 20))
        self.assertEqual(f["desde_iso"], "2026-10-01")
        self.assertEqual(f["hasta_iso"], "2026-11-15")
        self.assertEqual(f["meses"], ["2026-10", "2026-11"])

    def test_sin_fechas_usa_mes_actual(self):
        f = parse_filtros_fabricados_superart(QueryDict(""), hoy=date(2026, 7, 9))
        self.assertEqual(f["desde_iso"], primer_dia_mes_calendario(date(2026, 7, 9)).isoformat())
        self.assertEqual(f["hasta_iso"], "2026-07-09")
        self.assertEqual(f["meses"], ["2026-07"])


class BuscarPredictivoTest(SimpleTestCase):
    @patch("stock.services.inventario_tabla.listar_marcas_catalogo")
    def test_buscar_marcas_filtra_label(self, mock_cat):
        mock_cat.return_value = [
            {"value": 1, "label": "Best Sox"},
            {"value": 2, "label": "Otra"},
        ]
        out = buscar_marcas_predictivo("emp", "best")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["label"], "Best Sox")

    @patch("mpr.services_fabricados_superart.mysql_cursor")
    def test_buscar_superart_sql(self, mock_ctx):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"codigo": "SA-01"}]
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        out = buscar_superart_predictivo("emp", "SA")
        self.assertEqual(out[0]["codigo"], "SA-01")
        mock_cursor.execute.assert_called_once()

