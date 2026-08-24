"""Tests unidad de empaquetado (múltiplo de venta)."""

from decimal import Decimal

from django.test import SimpleTestCase

from ecom.services.multiplo_empaque import (
    campos_multiplo_articulo,
    cantidad_respeta_multiplo,
    disponible_unidades_a_packs,
    multiplo_empaque_venta,
)


class TestMultiploEmpaqueVenta(SimpleTestCase):
    def test_doce_sobre_seis_ok(self):
        self.assertTrue(cantidad_respeta_multiplo(12, 6))

    def test_siete_sobre_seis_fail(self):
        self.assertFalse(cantidad_respeta_multiplo(7, 6))

    def test_multiplo_uno_siempre_ok(self):
        self.assertTrue(cantidad_respeta_multiplo(7, 1))
        self.assertEqual(multiplo_empaque_venta(1), 1)
        self.assertEqual(multiplo_empaque_venta(6), 6)

    def test_cero_o_null_devuelve_uno(self):
        self.assertEqual(multiplo_empaque_venta(None), 1)
        self.assertEqual(multiplo_empaque_venta(0), 1)
        self.assertTrue(cantidad_respeta_multiplo(0, 6))
        self.assertTrue(cantidad_respeta_multiplo("", 6))

    def test_solo_multiplo_cantidad_vta(self):
        self.assertEqual(multiplo_empaque_venta(6), 6)
        campos = campos_multiplo_articulo(6)
        self.assertEqual(campos["multiplo_empaque"], 6)
        self.assertEqual(campos["multiplo_cantidad_vta"], 6)
        self.assertNotIn("multiplo_vta", campos)

    def test_decimal_como_cantidad(self):
        self.assertTrue(cantidad_respeta_multiplo(Decimal("12"), 6))
        self.assertFalse(cantidad_respeta_multiplo(Decimal("2.5"), 6))

    def test_disponible_unidades_a_packs(self):
        self.assertEqual(disponible_unidades_a_packs(0, 6), 0.0)
        self.assertEqual(disponible_unidades_a_packs(24, 6), 4.0)
        self.assertEqual(disponible_unidades_a_packs(25, 6), 4.0)
        self.assertEqual(disponible_unidades_a_packs(10, None), 10.0)
