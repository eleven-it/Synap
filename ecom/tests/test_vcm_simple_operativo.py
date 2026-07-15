# Tests VCM pedido simple vs masivo con viajante operativo (REQ-VCM-04/05, CAT-004/006).

import unittest
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.catalogo_producto_relay_views import CatalogoArticulosListadoRelayAPIView
from ecom.cliente_relay_views import ClienteSeleccionarRelayAPIView
from ecom.services.pedido_masivo_matriz import listar_clientes_con_ternas
from ecom.services.vendedor_asignacion_sql import vcm_ternas_disponible, where_vendedor_cliente


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.is_superuser = False
    return u


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


def _req_post(path: str, body: dict, session_user: dict, session_extra: dict | None = None):
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


class TestWhereVendedorClienteVcm(unittest.TestCase):
    @patch("ecom.services.vendedor_asignacion_sql.vcm_ternas_disponible", return_value=True)
    def test_operativo_usa_solo_terna_efectiva(self, _vcm):
        sess = {
            "todos_clientes": "No",
            "supervisor_venta": "Si",
            "id_vendedor_usr": 10,
            "vendedor_a_cargo": [10, 21, 49],
            "cod_viajante_operativo": 21,
        }
        sql, params = where_vendedor_cliente("emp1", sess, fuente="legacy")
        self.assertIn("ecom_vendedor_cliente_marca", sql)
        self.assertEqual(params, [21])
        self.assertNotIn("cliente.CodViajante IN", sql)

    @patch("ecom.services.vendedor_asignacion_sql.vcm_ternas_disponible", return_value=False)
    def test_legacy_supervisor_sin_vcm_mantiene_cargo(self, _vcm):
        sess = {
            "todos_clientes": "No",
            "supervisor_venta": "Si",
            "id_vendedor_usr": 10,
            "vendedor_a_cargo": [21, 49],
        }
        sql, params = where_vendedor_cliente("emp1", sess, fuente="legacy")
        self.assertIn("cliente.CodViajante IN", sql)
        self.assertEqual(params, [10, 21, 49])


class TestParidadSimpleMasivo(unittest.TestCase):
    @patch("ecom.services.cliente_relay.get_mysql_pool")
    @patch("ecom.services.pedido_masivo_matriz.get_mysql_pool")
    @patch("ecom.services.vendedor_asignacion_sql.vcm_ternas_disponible", return_value=True)
    def test_mismo_viajante_operativo_en_busquedas(self, _vcm, mock_pool_masivo, mock_pool_relay):
        cur_m = mock_pool_masivo.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value
        cur_m.fetchall.return_value = [(100, "Cliente A")]

        cur_a = mock_pool_relay.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value
        cur_a.description = [
            ("nombre_cliente",),
            ("codigo",),
            ("estado",),
            ("saldo",),
            ("telefono",),
            ("lista_precio",),
            ("email",),
            ("email_contacto",),
            ("id_manual_cli",),
            ("cod_viajante",),
            ("nombre_tipo_cliente",),
            ("condicion_iva",),
        ]
        cur_a.fetchall.return_value = [
            ("Cliente A", 100, "Activo", 0, "", "Lista 1", "", "", "", 21, "", ""),
        ]

        from ecom.services.cliente_relay import buscar_clientes_relay

        sess = {
            "todos_clientes": "No",
            "supervisor_venta": "Si",
            "id_vendedor_usr": 10,
            "vendedor_a_cargo": [10, 21],
            "cod_viajante_operativo": 21,
        }
        rows_m = listar_clientes_con_ternas("emp1", 21, q="Cliente")
        rows_s, err = buscar_clientes_relay(
            "emp1",
            modo_busqueda="texto",
            patron_texto="Cliente",
            codigo_cliente="",
            sess_user=sess,
            limit=10,
        )
        self.assertIsNone(err)
        self.assertEqual(len(rows_m), 1)
        self.assertEqual(rows_m[0]["id_cliente"], 100)
        self.assertEqual(len(rows_s), 1)
        self.assertEqual(rows_s[0]["codigo"], 100)

        sql_asig = cur_a.execute.call_args[0][0]
        self.assertIn("ecom_vendedor_cliente_marca", sql_asig)
        self.assertEqual(cur_a.execute.call_args[0][1], ["%Cliente%", "%Cliente%", 21, 10])


class TestCatalogoVcmSimple(unittest.TestCase):
    def _user(self):
        return _user()

    @patch("ecom.catalogo_producto_relay_views.vcm_ternas_disponible", return_value=True)
    def test_sin_cliente_400(self, _vcm):
        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {}, "pagina": 1, "tam": 20},
            {"base_empresa": "emp1", "id_vendedor_usr": 21},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("cliente", resp.data["detail"].lower())

    @patch("ecom.catalogo_producto_relay_views._session_user")
    @patch("ecom.catalogo_producto_relay_views.resolver_viajante_operativo", return_value=21)
    @patch("ecom.catalogo_producto_relay_views.listar_articulos_paginado")
    @patch("ecom.catalogo_producto_relay_views.marcas_asignadas_viajante_cliente", return_value=[5, 7])
    @patch("ecom.catalogo_producto_relay_views.vcm_ternas_disponible", return_value=True)
    def test_aplica_marcas_terna_operativo(self, _vcm, _marcas, mock_listar, _resolver, mock_sess):
        mock_sess.return_value = {
            "id_vendedor_usr": 10,
            "supervisor_venta": "Si",
            "vendedor_a_cargo": [10, 21],
            "cod_viajante_operativo": 21,
        }
        mock_listar.return_value = {
            "items": [],
            "total": 0,
            "pagina": 1,
            "tam": 20,
            "total_paginas": 0,
        }
        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {"q": "art"}, "pagina": 1, "tam": 20},
            {
                "base_empresa": "emp1",
                "id_vendedor_usr": 10,
                "supervisor_venta": "Si",
                "vendedor_a_cargo": [10, 21],
            },
            {"mayoristapp": {"idcliente": 50, "cod_viajante_operativo": 21}},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        filtros = mock_listar.call_args.kwargs["filtros"]
        self.assertEqual(filtros.get("marcas"), [5, 7])
        _marcas.assert_called_once_with("emp1", 21, 50, None)

    @patch("ecom.catalogo_producto_relay_views.listar_articulos_paginado")
    @patch("ecom.catalogo_producto_relay_views.vcm_ternas_disponible", return_value=True)
    def test_rechaza_override_lista(self, _vcm, mock_listar):
        mock_listar.return_value = {
            "items": [],
            "total": 0,
            "pagina": 1,
            "tam": 20,
            "total_paginas": 0,
        }
        req = _req_post(
            "/ecom/api/mayoristapp/catalogo/articulos/listado/",
            {"filtros": {}, "lista_id": 9, "pagina": 1, "tam": 20},
            {"base_empresa": "emp1", "id_vendedor_usr": 21},
            {"mayoristapp": {"idcliente": 50}},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosListadoRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("lista", resp.data["detail"].lower())
        mock_listar.assert_not_called()


class TestClienteSeleccionListaPrecio(unittest.TestCase):
    def _user(self):
        return _user()

    @patch("ecom.cliente_relay_views._session_user")
    @patch("ecom.cliente_relay_views.resolver_viajante_operativo", return_value=21)
    @patch("ecom.cliente_relay_views._url_pdf_lista_precio", return_value="http://test/lista.pdf")
    @patch("ecom.cliente_relay_views.lista_precio_relay_json")
    @patch("ecom.cliente_relay_views.guardar_cliente_seleccion_mayoristapp")
    @patch("ecom.cliente_relay_views.construir_payload_cliente_seleccionado")
    @patch("ecom.cliente_relay_views.cliente_accesible_por_sesion", return_value=True)
    def test_payload_lista_y_pdf(self, _acc, mock_payload, _guardar, mock_listas, _url, _resolver, mock_sess):
        mock_sess.return_value = {
            "base_empresa": "emp1",
            "id_vendedor_usr": 21,
            "supervisor_venta": "Si",
            "vendedor_a_cargo": [10, 21],
            "cod_viajante_operativo": 21,
        }
        mock_listas.return_value = [{"id": 3, "name": "Lista 3 Distribuidor", "selected": True}]
        mock_payload.return_value = (
            {"Codigo": 8, "listaPrecio": "Lista 3", "codListaPrecio": "3"},
            {},
            [],
            "si",
        )
        req = _req_post(
            "/ecom/api/mayoristapp/clientes/seleccionar/?ajax=1",
            {"codigo": "8"},
            {
                "base_empresa": "emp1",
                "id_vendedor_usr": 21,
                "supervisor_venta": "Si",
                "vendedor_a_cargo": [10, 21],
            },
            {"mayoristapp": {"cod_viajante_operativo": 21}},
        )
        force_authenticate(req, user=self._user())
        resp = ClienteSeleccionarRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["listaPrecio"]["codigo"], 3)
        self.assertIn("Distribuidor", resp.data["listaPrecio"]["nombre"])
        self.assertTrue(resp.data["listaPrecio"]["solo_lectura"])
        self.assertEqual(resp.data["lista_precio_pdf_url"], "http://test/lista.pdf")
        mock_payload.assert_called_once()
        self.assertEqual(mock_payload.call_args[0][2], 21)


class TestVcmTernasDisponible(unittest.TestCase):
    @patch("ecom.services.vendedor_asignacion_sql.leer_valor_configuracion_ecom", return_value="Si")
    def test_config_si(self, _cfg):
        self.assertTrue(vcm_ternas_disponible("emp_x"))

    @patch("ecom.services.vendedor_asignacion_sql.get_mysql_pool")
    @patch("ecom.services.vendedor_asignacion_sql.leer_valor_configuracion_ecom", return_value="auto")
    def test_auto_con_ternas(self, _cfg, mock_pool):
        vcm_ternas_disponible.__globals__["_vcm_disponible_cache"].clear()
        cur = mock_pool.return_value.get_connection.return_value.__enter__.return_value.cursor.return_value
        cur.fetchone.return_value = (1,)
        self.assertTrue(vcm_ternas_disponible("emp_y"))
