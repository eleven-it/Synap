"""Tests reporte_mpr_trazabilidad_componente."""

from django.test import SimpleTestCase

from mpr.services import reporte_mpr_trazabilidad_componente


class TestReporteMprTrazabilidad(SimpleTestCase):
    def test_sin_articulo(self):
        r = reporte_mpr_trazabilidad_componente("empresa92", None)
        self.assertEqual(r["eventos"], [])
