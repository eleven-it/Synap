"""Tests — pago TN y stock disponible (saldo − reservas)."""

from decimal import Decimal

from django.test import SimpleTestCase

from tiendanube_administranet.services.order_payment import (
    parse_tiendanube_order_payment,
    pago_confirmado,
)
from tiendanube_administranet.services.product_stock import (
    stock_unidades_articulo_deposito,
)


class ParseTiendanubeOrderPaymentTests(SimpleTestCase):
    def test_extrae_payment_details_y_gateway(self):
        order = {
            'payment_status': 'paid',
            'total': '1500.50',
            'paid_at': '2026-05-01T12:00:00+0000',
            'gateway': 'mercadopago',
            'gateway_id': 'MP-12345',
            'gateway_name': 'Mercado Pago',
            'gateway_method': 'credit_card',
            'payment_details': {
                'method': 'credit_card',
                'credit_card_company': 'visa',
                'installments': 3,
            },
        }
        pago = parse_tiendanube_order_payment(order)
        self.assertTrue(pago_confirmado(pago))
        self.assertEqual(pago.method_label, 'credit_card')
        self.assertEqual(pago.gateway_id, 'MP-12345')
        self.assertEqual(pago.gateway_name, 'Mercado Pago')
        self.assertEqual(pago.installments, 3)
        self.assertEqual(pago.total, Decimal('1500.50'))
        self.assertEqual(pago.medio_adminet, 'tarjeta')

    def test_transferencia_detectada(self):
        order = {
            'payment_status': 'paid',
            'total': 100,
            'payment_details': {'method': 'wire_transfer'},
            'gateway_name': 'Transferencia bancaria',
        }
        pago = parse_tiendanube_order_payment(order)
        self.assertEqual(pago.medio_adminet, 'transferencia')


class StockDisponibleConReservaTests(SimpleTestCase):
    def test_resta_saldo_pedido_cliente(self):
        self.assertEqual(
            stock_unidades_articulo_deposito(
                {'stock_deposito': 20, 'stock_pedido_cliente': 7},
                deposito_id=2,
            ),
            13,
        )

    def test_no_negativo_con_reserva_mayor(self):
        self.assertEqual(
            stock_unidades_articulo_deposito(
                {'stock_deposito': 3, 'stock_pedido_cliente': 10},
                deposito_id=1,
            ),
            0,
        )
