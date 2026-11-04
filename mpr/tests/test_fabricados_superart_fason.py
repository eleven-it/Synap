# -*- coding: utf-8 -*-
"""Fasón Tejeduría S y M + mesa de referencia producción Ago–Oct 2026."""
import csv
from collections import defaultdict
from pathlib import Path

from django.test import SimpleTestCase

from mpr.services_fabricados_superart import agrupar_fabricados_por_superart, merge_filas_fabricado_y_fason

FIXTURES = Path(__file__).resolve().parent / "fixtures"
# referencia_produccion_415.csv: pares Ago/Sep/Oct/Total del Excel Producción (415 filas);
# superart_esperado alineado a referencia_superart_415.csv (regla id_manual/nombre).
MESES_REF = ["2026-08", "2026-09", "2026-10"]
FASON_OCT_2026 = {
    1419: 4871,
    1421: 3886,
    1542: 2485,
    1543: 2400,
    1546: 2000,
    1547: 2416,
}


def _load_produccion_415():
    path = FIXTURES / "referencia_produccion_415.csv"
    rows = []
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(row)
    return rows


def _load_id_manual_por_art():
    path = FIXTURES / "referencia_superart_415.csv"
    out = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[int(row["IDArt"])] = (row.get("id_manual") or "").strip()
    return out


class TestReferenciaProduccion415ConFason(SimpleTestCase):
    """415 artículos MPR simulados + deltas fasón Oct → totales del workbook de Producción."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.detalle = _load_produccion_415()
        cls.id_manual_map = _load_id_manual_por_art()
        cls.esperado_por_superart = defaultdict(lambda: {"por_mes": {m: 0.0 for m in MESES_REF}, "total": 0.0})
        for row in cls.detalle:
            sa = (row.get("superart_esperado") or "").strip()
            cls.esperado_por_superart[sa]["por_mes"]["2026-08"] += float(row.get("Ago2026") or 0)
            cls.esperado_por_superart[sa]["por_mes"]["2026-09"] += float(row.get("Sep2026") or 0)
            cls.esperado_por_superart[sa]["por_mes"]["2026-10"] += float(row.get("Oct2026") or 0)
            cls.esperado_por_superart[sa]["total"] += float(row.get("Total") or 0)

    def _filas_mpr_y_fason_desde_fixture(self):
        filas_mpr = []
        filas_fason = []
        for row in self.detalle:
            aid = int(row["IDArt"])
            manual = self.id_manual_map.get(aid, "")
            nombre = row.get("NombreArticulo") or ""
            mes_vals = [
                ("2026-08", float(row.get("Ago2026") or 0)),
                ("2026-09", float(row.get("Sep2026") or 0)),
                ("2026-10", float(row.get("Oct2026") or 0)),
            ]
            for ym, qty in mes_vals:
                if qty <= 0:
                    continue
                mpr_qty = qty
                if ym == "2026-10" and aid in FASON_OCT_2026:
                    fason_qty = FASON_OCT_2026[aid]
                    filas_fason.append(
                        {
                            "id_articulo": aid,
                            "id_manual": manual,
                            "ym": ym,
                            "cantidad": float(fason_qty),
                        }
                    )
                    mpr_qty = qty - fason_qty
                if mpr_qty > 0:
                    filas_mpr.append(
                        {
                            "id_articulo": aid,
                            "id_manual": manual,
                            "ym": ym,
                            "cantidad": float(mpr_qty),
                        }
                    )
        return filas_mpr, filas_fason

    def test_referencia_workbook_100_superarts_y_totales(self):
        self.assertEqual(len(self.detalle), 415)
        filas_mpr, filas_fason = self._filas_mpr_y_fason_desde_fixture()
        merged = merge_filas_fabricado_y_fason(filas_mpr, filas_fason)
        desc_map = {
            int(r["IDArt"]): (str(r["IDArt"]), r.get("NombreArticulo") or "")
            for r in self.detalle
        }
        r = agrupar_fabricados_por_superart(merged, MESES_REF, desc_map)
        self.assertEqual(len(r["filas_superart"]), 100)
        self.assertEqual(r["totales_por_mes"]["2026-08"], 341232.0)
        self.assertEqual(r["totales_por_mes"]["2026-09"], 356251.0)
        self.assertEqual(r["totales_por_mes"]["2026-10"], 389981.0)
        self.assertEqual(r["total_general"], 1087464.0)

        obtenido = {
            sa["codigo_superart"]: sa for sa in r["filas_superart"]
        }
        self.assertEqual(set(obtenido.keys()), set(self.esperado_por_superart.keys()))
        diffs = []
        for cod, exp in self.esperado_por_superart.items():
            got = obtenido.get(cod)
            if not got:
                diffs.append((cod, "missing", exp["total"]))
                continue
            if got["total"] != exp["total"]:
                diffs.append((cod, got["total"], exp["total"]))
            for m in MESES_REF:
                if got["por_mes"].get(m) != exp["por_mes"][m]:
                    diffs.append((cod, m, got["por_mes"].get(m), exp["por_mes"][m]))
        self.assertEqual(diffs, [], msg=f"Primeras diferencias: {diffs[:5]}")
