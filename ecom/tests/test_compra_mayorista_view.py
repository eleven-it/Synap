"""
Test de render de la UI web de compra mayorista (Fase P3).

Se usa RequestFactory para probar la vista + plantilla sin el stack de middleware
(permisos de módulo, etc.). La vista solo arma URLs con reverse() (sin MySQL).
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory, TestCase
from django.urls import reverse

from ecom.mayoristapp_web_views import CompraMayoristaView


class TestCompraMayoristaView(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(email="vend1@example.com", nombre="Vendedor", password="x")
        self.url = reverse("ecom:mayoristapp_venta")
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
        resp = CompraMayoristaView.as_view()(req)
        self.assertEqual(resp.status_code, 302)

    def test_redirige_sin_base_empresa(self):
        req = self._request(self.user, {"user": {"id_usuario": 1}})
        resp = CompraMayoristaView.as_view()(req)
        self.assertEqual(resp.status_code, 302)

    def test_render_redirect_a_masivo_simple(self):
        req = self._request(self.user, {"user": {"base_empresa": "emp1", "id_usuario": 1}})
        resp = CompraMayoristaView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/mayoristapp/pedido-masivo-sucursales/", resp["Location"])
        self.assertIn("modo=simple", resp["Location"])

    def test_redirect_cod_mov_preserva_query(self):
        req = self.factory.get(self.url + "?cod_mov=7")
        req.user = self.user
        req.session = SessionStore()
        req.session["user"] = {"base_empresa": "emp1", "id_usuario": 1}
        req._messages = FallbackStorage(req)
        resp = CompraMayoristaView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        loc = resp["Location"]
        self.assertIn("modo=simple", loc)
        self.assertIn("cod_mov=7", loc)

    def test_redirect_compra_alias_a_masivo_simple(self):
        req = self.factory.get(reverse("ecom:mayoristapp_compra"))
        req.user = self.user
        req.session = SessionStore()
        req.session["user"] = {"base_empresa": "emp1", "id_usuario": 1}
        req._messages = FallbackStorage(req)
        resp = CompraMayoristaView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/mayoristapp/pedido-masivo-sucursales/", resp["Location"])
        self.assertIn("modo=simple", resp["Location"])

    def test_redirect_detalle_a_masivo_simple_cod_mov(self):
        req = self._request(self.user, {"user": {"base_empresa": "emp1", "id_usuario": 1}})
        from ecom.pedido_gestion_views import PedidoDetalleView

        resp = PedidoDetalleView.as_view()(req, cod_mov=7)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/mayoristapp/pedido-masivo-sucursales/", resp["Location"])
        self.assertIn("modo=simple", resp["Location"])
        self.assertIn("cod_mov=7", resp["Location"])

    def test_redirect_venta_url_follow_false_preserva_cod_mov(self):
        req = self.factory.get(self.url + "?cod_mov=42")
        req.user = self.user
        req.session = SessionStore()
        req.session["user"] = {"base_empresa": "emp1", "id_usuario": 1}
        req._messages = FallbackStorage(req)
        resp = CompraMayoristaView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        loc = resp["Location"]
        self.assertIn("/mayoristapp/pedido-masivo-sucursales/", loc)
        self.assertIn("modo=simple", loc)
        self.assertIn("cod_mov=42", loc)
