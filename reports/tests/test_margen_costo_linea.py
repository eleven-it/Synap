"""Tests de normalización de costo por renglón (Display/Bulto/Unidad)."""
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.margen_costo_linea import (
    costo_linea_normalizado_python,
    fetch_utiliza_embalaje_display_bulto,
    margen_costo_criterio_meta,
)


class MargenCostoLineaTests(SimpleTestCase):
    def test_unidad_precio_costoxu_escala_por_cantidad_base(self):
        """PrecioCostoxU por unidad física cuando cantidad_dividir=1."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=10.0,
                precio_costoxr=50.0,
                cantidad=5.0,
                tipo_unidad="Unidad",
                cantidad_dividir=1.0,
            ),
            50.0,
        )

    def test_unidad_fraccionada_usa_cantidad_unidad_display(self):
        """2 alfajores sueltos (TPV): dividir=1, display=24 en stock."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=5542.58,
                precio_costoxr=11085.16,
                cantidad=2.0,
                tipo_unidad="Unidad",
                cantidad_dividir=1.0,
                cantidad_unidad_display=24.0,
            ),
            5542.58 * 2 / 24,
            places=2,
        )

    def test_unidad_fraccionada_con_dividir_en_stock(self):
        """5 unidades de caja 24 cuando cantidad_dividir persiste en stock."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=5542.58,
                precio_costoxr=27712.9,
                cantidad=5.0,
                tipo_unidad="Unidad",
                cantidad_dividir=24.0,
            ),
            5542.58 * 5 / 24,
            places=2,
        )

    def test_unidad_sin_precio_costoxu_usa_renglon(self):
        self.assertEqual(
            costo_linea_normalizado_python(
                precio_costoxu=0.0,
                precio_costoxr=80.0,
                cantidad=8.0,
                tipo_unidad="Unidad",
            ),
            80.0,
        )

    def test_display_tpv_dividir_uno_usa_precio_costoxr(self):
        """Excepción TPV: Display con cantidad_dividir=1 y display=1."""
        self.assertEqual(
            costo_linea_normalizado_python(
                precio_costoxu=35.0,
                precio_costoxr=70.0,
                cantidad=2.0,
                tipo_unidad="Display",
                cantidad_dividir=1.0,
                cantidad_unidad_display=1.0,
            ),
            70.0,
        )

    def test_display_caja_completa_costo_empaque(self):
        """1 caja (24 u): Cantidad=24, costo = costo_caja × 24/24."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=5542.58,
                precio_costoxr=5542.58,
                cantidad=24.0,
                tipo_unidad="Display",
                cantidad_dividir=24.0,
                cantidad_unidad_display=24.0,
            ),
            5542.58,
            places=2,
        )

    def test_display_dos_empaques(self):
        """2 displays de 12 u: costo = 10 × 24/12 = 20."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=10.0,
                precio_costoxr=20.0,
                cantidad=24.0,
                tipo_unidad="Display",
                cantidad_dividir=12.0,
            ),
            20.0,
        )

    def test_display_sin_u_usa_precio_costoxr(self):
        self.assertEqual(
            costo_linea_normalizado_python(
                precio_costoxu=0.0,
                precio_costoxr=20.0,
                cantidad=24.0,
                tipo_unidad="Display",
                cantidad_dividir=12.0,
            ),
            20.0,
        )

    def test_bizcocho_venta_empaque_completo(self):
        """Bizcocho Don Satur (30): venta de 1 empaque con dividir=1 en TPV."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=682.38,
                precio_costoxr=682.38,
                cantidad=1.0,
                tipo_unidad="Unidad",
                cantidad_dividir=1.0,
                cantidad_unidad_display=1.0,
                multiplicador_comp=30.0,
            ),
            682.38,
            places=2,
        )

    def test_polvorita_caja_completa(self):
        """Polvorita (40): venta de 1 caja como unidad comercial."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=273.28,
                precio_costoxr=273.28,
                cantidad=1.0,
                tipo_unidad="Unidad",
                cantidad_dividir=1.0,
                cantidad_unidad_display=1.0,
                multiplicador_comp=40.0,
            ),
            273.28,
            places=2,
        )

    def test_bulto_escala_por_multiplicador_comp(self):
        """PrecioCostoxU en VB6 incluye multiplicador_comp; Cantidad en base."""
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=240.0,
                precio_costoxr=240.0,
                cantidad=288.0,
                tipo_unidad="Bulto",
                cantidad_dividir=288.0,
                multiplicador_comp=24.0,
            ),
            2880.0,
        )

    def test_bulto_sin_u_usa_precio_costoxr(self):
        self.assertEqual(
            costo_linea_normalizado_python(
                precio_costoxu=0.0,
                precio_costoxr=500.0,
                cantidad=120.0,
                tipo_unidad="Bulto",
                cantidad_dividir=12.0,
            ),
            500.0,
        )

    def test_sin_embalaje_usa_precio_costoxu_por_cantidad(self):
        self.assertAlmostEqual(
            costo_linea_normalizado_python(
                precio_costoxu=12.0,
                precio_costoxr=999.0,
                cantidad=4.0,
                utiliza_embalaje_display_bulto=False,
            ),
            48.0,
        )

    def test_sin_embalaje_sin_u_usa_precio_costoxr(self):
        self.assertEqual(
            costo_linea_normalizado_python(
                precio_costoxu=0.0,
                precio_costoxr=80.0,
                cantidad=3.0,
                utiliza_embalaje_display_bulto=False,
            ),
            80.0,
        )

    def test_fetch_utiliza_embalaje_display_bulto_si(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("Si", "No", "Si")
        self.assertTrue(fetch_utiliza_embalaje_display_bulto(cursor))

    def test_fetch_utiliza_embalaje_display_bulto_no(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("No", "Si", "Si")
        self.assertFalse(fetch_utiliza_embalaje_display_bulto(cursor))

    def test_margen_costo_criterio_meta(self):
        self.assertEqual(
            margen_costo_criterio_meta(True),
            "costo_empaque_escala_cantidad_dividir",
        )
        self.assertEqual(
            margen_costo_criterio_meta(False),
            "costo_unitario_precio_costoxu_cantidad",
        )
