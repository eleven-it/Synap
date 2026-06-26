"""Tests — extracción de campos producto TN desde variante."""

from django.test import SimpleTestCase

from tiendanube_administranet.services.tiendanube_product_fields import (
    resolver_campos_producto_tiendanube,
)


class TiendanubeProductFieldsTests(SimpleTestCase):
    def test_extrae_precio_stock_handle_desde_variante(self):
        tn_product = {
            'id': 349639384,
            'name': {'es': 'Artículo de prueba'},
            'handle': 'articulo-de-prueba',
            'published': True,
            'product_type': 'physical',
            'variants': [
                {
                    'id': 1,
                    'sku': '530003134',
                    'price': 1829.99,
                    'cost': 1238.77,
                    'inventory_levels': [{'stock': 218}],
                }
            ],
        }
        campos = resolver_campos_producto_tiendanube(tn_product)

        self.assertEqual(campos['tiendanube_handle'], 'articulo-de-prueba')
        self.assertEqual(campos['tiendanube_name'], 'Artículo de prueba')
        self.assertEqual(campos['tiendanube_price'], 1829.99)
        self.assertEqual(campos['tiendanube_cost'], 1238.77)
        self.assertEqual(campos['tiendanube_stock'], 218)
        self.assertEqual(campos['tiendanube_sku'], '530003134')

    def test_stock_desde_campo_variante(self):
        campos = resolver_campos_producto_tiendanube({
            'name': 'Simple',
            'variants': [{'price': 10, 'stock': 5}],
        })
        self.assertEqual(campos['tiendanube_stock'], 5)
