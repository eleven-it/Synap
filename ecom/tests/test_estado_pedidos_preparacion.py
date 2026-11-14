"""Estado de pedidos (pantalla preparación) — web y API."""

from django.test import Client, SimpleTestCase
from django.test import RequestFactory
from rest_framework.test import APIClient

from ecom.logistica_estado_pedidos_views import EstadoPedidosPreparacionView, EstadoPedidosKanbanAPIView
from ecom.services.logistica_estado_pedidos_relay import parse_cod_sucursal_request


class EstadoPedidosPreparacionWebTests(SimpleTestCase):
    def test_sin_sesion_redirige_login(self):
        c = Client(HTTP_HOST="127.0.0.1")
        resp = c.get("/ecom/mayoristapp/logistica/estado-pedidos/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.headers.get("Location", ""))

    def test_vendedor_no_puede_abrir_tablero_sin_filtro_de_viajante(self):
        request = RequestFactory().get("/ecom/mayoristapp/logistica/estado-pedidos/")
        request.session = {"user": {"nombre_puesto": "Vendedor", "tipousuario": "vendedor"}}
        response = EstadoPedidosPreparacionView().dispatch(request)
        self.assertEqual(response.status_code, 403)


class EstadoPedidosKanbanAPITests(SimpleTestCase):
    def test_sin_sesion_rechaza(self):
        c = APIClient(HTTP_HOST="127.0.0.1")
        r = c.get("/ecom/api/mayoristapp/logistica/estado-pedidos/", {"ajax": "1"})
        self.assertIn(r.status_code, (401, 403))

    def test_vendedor_no_puede_consultar_api_sin_filtro_de_viajante(self):
        request = RequestFactory().get("/ecom/api/mayoristapp/logistica/estado-pedidos/?ajax=1")
        request.session = {"user": {"nombre_puesto": "Vendedor", "tipousuario": "vendedor"}}
        response = EstadoPedidosKanbanAPIView().get(request)
        self.assertEqual(response.status_code, 403)


class ParseCodSucursalTests(SimpleTestCase):
    def test_none_y_vacio(self):
        self.assertIsNone(parse_cod_sucursal_request(None))
        self.assertIsNone(parse_cod_sucursal_request(""))

    def test_entero(self):
        self.assertEqual(parse_cod_sucursal_request("12"), 12)
        self.assertEqual(parse_cod_sucursal_request(5), 5)
