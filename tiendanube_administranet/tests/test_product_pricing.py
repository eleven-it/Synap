"""Tests precios finales Adminet → Tiendanube."""

from decimal import Decimal

from django.test import SimpleTestCase

from tiendanube_administranet.services.automatic_mapping_service import (
    AutomaticMappingService,
)
from unittest.mock import MagicMock

from tiendanube_administranet.services.product_pricing import (
    LISTA_PRECIO_TN_DEFAULT,
    costo_final_articulo,
    precio_venta_final_articulo,
    precios_finales_desde_product_mapping,
    precios_tiendanube_desde_articulo,
)


# Artículo 3134 — CAR.MAST.BERBAU (valores reales administranet74)
ART_3134 = {
    'PrecioCosto': Decimal('1023.7760'),
    'Precio4V': Decimal('1512.3885'),
    'Precio4VI': Decimal('1829.9901'),
    'Precio1V': Decimal('1429.7441'),
    'Precio1VI': Decimal('1729.9904'),
}


class PreciosFinalesArticuloTests(SimpleTestCase):
    def test_lista_web_precio_final(self):
        self.assertAlmostEqual(
            precio_venta_final_articulo(ART_3134, LISTA_PRECIO_TN_DEFAULT),
            1829.9901,
            places=2,
        )

    def test_lista_web_costo_final(self):
        self.assertAlmostEqual(
            costo_final_articulo(ART_3134, LISTA_PRECIO_TN_DEFAULT),
            1238.7690,
            places=2,
        )

    def test_no_usa_precio1v_neto(self):
        precios = precios_tiendanube_desde_articulo(ART_3134)
        self.assertNotAlmostEqual(precios['price'], 1429.74, places=1)
        self.assertAlmostEqual(precios['price'], 1829.99, places=1)

    def test_mapper_envia_precios_finales(self):
        svc = AutomaticMappingService()
        data = svc.map_adminet_to_tiendanube_product(
            {
                'NombreArticulo': 'Art',
                'NroCodBarra': 'SKU1',
                'ecommerce': 'Si',
                'stock_deposito': 5,
                **ART_3134,
            },
            deposito_id=3,
        )
        variant = data['variants'][0]
        self.assertAlmostEqual(variant['price'], 1829.9901, places=2)
        self.assertAlmostEqual(variant['cost'], 1238.7690, places=2)


class PreciosFinalesMappingTests(SimpleTestCase):
    def test_usa_campos_finales_persistidos(self):
        mapping = MagicMock()
        mapping.adminet_precio_venta_final = 1829.9901
        mapping.adminet_costo_final = 1238.7690
        mapping.adminet_precio_costo = ART_3134['PrecioCosto']
        mapping.adminet_precio_4v = ART_3134['Precio4V']
        precios = precios_finales_desde_product_mapping(mapping)
        self.assertAlmostEqual(precios['precio_venta'], 1829.9901, places=2)
        self.assertAlmostEqual(precios['costo'], 1238.7690, places=2)
