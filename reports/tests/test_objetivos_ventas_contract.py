# -*- coding: utf-8 -*-
"""Tests del contrato puro objetivos de venta (sin MySQL)."""

from datetime import date
from decimal import Decimal
import unittest

from reports.services.objetivos_ventas_contract import (
    calcular_falta,
    calcular_total_facturacion_remitos,
    objetivo_para_informe,
    periodos_solapan,
)


class TestPeriodosSolapan(unittest.TestCase):
    def test_solapan_parcial(self):
        self.assertTrue(
            periodos_solapan(
                date(2026, 1, 1),
                date(2026, 1, 31),
                date(2026, 1, 15),
                date(2026, 2, 15),
            )
        )

    def test_no_solapan_adyacentes(self):
        # [1-31 ene] y [1 feb - 28 feb] comparten frontera 31/1-1/2 → en inclusive, 1 feb inicio no solapa con fin 31 ene... fecha_hasta_a=31 ene, fecha_desde_b=1 feb → 1 feb <= 31 ene is False. Good.
        self.assertFalse(
            periodos_solapan(
                date(2026, 1, 1),
                date(2026, 1, 31),
                date(2026, 2, 1),
                date(2026, 2, 28),
            )
        )

    def test_solapan_un_dia_comun(self):
        self.assertTrue(
            periodos_solapan(
                date(2026, 1, 10),
                date(2026, 1, 10),
                date(2026, 1, 10),
                date(2026, 1, 10),
            )
        )

    def test_contenido(self):
        self.assertTrue(
            periodos_solapan(
                date(2026, 1, 1),
                date(2026, 12, 31),
                date(2026, 3, 1),
                date(2026, 3, 31),
            )
        )


class TestCalcularFaltaYTotal(unittest.TestCase):
    def test_falta_regla_acordada(self):
        self.assertEqual(
            calcular_falta(Decimal("1000"), Decimal("400"), Decimal("100")),
            Decimal("500"),
        )

    def test_falta_con_cero_objetivo(self):
        self.assertEqual(
            calcular_falta(0, 100, 50),
            Decimal("-150"),
        )

    def test_total_facturacion_remitos(self):
        self.assertEqual(
            calcular_total_facturacion_remitos(400, 100),
            Decimal("500"),
        )


class TestObjetivoParaInforme(unittest.TestCase):
    def test_sin_solape_devuelve_cero(self):
        self.assertEqual(
            objetivo_para_informe(
                Decimal("999"),
                date(2026, 2, 1),
                date(2026, 2, 28),
                date(2026, 1, 1),
                date(2026, 1, 31),
            ),
            Decimal("0"),
        )

    def test_con_solape_devuelve_importe(self):
        self.assertEqual(
            objetivo_para_informe(
                Decimal("1200"),
                date(2026, 1, 1),
                date(2026, 1, 31),
                date(2026, 1, 15),
                date(2026, 2, 15),
            ),
            Decimal("1200"),
        )


if __name__ == "__main__":
    unittest.main()
