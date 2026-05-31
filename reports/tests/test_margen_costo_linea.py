"""Tests de costo por renglón (paridad informe rentabilidad AdministraNET)."""
from django.test import SimpleTestCase

from reports.services.margen_costo_linea import (
    costo_linea_precio_costoxr_python,
    margen_costo_criterio_meta,
)


class MargenCostoLineaTests(SimpleTestCase):
    def test_usa_precio_costoxr_sin_escala(self):
        """Display/Bulto/Unidad: costo = valor persistido en renglón."""
        self.assertEqual(
            costo_linea_precio_costoxr_python(precio_costoxr=682.38),
            682.38,
        )
        self.assertEqual(
            costo_linea_precio_costoxr_python(precio_costoxr=11085.16),
            11085.16,
        )
        self.assertEqual(
            costo_linea_precio_costoxr_python(precio_costoxr=0.0),
            0.0,
        )

    def test_margen_costo_criterio_meta(self):
        self.assertEqual(margen_costo_criterio_meta(), "precio_costoxr_linea")
