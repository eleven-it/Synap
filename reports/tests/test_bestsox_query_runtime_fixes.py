# -*- coding: utf-8 -*-
"""Unit tests: fechas, reglas compras por detalle, consignación dict rows."""
from __future__ import annotations

from datetime import date, datetime
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.bestsox_query_dates import parse_filter_date
from reports.services.compras_terceros_config import get_compras_terceros_reglas
from reports.services.compras_terceros_sql import fetch_compras_regla_filas
from reports.services.consignacion_stock_query import fetch_remitos_consignacion_resumen


class ParseFilterDateTest(SimpleTestCase):
    def test_from_iso_string_returns_date(self):
        d = parse_filter_date("2026-08-01")
        self.assertIsInstance(d, date)
        self.assertEqual(d, date(2026, 8, 1))

    def test_from_date_unchanged(self):
        d0 = date(2026, 10, 31)
        self.assertIs(parse_filter_date(d0), d0)

    def test_from_datetime(self):
        self.assertEqual(parse_filter_date(datetime(2026, 11, 3, 15, 0)), date(2026, 11, 3))

    def test_timedelta_safe_on_parsed_range(self):
        desde = parse_filter_date("2026-08-01")
        hasta = parse_filter_date("2026-10-31")
        self.assertIsNotNone(desde)
        self.assertIsNotNone(hasta)
        excl = hasta + __import__("datetime").timedelta(days=1)
        self.assertEqual(excl.isoformat(), "2026-11-01")


class ComprasReglasDetalleTest(SimpleTestCase):
    def test_default_rules_use_detalle_not_cuentaproveedor(self):
        by_id = {r["id"]: r for r in get_compras_terceros_reglas()}
        self.assertEqual(by_id["mys_underwear"]["match"]["detalle_contains"], "MYS UNDERWEAR")
        self.assertEqual(by_id["jimmy_buchwald"]["match"]["detalle_contains"], "INGRESO DE JIMMY")
        self.assertNotIn("codigo_proveedor", by_id["mys_underwear"]["match"])
        self.assertNotIn("require_tipo_comp", by_id["mys_underwear"])

    def test_fetch_regla_sql_uses_detalle_like_without_proveedor_join(self):
        regla = next(r for r in get_compras_terceros_reglas() if r["id"] == "mys_underwear")
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        cursor.description = []

        fetch_compras_regla_filas(
            cursor,
            regla,
            desde=date(2026, 8, 1),
            hasta=date(2026, 11, 30),
        )

        sql = cursor.execute.call_args[0][0]
        params = cursor.execute.call_args[0][1]
        self.assertNotIn("cuentaproveedor", sql.lower())
        self.assertIn("ms.detalle", sql.lower())
        self.assertIn("LIKE %s", sql)
        self.assertTrue(any("%MYS UNDERWEAR%" in str(p) for p in params))


class ConsignacionDictRowTest(SimpleTestCase):
    def test_resumen_reads_fac_from_dict_cursor(self):
        cursor = MagicMock()

        def execute_side_effect(sql, params=None):
            if "FROM comp_ped h" in sql:
                cursor.fetchall.return_value = [
                    {
                        "CodigoMovimiento": 99,
                        "NroComprobante": "0008-00029348",
                        "Fecha": date(2026, 10, 15),
                        "codigo_cliente": 309,
                        "nombre_cliente": "MAURO BRUNO",
                        "modalidad_remit": "Normal",
                        "detalle": "EN CONSIGNACION",
                        "criterio_origen": "detalle",
                    }
                ]
            elif "AS rem" in sql or " AS rem," in sql:
                cursor.fetchone.return_value = {"rem": 444.0, "dev": 0.0, "renglones": 31}
            elif "AS fac" in sql:
                cursor.fetchone.return_value = {"fac": 0.0}

        cursor.execute.side_effect = execute_side_effect

        out = fetch_remitos_consignacion_resumen(
            cursor,
            remito_desde=date(2026, 8, 1),
            remito_hasta=date(2026, 10, 31),
            corte_facturas=date(2026, 11, 3),
        )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["packs_remitidos"], 444.0)
        self.assertEqual(out[0]["packs_facturados"], 0.0)
        self.assertEqual(out[0]["packs_saldo"], 444.0)
