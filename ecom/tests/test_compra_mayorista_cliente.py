"""Tests limpieza de cliente en compra mayorista."""

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase

from ecom.mayoristapp_web_views import CompraMayoristaView
from ecom.services.mayoristapp_session import (
    guardar_cliente_seleccion_mayoristapp,
    leer_idcliente_mayoristapp,
    limpiar_cliente_seleccion_mayoristapp,
)


class TestLimpiarClienteCompra(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, session_data=None):
        req = self.factory.get("/ecom/mayoristapp/compra/")
        req.session = SessionStore()
        for k, v in (session_data or {}).items():
            req.session[k] = v
        req.session.save()
        req._messages = FallbackStorage(req)
        User = get_user_model()
        req.user = User.objects.create_user(email="v1@example.com", nombre="V", password="x")
        return req

    def test_limpiar_quita_claves_sesion(self):
        req = self._request()
        guardar_cliente_seleccion_mayoristapp(
            req,
            cliente_datos={"Codigo": 474, "nombre_cliente": "Test"},
            autoriza_credito={},
            idcliente=474,
            domicilios_cliente=[],
            iva_incluido="Si",
        )
        self.assertEqual(leer_idcliente_mayoristapp(req), 474)
        limpiar_cliente_seleccion_mayoristapp(req)
        self.assertIsNone(leer_idcliente_mayoristapp(req))
        self.assertIsNone(req.session.get("cliente"))

    def test_compra_get_limpia_cliente_vendedor(self):
        req = self._request(
            {
                "user": {"base_empresa": "emp1", "id_usuario": 1, "tipousuario": "vendedor"},
                "mayoristapp": {"idcliente": 474, "cliente": [{"Codigo": 474}, {}]},
                "idcliente": 474,
            }
        )
        CompraMayoristaView.as_view()(req)
        self.assertIsNone(leer_idcliente_mayoristapp(req))
