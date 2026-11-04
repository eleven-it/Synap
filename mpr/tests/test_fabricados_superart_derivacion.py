# -*- coding: utf-8 -*-
"""Regla de superartículo fabricados: id_manual, nombre y CSV de referencia (415 filas)."""
import csv
from pathlib import Path

from django.test import SimpleTestCase

from mpr.services_fabricados_superart import (
    SIN_SUPERART_LABEL,
    agrupar_fabricados_por_superart,
    superart_desde_articulo,
    superart_desde_nombre_articulo,
)


class TestSuperartDerivacionUnit(SimpleTestCase):
    def test_id_manual_prioriza_sobre_nombre(self):
        _, cod, _ = superart_desde_articulo("SEPU1025BLFU4", "0966 T4 Puma Blanco/Fucsia 1Par")
        self.assertEqual(cod, "SEPU1025BLFU4")

    def test_placeholder_guion_como_vacio(self):
        _, cod, _ = superart_desde_articulo("-", "2574 T5 Puma Blanco/Negro 1Par")
        self.assertEqual(cod, "2574")

    def test_deriva_desde_nombre_ejemplos_reales(self):
        casos = [
            ("2574 T5 (7312)Puma Blanco/Negro 1Par", "2574"),
            ("8624-02 Kids Flower Quarter 2P", "8624"),
            ("Mateu Fútbol Talle 6", "Mateu"),
            ("3765 T5 Puma Gmel/Negro 1Par", "3765"),
            ("475 Mateu T5 Futbol Negro/Blanco 1Par", "475"),
            ("Bull T4 caña larga Negro/Blanco 1Par", "Bull"),
        ]
        for nombre, esperado in casos:
            with self.subTest(nombre=nombre):
                self.assertEqual(superart_desde_nombre_articulo(nombre), esperado)

    def test_superart_tres_caracteres(self):
        for code in ("510", "251", "508", "991", "797", "715", "709", "609", "610", "509"):
            nombre = f"{code} T4 Puma Test 1Par"
            _, cod, _ = superart_desde_articulo("", nombre)
            self.assertEqual(cod, code)

    def test_id_manual_1025_no_deriva_8624(self):
        _, cod, _ = superart_desde_articulo("1025", "8624 T5 Unisex Sneaker Plain Crudo/Beige 1Par")
        self.assertEqual(cod, "1025")

    def test_agrupacion_case_insensitive(self):
        filas = [
            {"id_articulo": 1, "id_manual": "", "ym": "2026-01", "cantidad": 1},
            {"id_articulo": 2, "id_manual": "", "ym": "2026-01", "cantidad": 2},
        ]
        desc = {
            1: ("A1", "mateu T4 test 1Par"),
            2: ("A2", "Mateu T5 test 1Par"),
        }
        r = agrupar_fabricados_por_superart(filas, ["2026-01"], desc)
        self.assertEqual(len(r["filas_superart"]), 1)
        self.assertEqual(r["filas_superart"][0]["codigo_superart"].lower(), "mateu")
        self.assertEqual(r["total_general"], 3.0)

    def test_filtro_por_superart_derivado(self):
        filas = [
            {"id_articulo": 812, "id_manual": "", "ym": "2026-08", "cantidad": 10},
            {"id_articulo": 817, "id_manual": "", "ym": "2026-08", "cantidad": 5},
        ]
        desc = {
            812: ("812", "2574 T5 (7312)Puma Blanco/Negro 1Par"),
            817: ("817", "2576 T5 (6512)Puma Blanco/Negro 1Par"),
        }
        r = agrupar_fabricados_por_superart(
            filas,
            ["2026-08"],
            desc,
            superarts_incluidos=["2574"],
        )
        self.assertEqual(len(r["filas_superart"]), 1)
        self.assertEqual(r["filas_superart"][0]["codigo_superart"], "2574")
        self.assertEqual(r["total_general"], 10.0)

    def test_sin_superart_si_nombre_vacio(self):
        _, _, label = superart_desde_articulo("", "")
        self.assertEqual(label, SIN_SUPERART_LABEL)


class TestReferenciaSuperart415Csv(SimpleTestCase):
    """Mesa de la regla contra referencia_superart_415.csv (415/415)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = Path(__file__).resolve().parent / "fixtures" / "referencia_superart_415.csv"
        cls.rows = []
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                cls.rows.append(row)

    def test_415_lineas_coinciden_con_superart_esperado(self):
        self.assertEqual(len(self.rows), 415)
        mismatches = []
        for row in self.rows:
            _, cod, _ = superart_desde_articulo(
                row.get("id_manual") or "",
                row.get("NombreArticulo") or "",
            )
            esperado = (row.get("superart_esperado") or "").strip()
            if cod != esperado:
                mismatches.append(
                    (row.get("IDArt"), row.get("id_manual"), row.get("NombreArticulo"), cod, esperado)
                )
        self.assertEqual(mismatches, [], msg=f"Primeras diferencias: {mismatches[:5]}")
