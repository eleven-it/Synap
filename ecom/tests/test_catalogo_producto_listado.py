"""
Tests para API de listado de artículos del catálogo mayorista.
"""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.catalogo_producto_relay_views import CatalogoArticulosListadoRelayAPIView


def _req_post(path: str, body: dict, session_user: dict, session_extra: dict = None):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    if session_extra:
        for k, v in session_extra.items():
            req.session[k] = v
    req.session.save()
    return req


class TestCatalogoArticulosListadoView(TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_producto_relay_views.listar_articulos_paginado")
    @patch("ecom.catalogo_producto_relay_views.lista_precio_relay_json")
    def test_listado_ok_con_cliente(self, mock_lista_precio, mock_listar):
        mock_lista_precio.return_value = [{"id": 2, "name": "Lista 2", "selected": True}]
        mock_listar.return_value = {
            "items": [
                {
                    "id_articulo": 1,
                    "id_manual": "ART001",
                    "codigo": "COD001",
                    "nombre": "Artículo 1",
                    "rubro": "Rubro 1",
                    "subrubro": "Subrubro 1",
                    "marca": "Marca 1",
                    "precio": 100.0,
                    "stock_disponible": 10.0,
                    "tiene_foto": False,
                    "en_promocion": False,
                }
            ],
            "total": 1,
            "pagina": 1,
            "tam": 20,
            "total_paginas": 1,
        }

        session_user = {"base_empresa": "emp1", "cliente_cod_lista_precio": 2}
        session_extra = {
            "mayoristapp": {
                "idcliente": 123,
                "cliente": [{"descRenglon": 5.0}, {}],
                "iva_incluido": "Si",
            }
        }

        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {"rubro": 1}, "pagina": 1, "tam": 20},
            session_user,
            session_extra,
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["items"]), 1)
        self.assertEqual(resp.data["total"], 1)
        mock_listar.assert_called_once()
        args, kwargs = mock_listar.call_args
        self.assertEqual(kwargs["lista_id"], 2)
        self.assertEqual(kwargs["codigo_cliente"], 123)
        self.assertEqual(kwargs["descuento_cliente"], Decimal("5.0"))
        self.assertTrue(kwargs["iva_incluido"])

    @patch("ecom.catalogo_producto_relay_views.listar_articulos_paginado")
    @patch("ecom.catalogo_producto_relay_views.lista_precio_relay_json")
    def test_listado_sin_cliente_usa_default(self, mock_lista_precio, mock_listar):
        mock_lista_precio.return_value = [{"id": 1, "name": "Lista 1", "selected": True}]
        mock_listar.return_value = {
            "items": [],
            "total": 0,
            "pagina": 1,
            "tam": 20,
            "total_paginas": 0,
        }

        session_user = {"base_empresa": "emp1"}

        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {}, "pagina": 1, "tam": 20},
            session_user,
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        mock_listar.assert_called_once()
        args, kwargs = mock_listar.call_args
        self.assertEqual(kwargs["lista_id"], 1)
        self.assertIsNone(kwargs["codigo_cliente"])

    def test_listado_sin_base_empresa_400(self):
        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {}, "pagina": 1, "tam": 20},
            {},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 403)

    @patch("ecom.catalogo_producto_relay_views.listar_articulos_paginado")
    @patch("ecom.catalogo_producto_relay_views.lista_precio_relay_json")
    def test_listado_paginacion_metadata(self, mock_lista_precio, mock_listar):
        mock_lista_precio.return_value = [{"id": 1, "name": "Lista 1", "selected": True}]
        mock_listar.return_value = {
            "items": [],
            "total": 45,
            "pagina": 2,
            "tam": 20,
            "total_paginas": 3,
        }

        session_user = {"base_empresa": "emp1"}

        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {}, "pagina": 2, "tam": 20},
            session_user,
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["total"], 45)
        self.assertEqual(resp.data["pagina"], 2)
        self.assertEqual(resp.data["total_paginas"], 3)
