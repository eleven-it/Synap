import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_project.settings")
django.setup()

import unittest
from unittest.mock import patch, MagicMock
from tiendanube.services.order_to_adminet_service import OrderToAdminetService

class OrderToAdminetServiceTest(unittest.TestCase):
    def setUp(self):
        # Mock config para MySQL
        self.mysql_config = {
            'host': 'localhost',
            'port': 3306,
            'database': 'adminet',
            'user': 'test',
            'password': 'test',
        }
        self.order_data = {
            'id': 'TND-123',
            'created_at': '2024-07-24 19:00:00',
            'total': 1000.0,
            'note': 'Pedido de prueba',
            'payment_method': 'credit_card',
            'customer': {
                'email': 'cliente@ejemplo.com',
                'identification': '20304050',
                'name': 'Cliente Prueba',
                'phone': '123456789',
                'address': {
                    'street': 'Calle Falsa 123',
                    'city': 'Ciudad',
                    'province': 'Provincia',
                    'zip': '1000',
                }
            },
            'shipping_address': {
                'street': 'Calle Falsa 123',
                'city': 'Ciudad',
                'province': 'Provincia',
                'zip': '1000',
            },
            'items': [
                {
                    'product_id': 1,
                    'name': 'Producto A',
                    'quantity': 2,
                    'price': 500.0,
                    'total': 1000.0
                }
            ]
        }

    @patch('tiendanube.services.order_to_adminet_service.MySQLConnectionService')
    @patch('tiendanube.services.order_to_adminet_service.TiendaNubeCondVentaMap')
    def test_save_order_inserts_cliente_pedido_y_lineas(self, MockCondVentaMap, MockMySQLService):
        # Mock de MySQL
        mock_mysql = MockMySQLService.return_value
        # Simular que el cliente no existe
        mock_mysql.execute_query.side_effect = [
            None,  # No existe cliente
            None,  # Insert cliente
            {'idcliente': 42},  # Nuevo cliente
            None,  # Insert pedido
            {'idpedido': 99},  # Nuevo pedido
            None  # Insert línea
        ]
        # Mock mapeo de condición de venta
        mock_map = MagicMock()
        mock_map.adminet_codigo = 5
        MockCondVentaMap.objects.filter.return_value.first.return_value = mock_map

        service = OrderToAdminetService(mysql_config=self.mysql_config)
        pedido_id = service.save_order(self.order_data)
        self.assertEqual(pedido_id, 99)
        # Verifica que se insertó cliente, pedido y línea
        self.assertTrue(mock_mysql.execute_query.called)
        self.assertEqual(mock_mysql.execute_query.call_count, 6)
        MockCondVentaMap.objects.filter.assert_called_with(payment_method='credit_card', activo=True)

if __name__ == '__main__':
    unittest.main() 