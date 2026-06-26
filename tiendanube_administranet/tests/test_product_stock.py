"""Tests stock artículo × depósito para Tiendanube."""

from django.test import SimpleTestCase

from tiendanube_administranet.services.automatic_mapping_service import (
    AutomaticMappingService,
)
from tiendanube_administranet.services.product_stock import (
    stock_unidades_articulo_deposito,
)


class StockUnidadesArticuloDepositoTests(SimpleTestCase):
    def test_usa_stock_deposito_menos_reserva(self):
        self.assertEqual(
            stock_unidades_articulo_deposito(
                {'stock_deposito': 12, 'stock_pedido_cliente': 2, 'IDArt': 1},
                deposito_id=3,
            ),
            10,
        )

    def test_sin_fila_deposito_es_cero(self):
        self.assertEqual(
            stock_unidades_articulo_deposito({'IDArt': 1}, deposito_id=3),
            0,
        )

    def test_requiere_deposito(self):
        with self.assertRaises(ValueError):
            stock_unidades_articulo_deposito({'stock_deposito': 5}, deposito_id=None)

    def test_no_negativo(self):
        self.assertEqual(
            stock_unidades_articulo_deposito({'stock_deposito': -2}, deposito_id=1),
            0,
        )


class MapAdminetToTiendanubeProductStockTests(SimpleTestCase):
    def test_mapper_publica_stock_deposito(self):
        svc = AutomaticMappingService()
        data = svc.map_adminet_to_tiendanube_product(
            {
                'NombreArticulo': 'Art',
                'Precio4V': 100,
                'Precio4VI': 121,
                'PrecioCosto': 50,
                'NroCodBarra': 'SKU1',
                'ecommerce': 'Si',
                'stock_deposito': 7,
                'saldo_articulo': 99,
            },
            deposito_id=5,
        )
        self.assertEqual(data['variants'][0]['stock'], 7)

    def test_mapper_resta_reserva_deposito(self):
        svc = AutomaticMappingService()
        data = svc.map_adminet_to_tiendanube_product(
            {
                'NombreArticulo': 'Art',
                'Precio4V': 100,
                'Precio4VI': 121,
                'PrecioCosto': 50,
                'NroCodBarra': 'SKU1',
                'ecommerce': 'Si',
                'stock_deposito': 15,
                'stock_pedido_cliente': 4,
                'saldo_articulo': 99,
            },
            deposito_id=5,
        )
        self.assertEqual(data['variants'][0]['stock'], 11)
