# -*- coding: utf-8 -*-
"""Tests helper FA/NC de cabecera sin renglón de mercadería."""
from unittest.mock import Mock

from django.test import SimpleTestCase

from reports.services.ajustes_sin_mercaderia import (
    NOMBRE_AJUSTES,
    consultar_ajustes_sin_mercaderia,
    filtros_catalogo_restringen,
    pin_ajustes_al_final,
)


class FiltrosCatalogoAjustesTest(SimpleTestCase):
    def test_sin_filtros(self):
        self.assertFalse(filtros_catalogo_restringen())

    def test_con_marca(self):
        self.assertTrue(filtros_catalogo_restringen(marcas_incluidos=[1]))

    def test_con_superart(self):
        self.assertTrue(filtros_catalogo_restringen(superarts=["SA1"]))


class ConsultarAjustesSinMercaderiaTest(SimpleTestCase):
    def test_mapea_cliente_y_omite_centavos(self):
        cursor = Mock()
        cursor.description = [("codigo_cliente",), ("nombre_cliente",), ("facturacion",)]
        cursor.fetchall.return_value = [
            (10, "Cliente A", -100.0),
            (11, "Cero", 0.001),
        ]
        filas = consultar_ajustes_sin_mercaderia(
            cursor,
            ["cc.Fecha >= %s"],
            ["2026-08-01"],
            renglon_ok_sql="art.tipo_art = 'Articulo'",
            group_by="cliente",
        )
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["codigo_cliente"], 10)
        self.assertEqual(filas[0]["nombre_cliente"], "Cliente A")
        self.assertAlmostEqual(filas[0]["facturacion"], -100.0, places=2)
        sql = cursor.execute.call_args.args[0]
        self.assertIn("NOT EXISTS", sql)
        self.assertIn("SubtotalDesc", sql)

    def test_group_by_mes_incluye_anio_mes(self):
        cursor = Mock()
        cursor.description = [
            ("codigo_cliente",),
            ("nombre_cliente",),
            ("anio_mes",),
            ("facturacion",),
        ]
        cursor.fetchall.return_value = [(10, "Cliente A", "202608", -50.0)]
        filas = consultar_ajustes_sin_mercaderia(
            cursor,
            ["cc.Anulado = 'No'"],
            [],
            renglon_ok_sql="1=1",
            group_by="cliente_mes",
        )
        self.assertEqual(filas[0]["anio_mes"], "202608")
        self.assertIn("DATE_FORMAT", cursor.execute.call_args.args[0])


class PinAjustesAlFinalTest(SimpleTestCase):
    def test_pin_y_flag(self):
        arbol = [
            {"id_art": -1, "nombre_articulo": NOMBRE_AJUSTES, "children": [{"tipo": "x"}]},
            {"id_art": 5, "nombre_articulo": "Art", "children": []},
        ]
        pinned = pin_ajustes_al_final(
            arbol,
            es_ajuste=lambda n: int(n.get("id_art") or 0) == -1,
        )
        self.assertEqual(pinned[0]["id_art"], 5)
        self.assertEqual(pinned[-1]["nombre_articulo"], NOMBRE_AJUSTES)
        self.assertTrue(pinned[-1]["es_ajuste_cabecera"])
        self.assertTrue(pinned[-1]["children"][0]["es_ajuste_cabecera"])
