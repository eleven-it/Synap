"""Tests gestión de pedidos: cabecera, plantilla, APIs y anulación."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.models import EcomCart
from ecom.pedido_gestion_views import (
    CarritoDesdePedidoAPIView,
    CarritoDesdePedidoPreviewAPIView,
    PedidoCabeceraV1APIView,
    PedidosRecientesAPIView,
)
from ecom.services.comprobantes_anulacion import anular_pedido_relay
from ecom.services.pedido_cabecera_relay import cabecera_comp_ped_relay, puede_anular_pedido_relay
from ecom.services.pedido_plantilla_service import preview_desde_pedido, validar_pedido_como_plantilla


def _session_user():
    return {
        "id_usuario": 1,
        "base_empresa": "test_base",
        "tipousuario": "vendedor",
        "CodViajante": 5,
    }


def _req_get(path: str, session_user: dict | None = None, session_extra: dict | None = None):
    factory = APIRequestFactory()
    req = factory.get(path)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user or _session_user()
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    user = MagicMock(is_authenticated=True, id=1)
    force_authenticate(req, user=user)
    return req


def _req_post(path: str, body: dict, session_user: dict | None = None, session_extra: dict | None = None):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user or _session_user()
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    user = MagicMock(is_authenticated=True, id=1)
    force_authenticate(req, user=user)
    return req


class TestPuedeAnularPedido(TestCase):
    @patch("ecom.services.pedido_cabecera_relay.cabecera_pedido_relay")
    def test_solo_pendiente(self, mock_cab):
        mock_cab.return_value = {"anulado": "No", "estado": "Pendiente"}
        ok, err = puede_anular_pedido_relay("b", 10)
        self.assertTrue(ok)
        self.assertEqual(err, "")

    @patch("ecom.services.pedido_cabecera_relay.cabecera_pedido_relay")
    def test_rechaza_preparado(self, mock_cab):
        mock_cab.return_value = {"anulado": "No", "estado": "Preparado"}
        ok, err = puede_anular_pedido_relay("b", 10)
        self.assertFalse(ok)
        self.assertIn("Preparado", err)


class TestCabeceraCompPedRelay(TestCase):
    @patch("ecom.services.pedido_cabecera_relay._fetch_all")
    def test_devuelve_pre_sin_filtro_ped(self, mock_fetch):
        mock_fetch.return_value = [{"codigo_movimiento": 99, "tipo_comprobante": "PRE", "nro_comprobante": "0001"}]
        cab = cabecera_comp_ped_relay("emp1", 99)
        self.assertIsNotNone(cab)
        self.assertEqual(cab["tipo_comprobante"], "PRE")
        sql = mock_fetch.call_args[0][1]
        self.assertNotIn("TipoComprobante = 'PED'", sql)

    @patch("ecom.services.pedido_cabecera_relay._fetch_all")
    def test_sin_filas(self, mock_fetch):
        mock_fetch.return_value = []
        self.assertIsNone(cabecera_comp_ped_relay("emp1", 1))


class TestAnularPedidoRelay(TestCase):
    @patch("ecom.services.comprobantes_anulacion.puede_anular_pedido_relay")
    @patch("ecom.services.comprobantes_anulacion.get_mysql_pool")
    def test_anula_con_reversa_stock(self, mock_pool, mock_puede):
        mock_puede.return_value = (True, "")
        conn = MagicMock()
        cur = MagicMock()
        cur.fetchall.return_value = [(100, Decimal("2"), 1)]
        conn.cursor.return_value = cur
        pool = MagicMock()
        pool.get_connection.return_value.__enter__ = lambda s: conn
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.return_value = pool

        out = anular_pedido_relay("b", 99, motivo="Anulación de prueba")
        self.assertEqual(out["msg"], "ok")
        sqls = [str(c[0][0]).lower() for c in cur.execute.call_args_list]
        self.assertTrue(any("stock_deposito" in s for s in sqls))


class TestPlantillaService(TestCase):
    @patch("ecom.services.pedido_plantilla_service._descuento_cliente")
    @patch("ecom.services.pedido_plantilla_service.detalle_pedido_relay")
    @patch("ecom.services.pedido_plantilla_service.cabecera_pedido_relay")
    @patch("ecom.services.pedido_plantilla_service.cliente_accesible_por_sesion")
    @patch("ecom.services.pedido_plantilla_service.resolver_precio_articulo")
    @patch("ecom.services.pedido_plantilla_service.StockService")
    def test_preview_sin_precio_historico_cliente(
        self, mock_stock_cls, mock_precio, mock_acc, mock_cab, mock_det, mock_desc
    ):
        mock_desc.return_value = Decimal("0")
        mock_cab.return_value = {
            "id_cliente": 50,
            "anulado": "No",
            "nro_comprobante": "0001-00000001",
            "fecha": "09/07/2026",
            "total": 1000,
        }
        mock_acc.return_value = True
        mock_det.return_value = [
            {
                "IDArt": 10,
                "CodigoArticulo": "A1",
                "Descripcion": "Art",
                "Salida": 2,
                "PrecioNetoxU": 50,
            }
        ]
        mock_precio.return_value = (Decimal("60"), {"alic_iva": 21})
        mock_stock_cls.return_value.get_disponible.return_value = Decimal("10")

        cart = MagicMock(spec=EcomCart)
        cart.lista_id = 1
        cart.id_deposito = 1

        preview, err = preview_desde_pedido(
            "b",
            123,
            {"tipousuario": "cliente"},
            50,
            cart,
            es_cliente=True,
        )
        self.assertIsNone(err)
        self.assertNotIn("precio_historico_unitario_neto", preview["renglones"][0])
        self.assertNotIn("total_historico", preview)

    @patch("ecom.services.pedido_plantilla_service.cabecera_pedido_relay")
    def test_validar_cliente_distinto(self, mock_cab):
        mock_cab.return_value = {"id_cliente": 99, "anulado": "No"}
        cab, err = validar_pedido_como_plantilla(
            "b", 1, {"tipousuario": "cliente"}, 50, es_cliente=True
        )
        self.assertIsNone(cab)
        self.assertIn("permiso", err.lower())


class TestPedidoGestionAPIViews(TestCase):
    @patch("ecom.pedido_gestion_views.cabecera_pedido_relay")
    @patch("ecom.pedido_gestion_views.puede_anular_pedido_relay")
    @patch("ecom.pedido_gestion_views.vinculos_pedido_relay")
    def test_cabecera_v1_ok(self, mock_vin, mock_puede, mock_cab):
        mock_cab.return_value = {"estado": "Pendiente", "anulado": "No"}
        mock_puede.return_value = (True, "")
        mock_vin.return_value = []
        req = _req_get("/ecom/api/v1/mayoristapp/comprobantes/pedidos/10/")
        resp = PedidoCabeceraV1APIView.as_view()(req, cod_mov=10)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])

    @patch("ecom.pedido_gestion_views.pedidos_recientes_relay")
    def test_recientes_requiere_cliente(self, mock_rec):
        mock_rec.return_value = []
        req = _req_get(
            "/ecom/api/mayoristapp/pedidos/recientes/",
            session_extra={"mayoristapp": {"idcliente": 7}},
        )
        resp = PedidosRecientesAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_rec.assert_called_once()

    @patch("ecom.pedido_gestion_views.preview_desde_pedido")
    @patch("ecom.pedido_gestion_views._resolver_contexto")
    def test_preview_desde_pedido(self, mock_ctx, mock_preview):
        cart = MagicMock()
        mock_ctx.return_value = (("b", 1, cart, Decimal("0")), None)
        mock_preview.return_value = ({"renglones": []}, None)
        req = _req_get("/ecom/api/mayoristapp/carrito/desde-pedido/5/preview/")
        resp = CarritoDesdePedidoPreviewAPIView.as_view()(req, cod_mov=5)
        self.assertEqual(resp.status_code, 200)

    @patch("ecom.pedido_gestion_views.cabecera_pedido_relay", return_value={"id_cliente": 10})
    @patch("ecom.pedido_gestion_views.cargar_desde_pedido")
    @patch("ecom.pedido_gestion_views._resolver_contexto")
    def test_cargar_desde_pedido(self, mock_ctx, mock_cargar, _cab):
        cart = MagicMock()
        mock_ctx.return_value = (("b", 1, cart, Decimal("0")), None)
        mock_cargar.return_value = ({"carrito": {}}, None)
        req = _req_post(
            "/ecom/api/mayoristapp/carrito/desde-pedido/",
            {"codigo_movimiento": 5, "origen": "edicion"},
        )
        resp = CarritoDesdePedidoAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        kwargs = mock_cargar.call_args.kwargs
        self.assertTrue(kwargs.get("omitir_validacion_stock"))
        self.assertEqual(mock_cargar.call_args.args[3], 10)
