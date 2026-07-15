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
    @patch("ecom.catalogo_producto_relay_views.vcm_ternas_disponible", return_value=False)
    def test_listado_ok_con_cliente(self, _vcm, mock_lista_precio, mock_listar):
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
    @patch("ecom.catalogo_producto_relay_views.vcm_ternas_disponible", return_value=False)
    def test_listado_sin_cliente_usa_default(self, _vcm, mock_lista_precio, mock_listar):
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
    @patch("ecom.catalogo_producto_relay_views.vcm_ternas_disponible", return_value=False)
    def test_listado_paginacion_metadata(self, _vcm, mock_lista_precio, mock_listar):
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


class TestConstruirWhereCatalogo(unittest.TestCase):
    def test_busqueda_tpv_mantiene_ecommerce_y_campos_tpv(self):
        from ecom.services.catalogo_producto import _construir_where_catalogo

        where, params = _construir_where_catalogo({"busqueda_tpv": True, "q": "ma"})
        self.assertIn("ecommerce = 'Si'", where)
        self.assertIn("Discontinuo = 'No'", where)
        self.assertIn("NroCodBarra", where)
        self.assertEqual(len(params), 6)

    def test_filtro_marcas_multiple(self):
        from ecom.services.catalogo_producto import _construir_where_catalogo

        where, params = _construir_where_catalogo({"marcas": [1, 2, "3"]})
        self.assertIn("CodigoMarca IN", where)
        self.assertEqual(params[-3:], [1, 2, 3])

    def test_catalogo_ecommerce_mantiene_filtros(self):
        from ecom.services.catalogo_producto import _construir_where_catalogo

        where, params = _construir_where_catalogo({"q": "ma"})
        self.assertIn("ecommerce = 'Si'", where)
        self.assertIn("Discontinuo = 'No'", where)
        self.assertEqual(len(params), 3)


class TestCatalogoListadoBusquedaTpv(TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_producto_relay_views.aplicar_restricciones_a_filtros")
    @patch("ecom.catalogo_producto_relay_views.listar_articulos_paginado")
    @patch("ecom.catalogo_producto_relay_views.lista_precio_relay_json")
    @patch("ecom.catalogo_producto_relay_views.vcm_ternas_disponible", return_value=False)
    def test_listado_busqueda_tpv_aplica_restricciones_pv(
        self, _vcm, mock_lista_precio, mock_listar, mock_restricciones
    ):
        mock_lista_precio.return_value = [{"id": 1, "name": "Lista 1", "selected": True}]
        mock_listar.return_value = {"items": [], "total": 0, "pagina": 1, "tam": 25, "total_paginas": 0}
        mock_restricciones.side_effect = lambda f, *a: dict(f or {})

        session_user = {"base_empresa": "emp1"}
        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {"busqueda_tpv": True, "q": "ma", "marcas": [5, 7]}, "pagina": 1, "tam": 25},
            session_user,
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        mock_restricciones.assert_called_once()
        filtros = mock_listar.call_args.kwargs["filtros"]
        self.assertTrue(filtros.get("busqueda_tpv"))
        self.assertEqual(filtros.get("marcas"), [5, 7])


class TestListarArticulosPaginadoBusquedaTpv(unittest.TestCase):
    @patch("ecom.services.catalogo_producto.opciones_presentacion_articulo")
    @patch("ecom.services.catalogo_producto.StockService")
    @patch("ecom.services.catalogo_producto.calcular_precio_articulo_row")
    @patch("ecom.services.catalogo_producto.resolver_reglas_precio_map")
    @patch("ecom.services.catalogo_producto._mysql_conn")
    def test_busqueda_tpv_omite_count_y_presentacion(
        self, mock_mysql_conn, mock_reglas_map, mock_precio, mock_stock_cls, mock_presentacion
    ):
        from ecom.services.catalogo_producto import listar_articulos_paginado

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_mysql_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_mysql_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_cur.description = [
            ("IDArt",), ("id_manual",), ("CodigoArticuloT",), ("NombreArticulo",),
            ("Precio1V",), ("Precio2V",), ("Precio3V",), ("Precio4V",), ("Precio5V",),
            ("PNOficial",), ("impuesto_interno",), ("CodigoProveedor",), ("CodigoRubro",),
            ("IDSubRubro",), ("promocion",), ("promocion_por",), ("promocion_cant",),
            ("promocion_tipo",), ("promocion_alcance",), ("promocion_lista1",),
            ("promocion_lista2",), ("promocion_lista3",), ("promocion_lista4",),
            ("promocion_lista5",), ("promocion_listaoficial",), ("promocion_vigencia_desde",),
            ("promocion_vigencia_hasta",), ("alic_iva",),
        ]
        mock_cur.fetchone.side_effect = None
        mock_cur.fetchall.return_value = [
            (
                10, "A1", "C1", "Art 1",
                100, 0, 0, 0, 0, 0, 0, 1, 2, 3,
                "No", 0, 0, "", "", "No", "No", "No", "No", "No", "No",
                None, None, 21,
            )
        ]

        mock_stock_cls.return_value.get_disponible_map.return_value = {10: Decimal("5")}
        mock_reglas_map.return_value = {}
        mock_precio.return_value = Decimal("99")

        resultado = listar_articulos_paginado(
            "emp1",
            filtros={"busqueda_tpv": True, "q": "art"},
            lista_id=1,
            codigo_cliente=123,
            descuento_cliente=Decimal("0"),
            iva_incluido=True,
            id_deposito=1,
            pagina=1,
            tam=25,
        )

        self.assertEqual(len(resultado["items"]), 1)
        self.assertEqual(resultado["items"][0]["presentacion"]["tipo_unidad_defecto"], "Unidad")
        mock_presentacion.assert_not_called()
        self.assertEqual(mock_cur.execute.call_count, 1)
        mock_reglas_map.assert_called_once()
        mock_precio.assert_called_once()
        args, kwargs = mock_precio.call_args
        self.assertFalse(kwargs.get("resolver_regla"))
