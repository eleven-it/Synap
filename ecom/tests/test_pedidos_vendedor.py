"""
Tests vista pedidos vendedor (F1 UI piloto).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase
from django.urls import reverse

from ecom.mayoristapp_web_views import PedidosVendedorView


class TestPedidosVendedorView(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="ped@example.com", nombre="Ped", password="x")
        self.url = reverse("ecom:mayoristapp_pedidos_vendedor")
        self.factory = RequestFactory()

    def _request(self, user, session_data):
        req = self.factory.get(self.url)
        req.user = user
        req.session = SessionStore()
        for k, v in (session_data or {}).items():
            req.session[k] = v
        req._messages = FallbackStorage(req)
        return req

    def test_redirige_sin_sesion(self):
        req = self._request(AnonymousUser(), {})
        resp = PedidosVendedorView.as_view()(req)
        self.assertEqual(resp.status_code, 302)

    def test_render_ok_con_sesion(self):
        req = self._request(self.user, {"user": {"base_empresa": "emp1", "id_usuario": 1}})
        resp = PedidosVendedorView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        resp.render()
        html = resp.content.decode()
        self.assertIn("Pedidos del vendedor", html)
        self.assertIn("pedidos-app", html)
        self.assertIn("/ecom/api/v1/mayoristapp/comprobantes/pedidos/", html)
