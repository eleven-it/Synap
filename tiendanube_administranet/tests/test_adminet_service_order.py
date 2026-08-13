"""Tests escritura pedido TN → AdministraNET: administranet_types y transacción."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import MySQLdb
from django.test import SimpleTestCase

from tiendanube_administranet.models import AdministraNETConfig
from tiendanube_administranet.services.adminet_service import AdministraNETService
from tiendanube_administranet.services.order_mysql_write import (
    normalize_comp_ped_params,
    normalize_stockp_line_params,
    resolve_fecha_entrega,
)


class ResolveFechaEntregaTests(SimpleTestCase):
    def test_fecha_estimada_invalida_retorna_none(self):
        self.assertIsNone(
            resolve_fecha_entrega({'estimated_delivery_date': 'no-es-fecha'})
        )

    def test_fecha_estimada_iso_valida(self):
        self.assertEqual(
            resolve_fecha_entrega({'estimated_delivery_date': '2026-08-20T15:00:00Z'}),
            '2026-08-20',
        )

    def test_sin_fecha_estimada_default_siete_dias(self):
        from datetime import datetime

        now = datetime(2026, 8, 13, 12, 0, 0)
        self.assertEqual(
            resolve_fecha_entrega({}, now=now),
            '2026-08-20',
        )


class NormalizeCompPedParamsTests(SimpleTestCase):
    def _base_kwargs(self, **overrides):
        base = {
            'nro_comprobante': '0001-00000001',
            'codigo_movimiento': 9001,
            'estado_pedido': 'En preparación',
            'cliente_id': '',
            'total': '1210.50',
            'importe_letras': 'mil doscientos',
            'subtotal': '1210.50',
            'subtotal_sin_iva': '1000.00',
            'iva_21': '210.50',
            'discount': '',
            'subtotal_menos_desc': '1210.50',
            'id_condventa': 1,
            'cond_venta': 'Contado',
            'cod_viajante': '',
            'user_id': 1,
            'sucursal_id': 1,
            'deposito_id': 2,
            'fecha_entrega': 'fecha-invalida',
            'forma_entrega': 'Envía por despacho',
            'carrier': '',
            'tiendanube_order_id': 'TN-001',
            'ped_eco_number': '',
            'info_ped_eco': '{}',
            'estado_pago_ecom': 'Si',
            'tipo_pedido': 'Ecom cliente',
            'punto_venta_id': 1,
        }
        base.update(overrides)
        return base

    def test_int_vacio_y_date_invalida_normalizados(self):
        params = normalize_comp_ped_params(**self._base_kwargs())
        # CodViajante (21), FechaEntrega (25), Vencimiento (32), ped_eco (29)
        self.assertIsNone(params[21])
        self.assertIsNone(params[25])
        self.assertIsNone(params[32])
        self.assertIsNone(params[29])
        self.assertEqual(params[3], 1)

    def test_decimal_y_varchar_default(self):
        params = normalize_comp_ped_params(**self._base_kwargs())
        self.assertIsInstance(params[4], Decimal)
        self.assertEqual(params[4], Decimal('1210.50'))
        self.assertEqual(params[27], '-')
        self.assertEqual(params[28], 'TN-001')


class NormalizeStockpLineParamsTests(SimpleTestCase):
    def test_producto_sin_ids_usa_decimal_y_varchar_default(self):
        params = normalize_stockp_line_params(
            product={'sku': '', 'name': '', 'quantity': '2', 'price': '150.25', 'adminet_product_id': ''},
            codigo_movimiento=9001,
            deposito_id=1,
            sucursal_id=1,
            cod_viajante='',
            nro_comprobante='0001-00000001',
            orden=1,
        )
        self.assertEqual(params[0], '-')
        self.assertEqual(params[1], '-')
        self.assertIsInstance(params[2], Decimal)
        self.assertEqual(params[2], Decimal('2'))
        self.assertIsInstance(params[5], Decimal)
        self.assertEqual(params[20], 0)
        self.assertIsNone(params[25])


class CreateOrderTransactionTests(SimpleTestCase):
    def _service(self):
        config = AdministraNETConfig(name='Test', database='empresa_test')
        return AdministraNETService(config, base_empresa='empresa_test')

    def _order_payload(self):
        return {
            'id': 777001,
            'number': 42,
            'total': '500',
            'subtotal': '500',
            'discount': 0,
            'shipping_cost': 0,
            'payment_status': 'pending',
            'customer': {'name': 'Cliente', 'email': 'c@test.com'},
            'shipping_address': {},
            'shipping': {'type': 'ship', 'carrier': ''},
            'products': [
                {
                    'sku': 'SKU-1',
                    'name': 'Artículo',
                    'quantity': 1,
                    'price': 500,
                    'adminet_product_id': 10,
                },
            ],
            'adminet_customer_id': 5,
        }

    @patch('tiendanube_administranet.services.adminet_service.get_connection')
    @patch(
        'tiendanube_administranet.services.adelanto_recibo_service.allocate_codigo_movimiento',
        return_value=88001,
    )
    def test_fallo_en_linea_hace_rollback_sin_commit(
        self, _mock_allocate, mock_get_connection
    ):
        conn = MagicMock()
        mock_get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_connection.return_value.__exit__ = MagicMock(return_value=False)
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        def execute_side_effect(query, params=None):
            if 'INSERT INTO stockp' in query:
                raise MySQLdb.OperationalError('fallo simulado línea stockp')

        cursor.execute.side_effect = execute_side_effect

        svc = self._service()
        svc.get_order_by_tiendanube_id = MagicMock(return_value={'success': False})
        svc.get_next_nro_comprobante = MagicMock(
            return_value={'success': True, 'nro_comprobante': '0001-00000099'}
        )

        result = svc.create_order_from_tiendanube(
            self._order_payload(),
            registrar_adelanto=False,
        )

        self.assertFalse(result['success'])
        self.assertIn('fallo', result['message'].lower())
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.autocommit.assert_any_call(False)
        conn.autocommit.assert_any_call(True)

    @patch('tiendanube_administranet.services.adminet_service.get_connection')
    @patch(
        'tiendanube_administranet.services.adelanto_recibo_service.allocate_codigo_movimiento',
        return_value=88002,
    )
    def test_exito_hace_commit_unico(self, _mock_allocate, mock_get_connection):
        conn = MagicMock()
        mock_get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_connection.return_value.__exit__ = MagicMock(return_value=False)
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        svc = self._service()
        svc.get_order_by_tiendanube_id = MagicMock(return_value={'success': False})
        svc.get_next_nro_comprobante = MagicMock(
            return_value={'success': True, 'nro_comprobante': '0001-00000100'}
        )

        result = svc.create_order_from_tiendanube(
            self._order_payload(),
            registrar_adelanto=False,
        )

        self.assertTrue(result['success'])
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()

    @patch('tiendanube_administranet.services.adminet_service.get_connection')
    @patch(
        'tiendanube_administranet.services.adelanto_recibo_service.allocate_codigo_movimiento',
        return_value=88003,
    )
    def test_comp_ped_insert_usa_tipos_administranet(
        self, _mock_allocate, mock_get_connection
    ):
        conn = MagicMock()
        mock_get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_get_connection.return_value.__exit__ = MagicMock(return_value=False)
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        captured = []

        def capture_execute(query, params=None):
            if 'INSERT INTO comp_ped' in query:
                captured.append(params)

        cursor.execute.side_effect = capture_execute

        svc = self._service()
        svc.get_order_by_tiendanube_id = MagicMock(return_value={'success': False})
        svc.get_next_nro_comprobante = MagicMock(
            return_value={'success': True, 'nro_comprobante': '0001-00000101'}
        )

        order = self._order_payload()
        order['shipping'] = {'type': 'ship', 'carrier': '', 'estimated_delivery_date': 'invalida'}
        order['products'] = []

        svc.create_order_from_tiendanube(order, registrar_adelanto=False)

        self.assertEqual(len(captured), 1)
        params = captured[0]
        self.assertIsInstance(params[4], Decimal)
        self.assertIsNone(params[25])
        self.assertEqual(params[27], '-')
