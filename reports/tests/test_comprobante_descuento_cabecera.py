# -*- coding: utf-8 -*-
"""Tests factor descuento al pie de cabecera (compartido VMM/DABRA)."""

from decimal import Decimal

from django.test import SimpleTestCase

from reports.services.comprobante_descuento_cabecera import (
    factor_descuento_cabecera,
    porcentaje_descuento_cabecera,
    sql_factor_descuento_cabecera_expr,
)
from reports.services.ventas_marcas_mensual_rules import (
    sql_signo_imp_expr,
    sql_signo_imp_post_pie_expr,
)


class FactorDescuentoCabeceraTest(SimpleTestCase):
    def test_sin_pie_factor_uno(self):
        self.assertEqual(factor_descuento_cabecera(Decimal("1000"), Decimal("1000")), Decimal("1"))
        self.assertEqual(factor_descuento_cabecera(Decimal("1000"), None), Decimal("1"))

    def test_dto_pie_20_pct(self):
        self.assertEqual(factor_descuento_cabecera(Decimal("1000"), Decimal("800")), Decimal("0.8"))
        self.assertEqual(
            porcentaje_descuento_cabecera(Decimal("1000"), Decimal("800")),
            Decimal("20"),
        )

    def test_subtotal1_cero_factor_uno(self):
        self.assertEqual(factor_descuento_cabecera(Decimal("0"), Decimal("800")), Decimal("1"))
        self.assertEqual(factor_descuento_cabecera(0, 0), Decimal("1"))

    def test_caso_dabra_julio_2026(self):
        self.assertEqual(
            factor_descuento_cabecera(Decimal("2625038.40"), Decimal("2100030.72")),
            Decimal("0.8"),
        )


class SqlFactorDescuentoCabeceraExprTest(SimpleTestCase):
    def test_expr_contiene_case_coalesce_y_epsilon(self):
        expr = sql_factor_descuento_cabecera_expr()
        self.assertIn("CASE", expr)
        self.assertIn("COALESCE(cc.SubtotalDesc", expr)
        self.assertIn("0.0001", expr)
        self.assertIn("cc.SubTotal1", expr)

    def test_expr_parametrizable(self):
        expr = sql_factor_descuento_cabecera_expr("cab.SubTotal1", "cab.SubtotalDesc")
        self.assertIn("cab.SubTotal1", expr)
        self.assertIn("cab.SubtotalDesc", expr)


class SqlSignoImpPostPieExprTest(SimpleTestCase):
    def test_expr_vieja_sin_subtotal_cabecera(self):
        expr = sql_signo_imp_expr()
        self.assertNotIn("SubTotal1", expr)
        self.assertNotIn("SubtotalDesc", expr)

    def test_expr_post_pie_incluye_factor_cabecera(self):
        expr = sql_signo_imp_post_pie_expr()
        self.assertIn("PrecioNetoxR", expr)
        self.assertIn("SubTotal1", expr)
        self.assertIn("SubtotalDesc", expr)
        self.assertIn("0.0001", expr)
        self.assertIn("CASE", expr)
