"""Tests — tabla comparativa producto Adminet ↔ TN."""

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from tiendanube_administranet.services.product_comparison import (
    filas_comparacion_producto,
    resumen_comparacion_producto,
)
from tiendanube_administranet.services.tiendanube_product_fields import (
    resolver_campos_producto_tiendanube,
)


class HandleTiendanubeTests(SimpleTestCase):
    def test_handle_dict_se_normaliza(self):
        campos = resolver_campos_producto_tiendanube({
            'name': {'es': 'Artículo'},
            'handle': {'es': 'articulo-ejemplo'},
            'variants': [{'price': 10, 'stock': 1}],
        })
        self.assertEqual(campos['tiendanube_handle'], 'articulo-ejemplo')


class FilasComparacionTests(SimpleTestCase):
    def _mapping_alineado(self):
        m = MagicMock()
        m.tiendanube_id = 100
        m.adminet_id = 3134
        m.tiendanube_name = 'Producto X'
        m.adminet_nombre = 'Producto X'
        m.tiendanube_sku = '530003134'
        m.adminet_codigo_barra = '530003134'
        m.adminet_codigo_articulo = '17.0.1'
        m.tiendanube_handle = 'producto-x'
        m.tiendanube_price = 1829.99
        m.tiendanube_cost = 1238.77
        m.tiendanube_stock = 218
        m.adminet_stock = 218
        m.tiendanube_published = True
        m.adminet_ecommerce = 'Si'
        m.tiendanube_featured = False
        m.adminet_promo_destacado = 'No'
        m.tiendanube_product_type = 'physical'
        m.tiendanube_weight = 0
        m.adminet_precio_venta_final = 1829.9901
        m.adminet_costo_final = 1238.7690
        m.adminet_precio_costo = 1023.7760
        m.adminet_precio_4v = 1512.3885
        return m

    def test_precios_y_stock_coinciden(self):
        filas = filas_comparacion_producto(self._mapping_alineado())
        resumen = resumen_comparacion_producto(filas)
        precio = next(f for f in filas if f['label'] == 'Precio de venta (final)')
        stock = next(f for f in filas if f['label'] == 'Stock')
        self.assertEqual(precio['estado'], 'ok')
        self.assertEqual(stock['estado'], 'ok')
        self.assertGreaterEqual(resumen['coinciden'], 4)

    def test_costo_distinto_marca_diff(self):
        m = self._mapping_alineado()
        m.tiendanube_cost = 1023.78
        filas = filas_comparacion_producto(m)
        costo = next(f for f in filas if f['label'] == 'Costo (final)')
        self.assertEqual(costo['estado'], 'diff')
