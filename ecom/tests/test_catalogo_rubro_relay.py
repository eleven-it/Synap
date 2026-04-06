# Tests relay catálogo rubro (paridad relay-rubro.php).

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.catalogo_relay_views import (
    CatalogoArticulosAutocompleteAPIView,
    CatalogoFiltroRubroCatalogoAPIView,
    CatalogoLaboratoriosRelayAPIView,
    CatalogoLotesRelayAPIView,
    CatalogoMarcasRelayAPIView,
    CatalogoMasVendidosRelayAPIView,
    CatalogoProveedoresRelayAPIView,
    CatalogoRubrosRelayAPIView,
    CatalogoSubrubrosRelayAPIView,
    CatalogoSubrubrosTipoClienteRelayAPIView,
    CatalogoTaccRelayAPIView,
)


def _req_get(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


def _req_post_json(path: str, body: dict, session_user: dict):
    factory = APIRequestFactory()
    req = factory.post(path, body, format="json")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestCatalogoRubrosRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    def test_sin_ajax_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/rubros/",
            {"idcategoria": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoRubrosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("ecom.catalogo_relay_views.list_rubros_por_categoria")
    def test_ok(self, mock_list):
        mock_list.return_value = [{"id": "", "name": "- todos -"}, {"id": 5, "name": "X"}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/rubros/",
            {"idcategoria": "3", "ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoRubrosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_list.assert_called_once_with("emp1", 3)


class TestCatalogoSubrubrosRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_relay_views.list_subrubros_por_rubro")
    def test_ok(self, mock_list):
        mock_list.return_value = [{"id": 10, "name": "Sr A"}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/subrubros/",
            {"idrubro": "7", "ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoSubrubrosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_list.assert_called_once_with("emp1", 7)


class TestCatalogoRubroService(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch("ecom.services.catalogo_rubro.get_mysql_pool")
    def test_list_rubros_incluye_todos(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [("id",), ("name",)]
        self.mock_cursor.fetchall.return_value = [(10, "ab cd")]

        from ecom.services.catalogo_rubro import list_rubros_por_categoria

        out = list_rubros_por_categoria("dbx", 2)
        self.assertEqual(out[0], {"id": "", "name": "- todos -"})
        self.assertEqual(out[1]["id"], 10)
        self.mock_cursor.execute.assert_called_once()
        self.assertEqual(self.mock_cursor.execute.call_args[0][1], [2])


class TestCatalogoFiltroRubroCatalogo(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_relay_views.guardar_filtro_catalogo_rubro")
    def test_post_ok(self, mock_save):
        req = _req_post_json(
            "/ecom/api/mayoristapp/catalogo/filtro-rubro-catalogo/",
            {"idr": 99},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoFiltroRubroCatalogoAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "ok")
        mock_save.assert_called_once()


class TestCatalogoArticulosAutocomplete(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    def test_sin_autocomplete_400(self):
        req = _req_post_json(
            "/ecom/api/mayoristapp/catalogo/articulos/autocomplete/",
            {"term": "x"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosAutocompleteAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("ecom.catalogo_relay_views.search_articulos_autocomplete")
    def test_ok(self, mock_search):
        mock_search.return_value = [{"id": 1, "label": "A - B", "value": "A"}]
        req = _req_post_json(
            "/ecom/api/mayoristapp/catalogo/articulos/autocomplete/",
            {"autocomplete": 1, "term": "ab"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoArticulosAutocompleteAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_search.assert_called_once_with("emp1", "ab")


class TestCatalogoSubrubrosTipoCliente(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_relay_views.list_subrubros_maestro_por_rubro")
    def test_sin_tipo_cliente(self, mock_fn):
        mock_fn.return_value = [{"id": 1, "name": "S"}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/subrubros-tipo-cliente/",
            {"idrubro": "3", "ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoSubrubrosTipoClienteRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1", 3)

    @patch("ecom.catalogo_relay_views.list_subrubros_por_rubro_y_tipo_cliente")
    def test_con_tipo_cliente(self, mock_fn):
        mock_fn.return_value = []
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/subrubros-tipo-cliente/",
            {"idrubro": "3", "tipoCliente": "2", "ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoSubrubrosTipoClienteRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1", 3, 2)


class TestCatalogoMarcasRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    def test_sin_ajax_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/marcas/",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoMarcasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("ecom.catalogo_relay_views.list_marcas_catalogo_ecommerce")
    def test_ok(self, mock_fn):
        mock_fn.return_value = [{"id": 1, "name": "Marca A"}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/marcas/",
            {"ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoMarcasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1")


class TestCatalogoLaboratoriosRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_relay_views.list_laboratorios_catalogo_ecommerce")
    def test_ok(self, mock_fn):
        mock_fn.return_value = [{"id": 2, "name": "Lab X"}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/laboratorios/",
            {"ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoLaboratoriosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1")


class TestCatalogoProveedoresRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_relay_views.list_proveedores_catalogo_ecommerce")
    def test_ok(self, mock_fn):
        mock_fn.return_value = [{"id": 10, "name": "Prov"}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/proveedores/",
            {"ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoProveedoresRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1")


class TestCatalogoMaestrosService(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch("ecom.services.catalogo_maestros.get_mysql_pool")
    def test_list_marcas_ejecuta_sql(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [("id",), ("name",)]
        self.mock_cursor.fetchall.return_value = [(5, "marca z")]

        from ecom.services.catalogo_maestros import list_marcas_catalogo_ecommerce

        out = list_marcas_catalogo_ecommerce("dbx")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], 5)
        self.assertEqual(out[0]["name"], "Marca Z")
        self.mock_cursor.execute.assert_called_once()


class TestCatalogoLotesRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    def test_sin_id_art_400(self):
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/lotes/",
            {"ajax": "1", "idDeposito": "2"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoLotesRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("ecom.catalogo_relay_views.list_lotes_por_articulo_deposito")
    def test_ok(self, mock_fn):
        mock_fn.return_value = [{"id_lote": 1, "valor_seleccion": "1|10.0"}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/lotes/",
            {"ajax": "1", "idArt": "99", "idDeposito": "3"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoLotesRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once_with("emp1", 99, 3)


class TestCatalogoTaccRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_relay_views.tacc_relay_payload")
    def test_ok(self, mock_fn):
        mock_fn.return_value = {"mensaje": "ok", "valores": [{"id": "Si", "name": "Si"}]}
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/tacc-opciones/",
            {"ajax": "1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoTaccRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["mensaje"], "ok")
        mock_fn.assert_called_once_with("emp1")


class TestCatalogoMasVendidosRelayView(unittest.TestCase):
    def _user(self):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        return u

    @patch("ecom.catalogo_relay_views.list_mas_vendidos_ecommerce")
    def test_ok(self, mock_fn):
        mock_fn.return_value = [{"id_art": 1, "cuantos": 5}]
        req = _req_get(
            "/ecom/api/mayoristapp/catalogo/mas-vendidos/",
            {"ajax": "1", "idrubro": "7", "limit": "10"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user())
        resp = CatalogoMasVendidosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_fn.assert_called_once()
        ca = mock_fn.call_args
        self.assertEqual(ca[0][0], "emp1")
        self.assertEqual(ca[1]["limit"], 10)
        self.assertEqual(ca[1]["id_rubro"], 7)


class TestCatalogoMasVendidosParse(unittest.TestCase):
    def test_parse_limit(self):
        from ecom.services.catalogo_mas_vendidos import parse_limit_mas_vendidos

        class Q:
            def __init__(self, d):
                self._d = d

            def get(self, k, default=None):
                return self._d.get(k, default)

        self.assertEqual(parse_limit_mas_vendidos(Q({})), 15)
        self.assertEqual(parse_limit_mas_vendidos(Q({"limit": "100"})), 50)
        self.assertEqual(parse_limit_mas_vendidos(Q({"limit": "5"})), 5)
