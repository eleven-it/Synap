"""Estado de pedidos (pantalla preparación) — web y API."""

from django.test import Client, SimpleTestCase
from rest_framework.test import APIClient

from ecom.services.logistica_estado_pedidos_relay import parse_cod_sucursal_request


class EstadoPedidosPreparacionWebTests(SimpleTestCase):
    def test_sin_sesion_redirige_login(self):
        c = Client(HTTP_HOST="127.0.0.1")
        resp = c.get("/ecom/mayoristapp/logistica/estado-pedidos/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp.headers.get("Location", ""))


class EstadoPedidosKanbanAPITests(SimpleTestCase):
    def test_sin_sesion_rechaza(self):
        c = APIClient(HTTP_HOST="127.0.0.1")
        r = c.get("/ecom/api/mayoristapp/logistica/estado-pedidos/", {"ajax": "1"})
        self.assertIn(r.status_code, (401, 403))


class ParseCodSucursalTests(SimpleTestCase):
    def test_none_y_vacio(self):
        self.assertIsNone(parse_cod_sucursal_request(None))
        self.assertIsNone(parse_cod_sucursal_request(""))

    def test_entero(self):
        self.assertEqual(parse_cod_sucursal_request("12"), 12)
        self.assertEqual(parse_cod_sucursal_request(5), 5)
