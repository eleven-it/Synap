"""
Tests unitarios mínimos para servicios Self-Checkout (EPIC 3).
Usan mocks para no depender de MySQL.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase

from self_checkout.services.stock_service import StockService
from self_checkout.services.kiosk_service import KioskSessionService
from self_checkout.services.cart_service import CartService
from self_checkout.services.tpv_payment_validation import evaluar_suma_medios_pago, TOLERANCIA_MEDIOS_TPV
from self_checkout.services.serie_service import articulos_requieren_serie_map
from self_checkout.services.tpv_paridad_precheck import evaluar_precheck_tpv_paridad
from self_checkout.constants import E_TPV_OBLIGA_PV, E_TPV_OBLIGA_VENDEDOR


class StockServiceTests(SimpleTestCase):
    """Tests de StockService: DISPONIBLE = saldo - saldo_pedido_cliente."""

    @patch('self_checkout.services.stock_service.mysql_cursor')
    def test_get_disponible_calcula_correctamente(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = {
            'saldo': 10,
            'saldo_pedido_cliente': 3,
        }
        svc = StockService('test_db')
        disp = svc.get_disponible(1, 1)
        self.assertEqual(disp, Decimal('7'))

    @patch('self_checkout.services.stock_service.mysql_cursor')
    def test_get_disponible_sin_registro_retorna_cero(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = None
        svc = StockService('test_db')
        disp = svc.get_disponible(999, 1)
        self.assertEqual(disp, Decimal('0'))

    @patch('self_checkout.services.stock_service.mysql_cursor')
    def test_validar_disponible_items_rechaza_exceso(self, mock_cursor):
        def fetchone_side_effect():
            return {'saldo': 5, 'saldo_pedido_cliente': 0}
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = fetchone_side_effect
        mock_cursor.return_value.__enter__.return_value = mock_cur

        svc = StockService('test_db')
        ok, err = svc.validar_disponible_items(
            [{'id_articulo': 1, 'cantidad': Decimal('10')}],
            id_deposito=1,
        )
        self.assertFalse(ok)
        self.assertEqual(err['id_articulo'], 1)
        self.assertEqual(err['cantidad_solicitada'], Decimal('10'))
        self.assertEqual(err['disponible'], Decimal('5'))
        self.assertEqual(err['faltante'], Decimal('5'))
        self.assertIn('reducir cantidad a 5', err['sugerencia'])

    @patch('self_checkout.services.stock_service.mysql_cursor')
    def test_validar_disponible_items_acepta_disponible_exacto(self, mock_cursor):
        """Cantidad solicitada = disponible exacto → acepta."""
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = {
            'saldo': 10,
            'saldo_pedido_cliente': 3,
        }
        svc = StockService('test_db')
        ok, err = svc.validar_disponible_items(
            [{'id_articulo': 1, 'cantidad': Decimal('7')}],
            id_deposito=1,
        )
        self.assertTrue(ok)
        self.assertIsNone(err)

    @patch('self_checkout.services.stock_service.mysql_cursor')
    def test_validar_disponible_items_acepta_stock_suficiente(self, mock_cursor):
        def fetchone_side_effect():
            return {'saldo': 10, 'saldo_pedido_cliente': 0}
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = fetchone_side_effect
        mock_cursor.return_value.__enter__.return_value = mock_cur

        svc = StockService('test_db')
        ok, err = svc.validar_disponible_items(
            [{'id_articulo': 1, 'cantidad': Decimal('5')}],
            id_deposito=1,
        )
        self.assertTrue(ok)
        self.assertIsNone(err)

    @patch('self_checkout.services.stock_service.mysql_cursor')
    def test_validar_disponible_items_rechaza_sin_fila_stock_deposito(self, mock_cursor):
        """Artículo sin fila en stock_deposito → disponible=0 → rechaza."""
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = None
        svc = StockService('test_db')
        ok, err = svc.validar_disponible_items(
            [{'id_articulo': 999, 'cantidad': Decimal('1')}],
            id_deposito=1,
        )
        self.assertFalse(ok)
        self.assertEqual(err['id_articulo'], 999)
        self.assertEqual(err['disponible'], Decimal('0'))
        self.assertIn('sin stock', err['sugerencia'])


class KioskSessionServiceTests(SimpleTestCase):
    """Tests de KioskSessionService: resolve_context, validar_alcance."""

    @patch('self_checkout.services.kiosk_service.mysql_cursor')
    def test_resolve_context_desde_config_kiosco(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = {
            'kiosk_id': 'k01',
            'id_sucursal': 1,
            'id_punto_venta': 2,
            'id_deposito': 3,
            'modo_rfid': 'delta',
            'activo': 1,
        }
        svc = KioskSessionService('test_db')
        ctx, err = svc.resolve_context('k01', {}, es_admin=False)
        self.assertIsNone(err)
        self.assertEqual(ctx['id_sucursal'], 1)
        self.assertEqual(ctx['id_punto_venta'], 2)
        self.assertEqual(ctx['id_deposito'], 3)
        self.assertEqual(ctx['cod_sucursal'], 1)

    @patch('self_checkout.services.kiosk_service.mysql_cursor')
    def test_resolve_context_sin_config_falla_si_sesion_vacia(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = None
        svc = KioskSessionService('test_db')
        ctx, err = svc.resolve_context('k99', {}, es_admin=False)
        self.assertIsNotNone(err)
        self.assertIsNone(ctx)

    @patch('self_checkout.services.kiosk_service.mysql_cursor')
    def test_resolve_context_desde_sesion_cuando_hay_datos(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.fetchone.return_value = None
        svc = KioskSessionService('test_db')
        session = {'id_sucursal': 1, 'id_punto_venta': 2, 'id_deposito': 3}
        ctx, err = svc.resolve_context('k99', session, es_admin=False)
        self.assertIsNone(err)
        self.assertEqual(ctx['id_sucursal'], 1)
        self.assertEqual(ctx['id_punto_venta'], 2)
        self.assertEqual(ctx['id_deposito'], 3)
        self.assertEqual(ctx['cod_sucursal'], 1)


class CartServiceTests(SimpleTestCase):
    """Tests de CartService: validación stock al agregar."""

    @patch.object(CartService, '_recalcular_totales')
    @patch('self_checkout.services.cart_service.StockService')
    @patch('self_checkout.services.cart_service.mysql_cursor')
    def test_agregar_item_rechaza_si_stock_insuficiente(self, mock_cursor, mock_stock_cls, mock_recalc):
        mock_stock = MagicMock()
        mock_stock.validar_disponible_items.return_value = (False, {'id_articulo': 1, 'disponible': 0})
        mock_stock_cls.return_value = mock_stock

        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = {'id_deposito': 1}
        mock_cur.fetchall.return_value = []
        mock_cur.lastrowid = 1
        mock_cursor.return_value.__enter__.return_value = mock_cur

        svc = CartService('test_db')
        item_id, err = svc.agregar_item(
            cart_id=1,
            id_articulo=1,
            codigo_articulo='X',
            descripcion='Art X',
            cantidad=Decimal('5'),
            precio_unitario=Decimal('10'),
            alicuota_iva=Decimal('21'),
            origen='scan',
        )
        self.assertIsNone(item_id)
        self.assertIsNotNone(err)
        self.assertIn('Stock insuficiente', err)

    @patch.object(CartService, '_recalcular_totales')
    @patch('self_checkout.services.cart_service.StockService')
    @patch('self_checkout.services.cart_service.mysql_cursor')
    def test_agregar_item_acepta_si_stock_ok(self, mock_cursor, mock_stock_cls, mock_recalc):
        mock_stock = MagicMock()
        mock_stock.validar_disponible_items.return_value = (True, None)
        mock_stock_cls.return_value = mock_stock

        mock_cur = MagicMock()
        # Primer with: deposito; segundo with: sin línea existente, luego max_orden
        mock_cur.fetchone.side_effect = [
            {'id_deposito': 1},
            None,
            {'max_orden': 0},
        ]
        mock_cur.fetchall.return_value = []
        mock_cur.lastrowid = 100
        mock_cursor.return_value.__enter__.return_value = mock_cur

        svc = CartService('test_db')
        item_id, err = svc.agregar_item(
            cart_id=1,
            id_articulo=1,
            codigo_articulo='X',
            descripcion='Art X',
            cantidad=Decimal('1'),
            precio_unitario=Decimal('10'),
            alicuota_iva=Decimal('21'),
            origen='scan',
        )
        self.assertEqual(item_id, 100)
        self.assertIsNone(err)


class TpvParidadPrecheckTests(SimpleTestCase):
    """Precheck TPV: obliga PV / obliga vendedor con permisos simulados."""

    @patch('self_checkout.services.tpv_paridad_precheck.cargar_permisos_puesto')
    def test_obliga_pv_rechaza_sin_id_pv(self, mock_perm):
        mock_perm.return_value = {'obliga_selecpv': 'Si'}
        ok, code, msg = evaluar_precheck_tpv_paridad(
            'base_x',
            cart_row={'id_punto_venta': None, 'kiosk_id': 'k1'},
            id_cliente=5,
            total_venta=100.0,
            tpv_importe_efectivo=None,
            cod_viajante_en_post=1,
            id_puesto=2,
        )
        self.assertFalse(ok)
        self.assertEqual(code, E_TPV_OBLIGA_PV)

    @patch('self_checkout.services.tpv_paridad_precheck.cargar_permisos_puesto')
    def test_obliga_vendedor_sin_cod_viajante(self, mock_perm):
        mock_perm.return_value = {'obliga_cambvendedor': 'Si'}
        ok, code, msg = evaluar_precheck_tpv_paridad(
            'base_x',
            cart_row={'id_punto_venta': 3, 'kiosk_id': 'k1'},
            id_cliente=5,
            total_venta=50.0,
            tpv_importe_efectivo=None,
            cod_viajante_en_post=None,
            id_puesto=2,
        )
        self.assertFalse(ok)
        self.assertEqual(code, E_TPV_OBLIGA_VENDEDOR)

    @patch('self_checkout.services.tpv_paridad_precheck.cargar_permisos_puesto')
    @patch('self_checkout.services.tpv_paridad_precheck._credito_cliente_ok')
    @patch('self_checkout.services.tpv_paridad_precheck._limite_efectivo_caja_y_supera')
    def test_sin_flags_permiso_ok(self, mock_lim, mock_cred, mock_perm):
        mock_perm.return_value = {}
        mock_cred.return_value = (True, None)
        mock_lim.return_value = (True, None)
        ok, code, msg = evaluar_precheck_tpv_paridad(
            'base_x',
            cart_row={'id_punto_venta': 1, 'kiosk_id': 'k1'},
            id_cliente=1,
            total_venta=10.0,
            tpv_importe_efectivo=None,
            cod_viajante_en_post=None,
            id_puesto=None,
        )
        self.assertTrue(ok)
        self.assertIsNone(code)


class ArticulosSerieMapTests(SimpleTestCase):
    @patch('self_checkout.services.serie_service.mysql_cursor')
    def test_mapa_marca_seriados(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.fetchall.return_value = [
            {'IDArt': 10, 'serie': 'Si'},
            {'IDArt': 20, 'serie': 'No'},
        ]
        m = articulos_requieren_serie_map('base_x', [10, 20])
        self.assertTrue(m.get(10))
        self.assertFalse(m.get(20))


class TpvPaymentValidationTests(SimpleTestCase):
    """evaluar_suma_medios_pago: paridad TPV.frm (efectivo + tarjeta + intereses ≈ total)."""

    def test_ambos_none_sin_validacion_aqui(self):
        ok, err = evaluar_suma_medios_pago(100.0, None, None, None)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_mixto_sin_intereses_ok(self):
        ok, err = evaluar_suma_medios_pago(100.0, 40.0, 60.0, None)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_mixto_con_intereses_ok(self):
        ok, err = evaluar_suma_medios_pago(110.0, 40.0, 60.0, 10.0)
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_rechaza_suma_cero(self):
        ok, err = evaluar_suma_medios_pago(100.0, 0.0, 0.0, 0.0)
        self.assertFalse(ok)
        self.assertIn('medio de cobro', err or '')

    def test_rechaza_mismatch_total(self):
        ok, err = evaluar_suma_medios_pago(100.0, 10.0, 20.0, None)
        self.assertFalse(ok)
        self.assertIn('no coincide', err or '')

    def test_tolerancia_redondeo(self):
        total = 99.99
        ok, err = evaluar_suma_medios_pago(total, 50.0, 50.0 - TOLERANCIA_MEDIOS_TPV, None)
        self.assertTrue(ok)
