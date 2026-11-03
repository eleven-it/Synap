# -*- coding: utf-8 -*-
"""Contrato SQL informes BestSox (marca, consignación, compras reglas)."""
from __future__ import annotations

import os
from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase, TestCase, tag

from reports.services import (
    compras_marca_superart_query,
    consignacion_stock_query,
    produccion_marca_superart_query,
)
from reports.services.compras_terceros_sql import sql_marca_join
from reports.tests.reference_bestsox_ago_oct_2026 import load_reference, meses_periodo, periodo_filtros


def _mock_query_cursor():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.description = []
    return cursor


def _executed_sql(cursor) -> str:
    return cursor.execute.call_args[0][0]


class BestsoxMarcaSqlContractTest(SimpleTestCase):
    def test_marca_join_uses_cod_marca(self):
        self.assertIn("m.CodMarca = a.CodigoMarca", sql_marca_join())
        self.assertNotIn("m.CodigoMarca", sql_marca_join())

    def test_produccion_queries_use_cod_marca(self):
        cursor = _mock_query_cursor()
        produccion_marca_superart_query.fetch_produccion_mpr_filas(cursor, ["2026-08"])
        sql_mpr = _executed_sql(cursor)
        self.assertIn("m.CodMarca = a.CodigoMarca", sql_mpr)
        self.assertNotIn("m.CodigoMarca", sql_mpr)

        cursor = _mock_query_cursor()
        produccion_marca_superart_query.fetch_produccion_fason_filas(
            cursor,
            desde=date(2026, 8, 1),
            hasta=date(2026, 10, 31),
        )
        sql_fason = _executed_sql(cursor)
        self.assertIn("m.CodMarca = a.CodigoMarca", sql_fason)
        self.assertIn("s.TipoComp", sql_fason)
        self.assertIn("FABRICA S Y M", sql_fason)
        self.assertNotIn("ms.tipo_mov = %s", sql_fason)

    def test_compras_standard_uses_cod_marca_and_id_stock(self):
        cursor = _mock_query_cursor()
        compras_marca_superart_query.fetch_compras_standard_filas(
            cursor,
            desde=date(2026, 8, 1),
            hasta=date(2026, 10, 31),
        )
        sql = _executed_sql(cursor)
        self.assertIn("m.CodMarca = a.CodigoMarca", sql)
        self.assertIn("s.id_stock", sql)
        self.assertNotIn("movimiento_ids", sql.lower())

    def test_consignacion_cliente_column_and_like_param(self):
        params: list = []
        cons_fragment = consignacion_stock_query._remito_es_consignacion_sql("h", params)
        self.assertIn("LIKE %s", cons_fragment)
        self.assertNotIn("LIKE '%EN CONSIGNACION%'", cons_fragment)
        self.assertTrue(any("EN CONSIGNACION" in str(p) for p in params))

        cursor = _mock_query_cursor()
        consignacion_stock_query.fetch_saldo_consignacion_por_articulo(
            cursor,
            remito_desde=date(2026, 8, 1),
            remito_hasta=date(2026, 10, 31),
            corte_facturas=date(2026, 11, 3),
        )
        sql = _executed_sql(cursor)
        self.assertIn("c.nombre_cliente", sql)
        self.assertNotIn("NombreCliente", sql)
        self.assertIn("LIKE %s", sql)
        self.assertIn("rf.CodigoMovimientoR = h.CodigoMovimiento", sql)
        self.assertNotIn(
            "rf.CodigoMovimientoR = h.CodigoMovimiento\n                           AND IFNULL(rf.Anulado",
            sql,
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
