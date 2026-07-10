"""
Tests del servicio de carrito mayorista (Fase P1).

El carrito vive en Postgres (modelos Django); el precio y el stock se mockean
(`resolver_precio_articulo`, `StockService`) para no depender de MySQL legacy.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from ecom.models import EcomCart
from ecom.services import mayorista_cart_service as svc

def _row(alic="21", impint="0", nombre="Artículo", codigo="C1", idm="M1"):
    return {
        "CodigoArticuloT": codigo,
        "id_manual": idm,
        "NombreArticulo": nombre,
        "alic_iva": alic,
        "impuesto_interno": impint,
        "promocion": "No",
        "promocion_tipo": "",
        "promocion_por": 0,
        "promocion_cant": 0,
    }


def _stock_ok(mock_stock):
    mock_stock.return_value.validar_disponible_items.return_value = (True, None)


class TestObtenerOCrearCarrito(TestCase):
    def test_crea_carrito_vacio(self):
        cart = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        self.assertIsNotNone(cart.pk)
        self.assertEqual(cart.total, Decimal("0"))
        self.assertEqual(cart.idcliente, 10)
        self.assertEqual(cart.lista_id, 2)

    def test_reutiliza_carrito_borrador(self):
        c1 = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        c2 = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        self.assertEqual(c1.pk, c2.pk)

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_cambio_cliente_reinicia(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row())
        cart = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        svc.agregar_item(cart, 1, 3)
        self.assertEqual(cart.items.count(), 1)

        cart2 = svc.obtener_o_crear_carrito("emp1", 5, idcliente=20, lista_id=2, id_deposito=1)
        self.assertEqual(cart2.pk, cart.pk)
        self.assertEqual(cart2.idcliente, 20)
        self.assertEqual(cart2.items.count(), 0)


class TestAgregarItem(TestCase):
    def _cart(self):
        return svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_agregar_ok(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row(alic="21"))
        cart = self._cart()
        item, err = svc.agregar_item(cart, 1, 10)
        self.assertIsNone(err)
        self.assertEqual(item.cantidad, Decimal("10"))
        cart.refresh_from_db()
        # neto 1000, IVA 21% = 210, total 1210
        self.assertEqual(cart.neto_gravado_21, Decimal("1000.00"))
        self.assertEqual(cart.iva_21, Decimal("210.00"))
        self.assertEqual(cart.total, Decimal("1210.00"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_stock_insuficiente(self, mock_precio, mock_stock):
        mock_stock.return_value.validar_disponible_items.return_value = (False, {"disponible": 5})
        mock_precio.return_value = (Decimal("100"), _row())
        cart = self._cart()
        item, err = svc.agregar_item(cart, 1, 8)
        self.assertIsNone(item)
        self.assertIn("Stock insuficiente", err)
        self.assertEqual(cart.items.count(), 0)

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_consolida_renglon(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row())
        cart = self._cart()
        svc.agregar_item(cart, 1, 3)
        svc.agregar_item(cart, 1, 2)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().cantidad, Decimal("5"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_cantidad_cero_rechazada(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row())
        cart = self._cart()
        item, err = svc.agregar_item(cart, 1, 0)
        self.assertIsNone(item)
        self.assertIn("mayor a 0", err)


class TestOperacionesRenglon(TestCase):
    def _cart(self):
        return svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_actualizar_cantidad_revalida_stock(self, mock_precio, mock_stock):
        mock_precio.return_value = (Decimal("100"), _row())
        mock_stock.return_value.validar_disponible_items.side_effect = [
            (True, None),  # alta con 5
            (False, {"disponible": 5}),  # intento subir a 10
        ]
        cart = self._cart()
        item, _ = svc.agregar_item(cart, 1, 5)
        ok, err = svc.actualizar_cantidad(cart, item.id, 10)
        self.assertFalse(ok)
        self.assertIn("Stock insuficiente", err)
        item.refresh_from_db()
        self.assertEqual(item.cantidad, Decimal("5"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_descuento_renglon(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("1000"), _row(alic="21"))
        cart = self._cart()
        item, _ = svc.agregar_item(cart, 1, 1)  # neto 1000
        ok, err = svc.actualizar_descuento_item(cart, item.id, 10)
        self.assertTrue(ok)
        item.refresh_from_db()
        self.assertEqual(item.neto, Decimal("900.00"))
        self.assertEqual(item.iva, Decimal("189.00"))
        cart.refresh_from_db()
        self.assertEqual(cart.total, Decimal("1089.00"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_quitar_item(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row())
        cart = self._cart()
        item, _ = svc.agregar_item(cart, 1, 2)
        self.assertTrue(svc.quitar_item(cart, item.id))
        self.assertEqual(cart.items.count(), 0)
        cart.refresh_from_db()
        self.assertEqual(cart.total, Decimal("0.00"))


class TestTotales(TestCase):
    def _cart(self):
        return svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_desglose_dos_alicuotas(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.side_effect = [
            (Decimal("1000"), _row(alic="21", codigo="C1")),
            (Decimal("500"), _row(alic="10.5", codigo="C2")),
        ]
        cart = self._cart()
        svc.agregar_item(cart, 1, 1)
        svc.agregar_item(cart, 2, 1)
        cart.refresh_from_db()
        self.assertEqual(cart.neto_gravado_21, Decimal("1000.00"))
        self.assertEqual(cart.iva_21, Decimal("210.00"))
        self.assertEqual(cart.neto_gravado_105, Decimal("500.00"))
        self.assertEqual(cart.iva_105, Decimal("52.50"))
        self.assertEqual(cart.total, Decimal("1762.50"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_descuento_pie(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("1000"), _row(alic="21"))
        cart = self._cart()
        svc.agregar_item(cart, 1, 1)  # neto 1000, iva 210
        ok, _ = svc.aplicar_descuento_pie(cart, 10)
        self.assertTrue(ok)
        cart.refresh_from_db()
        self.assertEqual(cart.neto_gravado_21, Decimal("900.00"))
        self.assertEqual(cart.iva_21, Decimal("189.00"))
        self.assertEqual(cart.total, Decimal("1089.00"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_item_exento(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("300"), _row(alic="0"))
        cart = self._cart()
        svc.agregar_item(cart, 1, 1)
        cart.refresh_from_db()
        self.assertEqual(cart.exento, Decimal("300.00"))
        self.assertEqual(cart.iva_21, Decimal("0.00"))
        self.assertEqual(cart.iva_105, Decimal("0.00"))
        self.assertEqual(cart.total, Decimal("300.00"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_impuesto_interno(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("1000"), _row(alic="21", impint="10"))
        cart = self._cart()
        svc.agregar_item(cart, 1, 1)  # neto 1000, iva 210, interno 100
        cart.refresh_from_db()
        self.assertEqual(cart.impuesto_interno_total, Decimal("100.00"))
        self.assertEqual(cart.total, Decimal("1310.00"))


class TestSerializar(TestCase):
    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_serializa_carrito(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row(alic="21"))
        cart = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        svc.agregar_item(cart, 1, 2)
        data = svc.serializar_carrito(cart)
        self.assertEqual(data["cart_id"], cart.id)
        self.assertEqual(data["cantidad_items"], 1)
        self.assertEqual(data["totales"]["total"], 242.0)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id_articulo"], 1)


class TestTipoComprobanteCarrito(TestCase):
    def _cart(self, tipo=EcomCart.TIPO_PEDIDO):
        return svc.obtener_o_crear_carrito(
            "emp1", 5, idcliente=10, lista_id=2, id_deposito=1, tipo_comprobante=tipo
        )

    def test_actualizar_tipo_ok(self):
        cart = self._cart()
        ok, err = svc.actualizar_tipo_comprobante(cart, "PRE")
        self.assertTrue(ok)
        self.assertIsNone(err)
        cart.refresh_from_db()
        self.assertEqual(cart.tipo_comprobante, EcomCart.TIPO_PRESUPUESTO)

    def test_actualizar_tipo_invalido(self):
        cart = self._cart()
        ok, err = svc.actualizar_tipo_comprobante(cart, "XXX")
        self.assertFalse(ok)
        self.assertIn("no válido", err)

    def test_actualizar_tipo_carrito_confirmado(self):
        cart = self._cart()
        cart.estado = EcomCart.ESTADO_CONFIRMADO
        cart.save(update_fields=["estado"])
        ok, err = svc.actualizar_tipo_comprobante(cart, "DEV")
        self.assertFalse(ok)
        self.assertIn("confirmado", err.lower())

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_devolucion_no_valida_stock(self, mock_precio, mock_stock):
        mock_stock.return_value.validar_disponible_items.return_value = (False, {"disponible": 0})
        mock_precio.return_value = (Decimal("100"), _row())
        cart = self._cart(tipo=EcomCart.TIPO_DEVOLUCION)
        item, err = svc.agregar_item(cart, 1, 99)
        self.assertIsNone(err)
        self.assertIsNotNone(item)
        mock_stock.return_value.validar_disponible_items.assert_not_called()
        self.assertEqual(cart.items.count(), 1)


class TestReiniciarBorradorCompra(TestCase):
    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_limpia_cliente_y_renglones(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row())
        cart = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        svc.agregar_item(cart, 1, 2)
        svc.reiniciar_borrador_compra_vendedor("emp1", 5)
        cart.refresh_from_db()
        self.assertIsNone(cart.idcliente)
        self.assertEqual(cart.items.count(), 0)
        self.assertEqual(cart.total, Decimal("0.00"))
