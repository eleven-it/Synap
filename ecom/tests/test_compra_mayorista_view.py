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

    def test_render_ok_con_sesion(self):
        req = self._request(self.user, {"user": {"base_empresa": "emp1", "id_usuario": 1}})
        resp = CompraMayoristaView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        resp.render()
        html = resp.content.decode()
        self.assertIn("Pedido de venta", html)
        self.assertIn("compra-mayorista-urls", html)
        self.assertIn("compra-mayorista-pedido-bootstrap", html)
        self.assertIn("compraMayorista", html)
        self.assertIn("ecom/js/compra_mayorista_app.mjs", html)
        self.assertIn("heroPedidoSub", html)
        self.assertIn('id="compra_cliente_search"', html)
        self.assertIn(reverse("ecom:mayoristapp_catalogo_articulos_listado"), html)
        self.assertIn(reverse("ecom:mayoristapp_checkout_confirmar"), html)
        self.assertIn(reverse("ecom:mayoristapp_lista_precios_pdf"), html)
        self.assertIn(reverse("ecom:mayoristapp_carrito_tipo_comprobante"), html)
        self.assertIn(reverse("ecom:mayoristapp_comprobante_detalle", args=[0]), html)
        self.assertIn(reverse("ecom:mayoristapp_venta_contexto"), html)
        self.assertIn("solicitarCambiarTipo('PRE')", html)
        self.assertIn("pedidos-dialog-panel", html)
        self.assertIn("solicitarVaciar()", html)
        self.assertIn("compra-toggle-shell", html)
        self.assertIn("pedidos-linea-card", html)
        self.assertIn("toggleSummaryMobile()", html)
        self.assertIn("pedidos-aria-live", html)
        self.assertIn('role="tablist"', html)
        self.assertIn('aria-haspopup="listbox"', html)

    def test_redirect_compra_alias_a_venta(self):
        from django.test import Client

        c = Client()
        resp = c.get(reverse("ecom:mayoristapp_compra"))
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/mayoristapp/venta/", resp.url)

    def test_redirect_detalle_a_venta_cod_mov(self):
        from django.test import Client

        c = Client()
        # Sin sesión redirige a login vía mixin; usamos vista directa
        req = self._request(self.user, {"user": {"base_empresa": "emp1", "id_usuario": 1}})
        from ecom.pedido_gestion_views import PedidoDetalleView

        resp = PedidoDetalleView.as_view()(req, cod_mov=7)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/mayoristapp/venta/", resp["Location"])
        self.assertIn("cod_mov=7", resp["Location"])
