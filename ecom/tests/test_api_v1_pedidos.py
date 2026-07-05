"""
Tests API REST v1 — comprobantes pedidos (piloto F0).
"""

from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.api.v1.comprobantes.pedidos import PedidosListV1APIView
from ecom.comprobantes_relay_views import ComprobantesPedidosRelayAPIView


def _api_post(path: str, body: dict, user, session_user: dict):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    force_authenticate(req, user=user)
    return req


class TestApiV1Pedidos(TestCase):
    def setUp(self):
        self.user = MagicMock()
        self.user.is_authenticated = True
        self.user.is_superuser = True
        self.url_v1 = reverse("ecom:v1_comprobantes_pedidos")
        self.url_legacy = reverse("ecom:mayoristapp_comprobantes_pedidos")

    @patch("ecom.api.v1.comprobantes.pedidos.listar_pedidos_relay")
    def test_v1_listado_sin_ajax(self, mock_listar):
        mock_listar.return_value = [{"NroComprobante": "PED-1"}]
        req = _api_post(
            self.url_v1,
            {"campo_busca": "fecha", "fecha_desde": "01/01/2026", "fecha_hasta": "31/01/2026"},
            self.user,
            {"base_empresa": "emp1", "id_usuario": 1},
        )
        resp = PedidosListV1APIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(resp.data["total"], 1)
        mock_listar.assert_called_once()
        body = mock_listar.call_args[0][1]
        self.assertEqual(body.get("campoBusca"), "fecha")

    def test_v1_sin_base_empresa(self):
        req = _api_post(self.url_v1, {}, self.user, {"id_usuario": 1})
        resp = PedidosListV1APIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.data["ok"])

    @patch("ecom.comprobantes_relay_views.listar_pedidos_relay")
    def test_legacy_deprecation_header(self, mock_listar):
        mock_listar.return_value = []
        req = _api_post(self.url_legacy + "?ajax=1", {}, self.user, {"base_empresa": "emp1"})
        resp = ComprobantesPedidosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get("Deprecation"), "true")
        self.assertIn("successor-version", resp.get("Link", ""))

    @patch("ecom.api.v1.comprobantes.pedidos.sugerencias_nro_comp_relay")
    def test_v1_sugerencias_numero(self, mock_sug):
        from ecom.api.v1.comprobantes.pedidos import PedidosSugerenciasNumeroV1APIView

        mock_sug.return_value = ["PED-001", "PED-002"]
        url = reverse("ecom:v1_comprobantes_pedidos_sugerencias")
        factory = APIRequestFactory()
        req = factory.get(url + "?q=PED", format="json")
        middleware = SessionMiddleware(lambda r: HttpResponse())
        middleware.process_request(req)
        req.session["user"] = {"base_empresa": "emp1", "id_usuario": 1}
        req.session.save()
        force_authenticate(req, user=self.user)
        resp = PedidosSugerenciasNumeroV1APIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
        self.assertEqual(resp.data["total"], 2)
        self.assertEqual(len(resp.data["results"]), 2)
