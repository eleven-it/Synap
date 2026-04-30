# -*- coding: utf-8 -*-
"""Tests en memoria: merge/rollup REM y PED por línea en árbol de detalle objetivos vs BO."""

from __future__ import annotations

from django.test import SimpleTestCase

from reports.services import ventas_objetivos_bo_runner as runner


class TestMergeRemPedLineasEnDetalle(SimpleTestCase):
    def test_merge_y_rollup_suma_en_rubro(self):
        tree = [
            {
                "tipo": "rubro",
                "codigo_rubro": 1,
                "nombre_rubro": "R1",
                "facturacion": 100.0,
                "cantidades_vendidas": 1.0,
                "children": [
                    {
                        "tipo": "subrubro",
                        "id_subrubro": 2,
                        "nombre_subrubro": "S1",
                        "facturacion": 100.0,
                        "cantidades_vendidas": 1.0,
                        "children": [
                            {
                                "tipo": "articulo",
                                "id_art": 99,
                                "nombre_articulo": "Art",
                                "facturacion": 100.0,
                                "cantidades_vendidas": 1.0,
                                "backorder_total": 0.0,
                                "bo_con_stock": 0.0,
                                "bo_con_ingreso": 0.0,
                                "bo_sin_stock": 0.0,
                            }
                        ],
                    }
                ],
            }
        ]
        meta = {
            "codigo_rubro": 1,
            "nombre_rubro": "R1",
            "id_subrubro": 2,
            "nombre_subrubro": "S1",
            "nombre_articulo": "Art",
        }
        rem = {99: {**meta, "remitos_lineas": 10.0}}
        ped = {99: {**meta, "pedidos_armado_lineas": 7.5}}
        runner._merge_bo_en_detalle_arbol(tree, {})
        runner._merge_rem_ped_lineas_en_detalle_arbol(tree, rem, ped)
        runner._rollup_bo_en_detalle(tree)
        runner._rollup_rem_ped_lineas_en_detalle(tree)

        art = tree[0]["children"][0]["children"][0]
        self.assertAlmostEqual(art["remitos_lineas"], 10.0)
        self.assertAlmostEqual(art["pedidos_armado_lineas"], 7.5)
        self.assertAlmostEqual(tree[0]["remitos_lineas"], 10.0)
        self.assertAlmostEqual(tree[0]["pedidos_armado_lineas"], 7.5)

    def test_append_solo_rem_sin_venta(self):
        tree: list = []
        runner._merge_rem_ped_lineas_en_detalle_arbol(
            tree,
            {
                42: {
                    "remitos_lineas": 20.0,
                    "pedidos_armado_lineas": 0.0,
                    "nombre_articulo": "Solo REM",
                    "codigo_rubro": 5,
                    "nombre_rubro": "Rx",
                    "id_subrubro": 6,
                    "nombre_subrubro": "Sx",
                }
            },
            {},
        )
        runner._rollup_bo_en_detalle(tree)
        runner._rollup_rem_ped_lineas_en_detalle(tree)
        self.assertEqual(len(tree), 1)
        art = tree[0]["children"][0]["children"][0]
        self.assertEqual(art["id_art"], 42)
        self.assertAlmostEqual(art["remitos_lineas"], 20.0)
        self.assertAlmostEqual(art["facturacion"], 0.0)
