# -*- coding: utf-8 -*-
"""Tests unitarios: Ventas BOM en docenas (explosión, signos, export)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from reports.services.ventas_bom_docenas_rules import (
    VENTAS_BOM_DOCENAS_SLUG,
    docenas_desde_pares,
    explode_pack_qty_to_components,
)
from reports.services.ventas_bom_docenas_runner import (
    aggregate_bom_from_packs,
    build_result_rows,
)
from reports.services.export_service import ExportService


class ExplodeBomTests(TestCase):
    def test_explode_pack_qty_multiplies_bom(self):
        comps = [
            {"id_articulo": 101, "cantidad_articulo": 2},
            {"id_articulo": 102, "cantidad_articulo": 1},
        ]
        out = explode_pack_qty_to_components(10, comps)
        self.assertEqual(out[101], 20.0)
        self.assertEqual(out[102], 10.0)

    def test_explode_negative_qty_for_nc(self):
        comps = [{"id_articulo": 101, "cantidad_articulo": 2}]
        out = explode_pack_qty_to_components(-5, comps)
        self.assertEqual(out[101], -10.0)

    def test_docenas_divisor_12(self):
        self.assertEqual(docenas_desde_pares(24), 2.0)
        self.assertEqual(docenas_desde_pares(20), 1.67)
        self.assertEqual(docenas_desde_pares(10), 0.83)


class AggregateBomTests(TestCase):
    def test_aggregate_and_omit_packs_without_bom(self):
        pack_rows = [
            {"id_en_abm": 1, "qty_pack": 10},
            {"id_en_abm": 2, "qty_pack": 3},
        ]
        bom = {
            1: [
                {"id_articulo": 201, "cantidad_articulo": 2},
                {"id_articulo": 202, "cantidad_articulo": 1},
            ]
        }
        pares, omitidos = aggregate_bom_from_packs(pack_rows, bom)
        self.assertEqual(omitidos, 1)
        self.assertEqual(pares[201], 20.0)
        self.assertEqual(pares[202], 10.0)

    def test_fa_minus_nc(self):
        pack_rows = [
            {"id_en_abm": 1, "qty_pack": 10},
            {"id_en_abm": 1, "qty_pack": -2},
        ]
        bom = {1: [{"id_articulo": 9, "cantidad_articulo": 3}]}
        pares, omitidos = aggregate_bom_from_packs(pack_rows, bom)
        self.assertEqual(omitidos, 0)
        self.assertEqual(pares[9], 24.0)
        self.assertEqual(docenas_desde_pares(pares[9]), 2.0)

    def test_build_result_rows_sorted_by_docenas(self):
        pares = {1: 12.0, 2: 36.0}
        meta = {
            1: {
                "id_art": 1,
                "codigo_articulo": "A1",
                "nombre_articulo": "Comp A",
                "codigo_marca": 1,
                "nombre_marca": "M1",
            },
            2: {
                "id_art": 2,
                "codigo_articulo": "B1",
                "nombre_articulo": "Comp B",
                "codigo_marca": 2,
                "nombre_marca": "M2",
            },
        }
        rows = build_result_rows(pares, meta)
        self.assertEqual(rows[0]["id_art"], 2)
        self.assertEqual(rows[0]["docenas"], 3.0)
        self.assertEqual(rows[1]["pares"], 12.0)


class ExportVentasBomTests(TestCase):
    def test_filename_uses_dates(self):
        svc = ExportService(user=SimpleNamespace())
        name = svc._resolve_export_filename(
            VENTAS_BOM_DOCENAS_SLUG,
            {
                "filters": {
                    "fecha_inicio_facturacion": "2026-03-01",
                    "fecha_fin_facturacion": "2026-03-31",
                }
            },
            "20260313_120000",
        )
        self.assertEqual(name, "Ventas_BOM_docenas_01032026_31032026.xlsx")

    def test_export_headers_order(self):
        svc = ExportService(user=SimpleNamespace())
        report = SimpleNamespace(slug=VENTAS_BOM_DOCENAS_SLUG, config={})
        headers = svc._resolve_export_headers(
            report,
            {
                "id_art": 1,
                "codigo_articulo": "X",
                "nombre_articulo": "Art",
                "nombre_marca": "M",
                "pares": 12,
                "docenas": 1,
            },
        )
        self.assertEqual(
            headers,
            ["codigo_articulo", "nombre_articulo", "nombre_marca", "pares", "docenas"],
        )


class RunnerMissingBaseTests(TestCase):
    def test_missing_base_empresa_returns_note(self):
        from reports.services.ventas_bom_docenas_runner import run_ventas_bom_docenas

        report = SimpleNamespace(
            slug=VENTAS_BOM_DOCENAS_SLUG,
            name="Ventas BOM en docenas",
            category="operational",
            version="1.0.0",
        )
        with patch("reports.services.ventas_bom_docenas_runner.get_mysql_pool") as pool:
            result = run_ventas_bom_docenas(
                report,
                {
                    "filters": {
                        "fecha_inicio_facturacion": "2026-03-01",
                        "fecha_fin_facturacion": "2026-03-31",
                    }
                },
                user=None,
            )
            pool.assert_not_called()
        self.assertEqual(result.data, [])
        self.assertTrue(any("base de datos" in n.lower() for n in result.notes))


class SeedDefaultsTests(TestCase):
    def test_seed_defaults_slug_and_metrics(self):
        from reports.services.ventas_bom_docenas_seed import _report_defaults

        defaults = _report_defaults()
        self.assertEqual(defaults["name"], "Ventas BOM en docenas")
        self.assertIn("docenas", defaults["config"]["metrics"])
        self.assertEqual(defaults["category"], "operational")
        self.assertIn("fecha_inicio_facturacion", defaults["config"]["filters"])
