# -*- coding: utf-8 -*-
from django.test import SimpleTestCase

from reports.services.articulo_pack_unidades import (
    docenas_desde_prendas,
    prendas_desde_packs,
    unidades_por_pack_compras,
)


class ArticuloPackUnidadesTests(SimpleTestCase):
    def test_p6_pack_units(self):
        self.assertEqual(unidades_por_pack_compras("P6"), 6.0)
        self.assertEqual(prendas_desde_packs(2, 6), 12.0)
        self.assertEqual(docenas_desde_prendas(12), 1.0)

    def test_suffix_2u_from_name(self):
        name = "37453-M001 L Levis BW Men Solid Bsaic Boxer Negro 2U"
        self.assertEqual(unidades_por_pack_compras("Unidad", nombre_articulo=name), 2.0)
        self.assertEqual(prendas_desde_packs(502, 2), 1004.0)
        self.assertAlmostEqual(docenas_desde_prendas(1004), 83.6667, places=3)

    def test_suffix_3p_from_name(self):
        name = "880966-05 T4 Puma Invisible Sneaker Bl/Bl/Fu 3P"
        self.assertEqual(unidades_por_pack_compras("", nombre_articulo=name), 3.0)
        self.assertEqual(prendas_desde_packs(6, 3), 18.0)
