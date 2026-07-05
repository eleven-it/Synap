"""
Tests para API de detalle de artículo del catálogo mayorista.
"""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.catalogo_producto_relay_views import CatalogoArticuloDetalleRelayAPIView


def _req_get(path: str, session_user: dict, session_extra: dict = None):
    factory = APIRequestFactory()
    req = factory.get(path)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    return req


class TestCatalogoArticuloDetalleView(TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_producto_relay_views.obtener_detalle_articulo")
    @patch("ecom.catalogo_producto_relay_views.lista_precio_relay_json")
    def test_detalle_ok(self, mock_lista_precio, mock_detalle):
        mock_lista_precio.return_value = [{"id": 2, "name": "Lista 2", "selected": True}]
        mock_detalle.return_value = {
            "id_articulo": 1,
            "id_manual": "ART001",
            "codigo": "COD001",
            "nombre": "Artículo 1",
            "descripcion": "Descripción del artículo",
            "rubro": "Rubro 1",
            "subrubro": "Subrubro 1",
            "marca": "Marca 1",
            "precio": 100.0,
            "precio_neto": 90.0,
            "stock_disponible": 10.0,
            "stock_depositos": [
                {
                    "id_deposito": 1,
                    "nombre_deposito": "Depósito 1",
                    "saldo": 15.0,
                    "saldo_pedido": 5.0,
                    "disponible": 10.0,
                }
            ],
            "tiene_foto": False,
            "promocion": None,
        }

        session_user = {"base_empresa": "emp1", "cliente_cod_lista_precio": 2}
        session_extra = {
            "mayoristapp": {
                "idcliente": 123,
                "cliente": [{"descRenglon": 5.0}, {}],
                "iva_incluido": "Si",
            }
        }

        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/articulos/1/detalle/",
            session_user,
            session_extra,
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticuloDetalleRelayAPIView.as_view()(req, idart=1)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id_articulo"], 1)
        self.assertEqual(resp.data["nombre"], "Artículo 1")
        self.assertEqual(len(resp.data["stock_depositos"]), 1)
        mock_detalle.assert_called_once()

    @patch("ecom.catalogo_producto_relay_views.obtener_detalle_articulo")
    @patch("ecom.catalogo_producto_relay_views.lista_precio_relay_json")
    def test_detalle_con_promocion(self, mock_lista_precio, mock_detalle):
        mock_lista_precio.return_value = [{"id": 1, "name": "Lista 1", "selected": True}]
        mock_detalle.return_value = {
            "id_articulo": 2,
            "id_manual": "ART002",
            "codigo": "COD002",
            "nombre": "Artículo 2",
            "descripcion": "Artículo en promoción",
            "rubro": "Rubro 1",
            "subrubro": "Subrubro 1",
            "marca": "Marca 1",
            "precio": 80.0,
            "precio_neto": 70.0,
            "stock_disponible": 20.0,
            "stock_depositos": [],
            "tiene_foto": False,
            "promocion": {
                "tipo": "Importe descuento",
                "por": 15.0,
                "cant": 0,
                "alcance": "General",
                "vigencia_desde": "01/01/2026",
                "vigencia_hasta": "31/12/2026",
            },
        }

        session_user = {"base_empresa": "emp1"}

        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/articulos/2/detalle/",
            session_user,
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticuloDetalleRelayAPIView.as_view()(req, idart=2)

        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.data["promocion"])
        self.assertEqual(resp.data["promocion"]["tipo"], "Importe descuento")
        self.assertEqual(resp.data["promocion"]["por"], 15.0)

    @patch("ecom.catalogo_producto_relay_views.obtener_detalle_articulo")
    @patch("ecom.catalogo_producto_relay_views.lista_precio_relay_json")
    def test_detalle_no_encontrado_404(self, mock_lista_precio, mock_detalle):
        mock_lista_precio.return_value = [{"id": 1, "name": "Lista 1", "selected": True}]
        mock_detalle.return_value = None

        session_user = {"base_empresa": "emp1"}

        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/articulos/999/detalle/",
            session_user,
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticuloDetalleRelayAPIView.as_view()(req, idart=999)

        self.assertEqual(resp.status_code, 404)

    def test_detalle_sin_base_empresa_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/articulos/1/detalle/",
            {},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticuloDetalleRelayAPIView.as_view()(req, idart=1)
        self.assertEqual(resp.status_code, 403)
