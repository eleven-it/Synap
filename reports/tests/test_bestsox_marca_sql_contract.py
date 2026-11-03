# -*- coding: utf-8 -*-
"""Contrato SQL informes BestSox (marca, consignación, compras reglas)."""
from __future__ import annotations

import inspect
import os
from unittest.mock import MagicMock

from django.test import SimpleTestCase, TestCase, tag

from reports.services import (
    compras_marca_superart_query,
    consignacion_stock_query,
    produccion_marca_superart_query,
)
from reports.services.compras_terceros_sql import sql_marca_join
from reports.tests.reference_bestsox_ago_oct_2026 import load_reference, meses_periodo, periodo_filtros


class BestsoxMarcaSqlContractTest(SimpleTestCase):
    def test_marca_join_uses_cod_marca(self):
        self.assertIn("m.CodMarca = a.CodigoMarca", sql_marca_join())
        self.assertNotIn("m.CodigoMarca", sql_marca_join())

    def test_produccion_queries_use_cod_marca(self):
        for fn in (
            produccion_marca_superart_query.fetch_produccion_mpr_filas,
            produccion_marca_superart_query.fetch_produccion_fason_filas,
        ):
            src = inspect.getsource(fn)
            with self.subTest(fn=fn.__name__):
                self.assertIn("m.CodMarca = a.CodigoMarca", src)
                self.assertIn("s.TipoComp", src if fn.__name__ == "fetch_produccion_fason_filas" else "CodMarca")
        fason_src = inspect.getsource(produccion_marca_superart_query.fetch_produccion_fason_filas)
        self.assertIn("FABRICA S Y M", fason_src)
        self.assertNotIn("ms.tipo_mov = %s", fason_src)

    def test_compras_standard_uses_cod_marca_and_id_stock(self):
        src = inspect.getsource(compras_marca_superart_query.fetch_compras_standard_filas)
        self.assertIn("m.CodMarca = a.CodigoMarca", src)
        self.assertIn("s.id_stock", src)
        self.assertNotIn("movimiento_ids", src.lower())

    def test_consignacion_cliente_column_and_like_param(self):
        src = inspect.getsource(consignacion_stock_query.fetch_saldo_consignacion_por_articulo)
        self.assertIn("c.nombre_cliente", src)
        self.assertNotIn("NombreCliente", src)
        self.assertIn("LIKE %s", src)
        self.assertNotIn("LIKE '%EN CONSIGNACION%'", src)
        self.assertIn("rf.CodigoMovimientoR = h.CodigoMovimiento", src)
        self.assertNotIn(
            "rf.CodigoMovimientoR = h.CodigoMovimiento\n                           AND IFNULL",
            src,
        )

    def test_dedupe_keeps_single_id_stock(self):
        filas = [
            {"id_stock": 1, "packs": 10.0, "prendas": 10.0, "docenas": 1.0},
            {"id_stock": 1, "packs": 5.0, "prendas": 5.0, "docenas": 0.5},
            {"id_stock": 2, "packs": 3.0, "prendas": 3.0, "docenas": 0.25},
        ]
        out = compras_marca_superart_query._dedupe_compras_filas(filas)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["packs"], 10.0)


@tag("bestsox_mysql")
class BestsoxMarcaReportsLiveMysqlTotalsTest(TestCase):
    """Requiere pool Synap + BESTSOX_BASE_EMPRESA apuntando a BestSox."""

    def _base(self):
        return (os.environ.get("BESTSOX_BASE_EMPRESA") or "").strip()

    def setUp(self):
        if not self._base():
            self.skipTest("BESTSOX_BASE_EMPRESA no configurada")

    def _filters(self):
        p = periodo_filtros()
        return {**p, "base_empresa": self._base()}

    def test_live_produccion_totales(self):
        from reports.services.produccion_marca_superart_runner import run_produccion_marca_superart

        report = MagicMock(slug="produccion-marca-superart", name="P", category="operational", version="1")
        user = MagicMock(base_empresa=self._base())
        result = run_produccion_marca_superart(report, {"filters": self._filters()}, user)
        self.assertFalse(result.notes, msg=result.notes)
        ref = load_reference()["produccion"]["total"]
        self.assertEqual(int(result.totals["pares_total"]), int(ref["pares"]["total"]))

    def test_live_compras_totales(self):
        from reports.services.compras_marca_superart_runner import run_compras_marca_superart

        report = MagicMock(slug="compras-marca-superart", name="C", category="operational", version="1")
        user = MagicMock(base_empresa=self._base())
        result = run_compras_marca_superart(report, {"filters": self._filters()}, user)
        self.assertFalse(result.notes, msg=result.notes)
        ref = load_reference()["compras"]["total"]
        self.assertEqual(int(result.totals["packs_total"]), int(ref["packs"]["total"]))
        self.assertEqual(int(result.totals["prendas_total"]), int(ref["prendas"]["total"]))

    def test_live_consignacion_totales(self):
        from reports.services.consignacion_stock_runner import run_consignacion_stock

        report = MagicMock(slug="consignacion-stock", name="S", category="operational", version="1")
        user = MagicMock(base_empresa=self._base())
        result = run_consignacion_stock(report, {"filters": self._filters()}, user)
        self.assertFalse(result.notes, msg=result.notes)
        ref = load_reference()["consignacion"]["total"]
        self.assertEqual(int(result.totals["packs_saldo"]), int(ref["packs"]))

    def test_live_sql_executes_produccion_mpr(self):
        from reports.services.produccion_marca_superart_query import fetch_produccion_mpr_filas
        from mpr.services import mysql_cursor

        with mysql_cursor(self._base(), dict_cursor=True) as cursor:
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            rows = fetch_produccion_mpr_filas(cursor, meses_periodo())
        self.assertGreater(len(rows), 0)
