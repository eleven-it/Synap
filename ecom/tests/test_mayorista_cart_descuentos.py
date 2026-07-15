"""
Tests descuentos renglón + pie en carrito mayorista (Oleada C).

REQ-DSC-01/02/05, CAR-005/006/007.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.carrito_relay_views import CarritoRelayAPIView, CarritoItemRelayAPIView
from ecom.models import EcomCart
from ecom.services import mayorista_cart_service as svc
from ecom.services.mayoristapp_session import guardar_cliente_seleccion_mayoristapp


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


class TestDescRenglonPrecarga(TestCase):
    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_desc_renglon_al_agregar(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("1000"), _row(alic="21"))
        cart = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        item, err = svc.agregar_item(cart, 1, 1, descuento_cliente=Decimal("12"))
        self.assertIsNone(err)
        self.assertEqual(item.porcentaje_descuento, Decimal("12"))
        item.refresh_from_db()
        self.assertEqual(item.neto, Decimal("880.00"))
        self.assertEqual(item.iva, Decimal("184.80"))
        self.assertEqual(item.total, Decimal("1064.80"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_consolidar_no_pisa_descuento_manual(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("1000"), _row(alic="21"))
        cart = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        item, _ = svc.agregar_item(cart, 1, 1, descuento_cliente=Decimal("8"))
        svc.actualizar_descuento_item(cart, item.id, 0)
        item.refresh_from_db()
        self.assertEqual(item.porcentaje_descuento, Decimal("0"))
        svc.agregar_item(cart, 1, 1, descuento_cliente=Decimal("8"))
        item.refresh_from_db()
        self.assertEqual(item.porcentaje_descuento, Decimal("0"))


class TestDescPieCliente(TestCase):
    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_primera_seleccion_precarga_desc_pie(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("100"), _row())
        cart = svc.obtener_o_crear_carrito("emp1", 5, lista_id=2, id_deposito=1)
        cart2 = svc.obtener_o_crear_carrito(
            "emp1", 5, idcliente=10, lista_id=2, id_deposito=1, desc_pie_cliente=Decimal("5")
        )
        self.assertEqual(cart.pk, cart2.pk)
        cart2.refresh_from_db()
        self.assertEqual(cart2.descuento_pie_pct, Decimal("5"))

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_cambio_cliente_actualiza_desc_pie(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("1000"), _row(alic="21"))
        cart = svc.obtener_o_crear_carrito(
            "emp1", 5, idcliente=10, lista_id=2, id_deposito=1, desc_pie_cliente=Decimal("0")
        )
        svc.agregar_item(cart, 1, 1)
        cart2 = svc.obtener_o_crear_carrito(
            "emp1", 5, idcliente=20, lista_id=2, id_deposito=1, desc_pie_cliente=Decimal("10")
        )
        self.assertEqual(cart.pk, cart2.pk)
        cart2.refresh_from_db()
        self.assertEqual(cart2.idcliente, 20)
        self.assertEqual(cart2.descuento_pie_pct, Decimal("10"))
        self.assertEqual(cart2.items.count(), 0)


class TestOrdenDescuentos(TestCase):
    """REQ-DSC-05: renglón antes que pie."""

    @patch.object(svc, "StockService")
    @patch.object(svc, "resolver_precio_articulo")
    def test_renglon_10_pie_10_sobre_neto_gravado(self, mock_precio, mock_stock):
        _stock_ok(mock_stock)
        mock_precio.return_value = (Decimal("1000"), _row(alic="21"))
        cart = svc.obtener_o_crear_carrito("emp1", 5, idcliente=10, lista_id=2, id_deposito=1)
        item, _ = svc.agregar_item(cart, 1, 1)
        svc.actualizar_descuento_item(cart, item.id, 10)
        svc.aplicar_descuento_pie(cart, 10)
        cart.refresh_from_db()
        # neto renglón 900 → pie 10% → 810 gravado 21%; IVA 170.10; total 980.10
        self.assertEqual(cart.neto_gravado_21, Decimal("810.00"))
        self.assertEqual(cart.iva_21, Decimal("170.10"))
        self.assertEqual(cart.total, Decimal("980.10"))


class TestCarritoRelayDescuentos(TestCase):
    def setUp(self):
        self.api_factory = APIRequestFactory()
        User = get_user_model()
        self.user = User.objects.create_user(email="v1@example.com", nombre="V", password="x")

    def _session_request(self, method, path, data=None, *, cliente=None):
        req = getattr(self.api_factory, method.lower())(path, data or {}, format="json")
        req.session = SessionStore()
        req.session["user"] = {
            "base_empresa": "emp1",
            "id_usuario": 5,
            "tipousuario": "vendedor",
            "id_vendedor_usr": 1,
        }
        req.session["mayoristapp"] = {"formulario": "PED", "iva_incluido": "Si"}
        if cliente is not None:
            guardar_cliente_seleccion_mayoristapp(
                req,
                cliente_datos=cliente,
                autoriza_credito={},
                idcliente=cliente["Codigo"],
                domicilios_cliente=[],
                iva_incluido="Si",
            )
        req.session.save()
        force_authenticate(req, user=self.user)
        return req

    @patch("ecom.carrito_relay_views.cart_svc.agregar_item")
    @patch("ecom.carrito_relay_views.cart_svc.obtener_o_crear_carrito")
    @patch("ecom.carrito_relay_views._leer_desc_pie_cliente")
    @patch("ecom.carrito_relay_views._obtener_lista_id_y_cliente")
    @patch("ecom.carrito_relay_views._obtener_id_deposito")
    @patch("ecom.carrito_relay_views._session_base_empresa")
    @patch("ecom.carrito_relay_views._session_id_usuario")
    def test_get_carrito_sincroniza_desc_pie_cliente(
        self,
        mock_uid,
        mock_base,
        mock_dep,
        mock_ctx,
        mock_desc_pie,
        mock_cart,
        mock_agregar,
    ):
        mock_uid.return_value = 5
        mock_base.return_value = "emp1"
        mock_dep.return_value = 1
        mock_ctx.return_value = (2, 10, Decimal("8"), True)
        mock_desc_pie.return_value = Decimal("5")
        cart = MagicMock()
        mock_cart.return_value = cart
        mock_agregar.return_value = (MagicMock(), None)

        with patch("ecom.carrito_relay_views.cart_svc.serializar_carrito") as mock_ser:
            mock_ser.return_value = {"descuento_pie_pct": 5.0, "items": [], "totales": {}}
            req = self._session_request(
                "GET",
                reverse("ecom:mayoristapp_carrito"),
                cliente={"Codigo": 10, "descPie": 5, "descRenglon": 8},
            )
            resp = CarritoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_cart.assert_called_once()
        _args, kwargs = mock_cart.call_args
        self.assertEqual(kwargs.get("desc_pie_cliente"), Decimal("5"))

    @patch("ecom.carrito_relay_views.cart_svc.actualizar_descuento_item")
    @patch("ecom.carrito_relay_views.cart_svc.obtener_o_crear_carrito")
    @patch("ecom.carrito_relay_views._leer_desc_pie_cliente")
    @patch("ecom.carrito_relay_views._obtener_lista_id_y_cliente")
    @patch("ecom.carrito_relay_views._obtener_id_deposito")
    @patch("ecom.carrito_relay_views._session_base_empresa")
    @patch("ecom.carrito_relay_views._session_id_usuario")
    def test_patch_descuento_renglon(
        self,
        mock_uid,
        mock_base,
        mock_dep,
        mock_ctx,
        mock_desc_pie,
        mock_cart,
        mock_upd,
    ):
        mock_uid.return_value = 5
        mock_base.return_value = "emp1"
        mock_dep.return_value = 1
        mock_ctx.return_value = (2, 10, Decimal("0"), True)
        mock_desc_pie.return_value = Decimal("0")
        cart = MagicMock()
        mock_cart.return_value = cart
        mock_upd.return_value = (True, None)

        with patch("ecom.carrito_relay_views.cart_svc.serializar_carrito") as mock_ser:
            mock_ser.return_value = {
                "items": [{"id": 7, "porcentaje_descuento": 15.0}],
                "totales": {"total": 850.0},
            }
            req = self._session_request(
                "PATCH",
                reverse("ecom:mayoristapp_carrito_item", kwargs={"item_id": 7}),
                {"porcentaje_descuento": 15},
            )
            resp = CarritoItemRelayAPIView.as_view()(req, item_id=7)
        self.assertEqual(resp.status_code, 200)
        mock_upd.assert_called_once_with(cart, 7, 15)
        self.assertEqual(resp.data["items"][0]["porcentaje_descuento"], 15.0)
