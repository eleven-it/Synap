"""Tests servicio/API ternas Vendedor→Cliente→Marca."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from ecom.services.vendedor_cliente_marca import (
    ConflictoMarcaCliente,
    anular_terna,
    crear_terna,
)
from ecom.vendedor_cliente_marca_views import (
    VendedorClienteMarcaAnularAPIView,
    VendedorClienteMarcaCrearAPIView,
)


class _User:
    is_authenticated = True
    is_superuser = True

    def tiene_permiso(self, _codigo):
        return True


class TestCrearTernaConflicto(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca.buscar_dueno_marca_cliente")
    def test_conflicto_otro_viajante(self, mock_dueno):
        mock_dueno.return_value = {
            "id": 1,
            "CodViajante": 5,
            "id_cliente": 10,
            "CodMarca": 2,
            "nombre_viajante": "Pérez",
        }
        with self.assertRaises(ConflictoMarcaCliente) as ctx:
            crear_terna("emp1", 9, 10, 2, usuario_mod="test")
        self.assertEqual(ctx.exception.dueno["CodViajante"], 5)
        self.assertIn("Pérez", ctx.exception.message)

    @patch("ecom.services.vendedor_cliente_marca.buscar_dueno_marca_cliente")
    def test_idempotente_mismo_viajante(self, mock_dueno):
        mock_dueno.return_value = {
            "id": 1,
            "CodViajante": 9,
            "id_cliente": 10,
            "CodMarca": 2,
            "nombre_viajante": "Yo",
        }
        ok, msg, terna = crear_terna("emp1", 9, 10, 2)
        self.assertTrue(ok)
        self.assertEqual(terna["CodViajante"], 9)


class TestAnularTerna(SimpleTestCase):
    @patch("ecom.services.vendedor_cliente_marca.get_mysql_pool")
    def test_anular_ok(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.rowcount = 1
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        ok, msg = anular_terna("emp1", 3, usuario_mod="u")
        self.assertTrue(ok)
        self.assertIn("anulada", msg.lower())


class TestApiCrear409(TestCase):
    @patch("ecom.vendedor_cliente_marca_views.crear_terna")
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_post_conflicto_409(self, _base, mock_crear):
        mock_crear.side_effect = ConflictoMarcaCliente(
            "La marca ya está asignada a Pérez para este cliente.",
            {"CodViajante": 5, "nombre_viajante": "Pérez", "id": 1},
        )
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/crear/",
            {"CodViajante": 9, "id_cliente": 10, "CodMarca": 2},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaCrearAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data["code"], "conflicto_marca")
        self.assertEqual(resp.data["dueno"]["CodViajante"], 5)

    @patch("ecom.vendedor_cliente_marca_views.anular_terna", return_value=(True, "Terna anulada."))
    @patch("ecom.vendedor_cliente_marca_views._session_base_empresa", return_value="emp1")
    def test_anular_ok(self, _base, _anular):
        factory = APIRequestFactory()
        req = factory.post(
            "/ecom/api/mayoristapp/vendedor-cliente-marca/anular/",
            {"id": 7},
            format="json",
        )
        req.session = {"user": {"base_empresa": "emp1"}}
        force_authenticate(req, user=_User())
        resp = VendedorClienteMarcaAnularAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["ok"])
