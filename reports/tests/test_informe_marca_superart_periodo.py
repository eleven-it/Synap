# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from reports.services.informe_marca_superart_periodo import agregar_filas_marca_superart_periodo


class InformeMarcaSuperartPeriodoTests(SimpleTestCase):
    def test_agrega_marca_superart_articulo(self):
        filas = [
            {
                "id_articulo": 1,
                "id_manual": "SA1",
                "codigo_marca": 10,
                "nombre_marca": "LB",
                "codigo_articulo": 1,
                "nombre_articulo": "Art",
                "ym": "2026-08",
                "cantidad": 12,
            }
        ]
        ctx = agregar_filas_marca_superart_periodo(
            filas, ["2026-08"], metric_prefix="Pares", metric_field="cantidad"
        )
        arbol = ctx["marca_superart_jerarquia"]
        self.assertEqual(len(arbol), 1)
        self.assertEqual(arbol[0]["nombre_marca"], "LB")
        self.assertEqual(arbol[0]["metrics"]["Pares_Total"], 12.0)
