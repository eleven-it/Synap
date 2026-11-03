# -*- coding: utf-8 -*-
"""
Paridad Ago–Oct 2026 vs Excel de referencia (uploads).

Validación en CI: mock de consultas MySQL con filas derivadas del Excel «Detalle»
/ «Saldo en consignación» (fixture JSON). No sustituye corrida read-only contra
administraNET BestSox; ver docs/reports/BESTSOX_MARCA_VALIDATION_AGO_OCT_2026.md.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, tag

from reports.services.bestsox_marca_reports_seed import (
    COMPRAS_MARCA_SUPERART_SLUG,
    CONSIGNACION_STOCK_SLUG,
    PRODUCCION_MARCA_SUPERART_SLUG,
)
from reports.tests.reference_bestsox_ago_oct_2026 import (
    filas_sql_compras,
    filas_sql_consignacion,
    filas_sql_produccion,
    load_reference,
    mes_label,
    meses_periodo,
    metric_key,
    periodo_filtros,
)


def _report(slug: str, name: str):
    r = MagicMock()
    r.slug = slug
    r.name = name
    r.category = "operational"
    r.version = "1.0.0"
    return r


class BestsoxReferenceFixtureTotalsTest(SimpleTestCase):
    """El fixture JSON reproduce los totales del Excel (sanity del artefacto)."""

    def test_reference_grand_totals(self):
        ref = load_reference()
        prod = ref["produccion"]["total"]
        self.assertEqual(prod["pares"]["total"], 1087464)
        self.assertAlmostEqual(prod["docenas"]["total"], 90622.0, places=2)

        comp = ref["compras"]["total"]
        self.assertEqual(comp["packs"]["total"], 30182)
        self.assertEqual(comp["prendas"]["total"], 34005)
        self.assertAlmostEqual(comp["docenas"]["total"], 2833.75, places=2)

        cons = ref["consignacion"]["total"]
        self.assertEqual(cons["packs"], 696)
        self.assertEqual(cons["prendas"], 1782)
        self.assertAlmostEqual(cons["docenas"], 148.5, places=2)


class BestsoxMarcaReportsReferenceRunnersTest(TestCase):
    def setUp(self):
        self.periodo = periodo_filtros()
        self.meses = meses_periodo()
        self.filters = {
            **self.periodo,
            "base_empresa": "bestsox_fixture",
        }
        self.user = MagicMock(base_empresa="bestsox_fixture")

    @patch("reports.services.produccion_marca_superart_runner.consultar_produccion_marca_superart")
    def test_produccion_totales_marca_y_mes(self, mock_q):
        from reports.services.produccion_marca_superart_runner import run_produccion_marca_superart

        mock_q.return_value = filas_sql_produccion()
        result = run_produccion_marca_superart(
            _report(PRODUCCION_MARCA_SUPERART_SLUG, "Producción"),
            {"filters": self.filters},
            self.user,
        )
        ref = load_reference()["produccion"]
        self.assertEqual(int(result.totals["pares_total"]), ref["total"]["pares"]["total"])
        self.assertAlmostEqual(
            float(result.totals["docenas_total"]),
            ref["total"]["docenas"]["total"],
            places=2,
        )
        by_marca = {
            row["nombre_marca"]: row
            for row in result.meta["extra"]["tabs"]["totales_por_marca"]
        }
        for marca in ref["marcas"]:
            got = by_marca[marca["nombre_marca"]]
            for ym in self.meses:
                with self.subTest(marca=marca["nombre_marca"], ym=ym):
                    self.assertEqual(
                        int(got[metric_key("Pares", ym)]),
                        int(marca["pares"][ym]),
                    )
            self.assertEqual(int(got["Pares_Total"]), int(marca["pares"]["total"]))

    @patch("reports.services.compras_marca_superart_runner.consultar_compras_marca_superart")
    def test_compras_totales_marca_y_mes(self, mock_q):
        from reports.services.compras_marca_superart_runner import run_compras_marca_superart

        mock_q.return_value = filas_sql_compras()
        result = run_compras_marca_superart(
            _report(COMPRAS_MARCA_SUPERART_SLUG, "Compras"),
            {"filters": self.filters},
            self.user,
        )
        ref = load_reference()["compras"]
        self.assertEqual(int(result.totals["packs_total"]), ref["total"]["packs"]["total"])
        self.assertEqual(int(result.totals["prendas_total"]), ref["total"]["prendas"]["total"])
        self.assertAlmostEqual(
            float(result.totals["docenas_total"]),
            ref["total"]["docenas"]["total"],
            places=2,
        )
        by_marca = {
            row["nombre_marca"]: row
            for row in result.meta["extra"]["tabs"]["totales_por_marca"]
        }
        for marca in ref["marcas"]:
            got = by_marca[marca["nombre_marca"]]
            for ym in self.meses:
                with self.subTest(marca=marca["nombre_marca"], ym=ym, metric="packs"):
                    self.assertEqual(
                        int(got[metric_key("Packs", ym)]),
                        int(marca["packs"][ym]),
                    )
            self.assertEqual(int(got["Packs_Total"]), int(marca["packs"]["total"]))

    @patch("reports.services.consignacion_stock_runner.consultar_consignacion_stock")
    def test_consignacion_totales_marca(self, mock_q):
        from reports.services.consignacion_stock_runner import run_consignacion_stock

        filas = filas_sql_consignacion()
        mock_q.return_value = {
            "filas_articulo": filas,
            "remitos": load_reference()["consignacion"]["remitos"],
            "totales": {
                "packs_saldo": sum(r["packs_saldo"] for r in filas),
                "prendas_saldo": sum(r["prendas_saldo"] for r in filas),
                "docenas_saldo": sum(r["docenas_saldo"] for r in filas),
            },
        }
        result = run_consignacion_stock(
            _report(CONSIGNACION_STOCK_SLUG, "Consignación"),
            {"filters": self.filters},
            self.user,
        )
        ref = load_reference()["consignacion"]
        self.assertEqual(int(result.totals["packs_saldo"]), ref["total"]["packs"])
        self.assertEqual(int(result.totals["prendas_saldo"]), ref["total"]["prendas"])
        self.assertAlmostEqual(float(result.totals["docenas_saldo"]), ref["total"]["docenas"], places=2)
        by_marca = {row["nombre_marca"]: row for row in result.meta["extra"]["tabs"]["totales_por_marca"]}
        for marca in ref["marcas"]:
            got = by_marca[marca["nombre_marca"]]
            self.assertEqual(int(got["packs_saldo"]), int(marca["packs"]))
            self.assertEqual(int(got["prendas_saldo"]), int(marca["prendas"]))
            self.assertAlmostEqual(float(got["docenas_saldo"]), float(marca["docenas"]), places=2)


@tag("bestsox_mysql")
class BestsoxMarcaReportsLiveMysqlTest(TestCase):
    """
    Opcional: `BESTSOX_BASE_EMPRESA=...` + pool MySQL Synap.
    SET SESSION TRANSACTION READ ONLY en la conexión del pool (si está configurado).
    """

    def _base(self):
        return (os.environ.get("BESTSOX_BASE_EMPRESA") or "").strip()

    def setUp(self):
        if not self._base():
            self.skipTest("BESTSOX_BASE_EMPRESA no configurada")

    def test_live_produccion_grand_total(self):
        from reports.services.produccion_marca_superart_query import consultar_produccion_marca_superart

        filas = consultar_produccion_marca_superart(
            self._base(),
            meses=meses_periodo(),
            desde_iso=periodo_filtros()["desde"],
            hasta_iso=periodo_filtros()["hasta"],
        )
        ref = load_reference()["produccion"]["total"]
        total_pares = sum(float(r.get("cantidad") or 0) for r in filas)
        self.assertEqual(int(round(total_pares)), int(ref["pares"]["total"]))
