# Tests relays precios (lista-precio, promociones).

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from ecom.precio_relay_views import ListaPrecioRelayAPIView, PromocionesRelayAPIView


def _req_get(path: str, query: dict, session_user: dict, session_extra: dict | None = None):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    return req


class TestListaPrecioRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.precio_relay_views.lista_precio_relay_json")
    def test_ok_sin_cod_sesion(self, mock_fn):
        mock_fn.return_value = [{"id": 1, "name": "Lista 1 X", "selected": True}]
        req = _req_get(
            "/ecom/api/mayoristapp/precios/lista-precio/",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ListaPrecioRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1", cod_lista_precio_cliente=None)

    @patch("ecom.precio_relay_views.lista_precio_relay_json")
    def test_cod_query(self, mock_fn):
        mock_fn.return_value = []
        req = _req_get(
            "/ecom/api/mayoristapp/precios/lista-precio/",
            {"cod_lista_cliente": "3"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = ListaPrecioRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1", cod_lista_precio_cliente=3)


class TestPromocionesRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    def test_sin_ajax_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/precios/promociones/",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = PromocionesRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("ecom.precio_relay_views.promociones_relay_payload")
    def test_ok(self, mock_fn):
        mock_fn.return_value = {"articulos": [], "intervalos_por_articulo": {}}
        req = _req_get(
            "/ecom/api/mayoristapp/precios/promociones/",
            {"ajax": "1", "rubro": "5", "listaPrecio": "Lista 2"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = PromocionesRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once()
        kw = mock_fn.call_args[1]
        self.assertEqual(kw["id_rubro"], 5)
        self.assertEqual(kw["lista_precio_cliente"], "Lista 2")


class TestPrecioRelaysHelpers(unittest.TestCase):
    def test_columna_promocion(self):
        from ecom.services.precio_relays import columna_promocion_articulo

        self.assertEqual(columna_promocion_articulo("Lista Oficial"), "promocion_listaoficial")
        self.assertEqual(columna_promocion_articulo("Lista 1"), "promocion_lista1")
        self.assertIsNone(columna_promocion_articulo(None))
