# Tests vendedor operativo mayoristapp (REQ-VOP-*).

import unittest
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory

from ecom.checkout_relay_views import _session_cod_viajante
from ecom.services.vendedor_operativo import (
    cartera_permitida,
    cartera_permitida_legacy,
    guardar_cod_viajante_operativo,
    leer_vendedores_a_cargo_config,
    normalizar_lista_cod_viajantes,
    resolver_viajante_operativo,
    reset_cod_viajante_operativo,
)


class TestNormalizarListaCodViajantes(unittest.TestCase):
    def test_json_array(self):
        self.assertEqual(normalizar_lista_cod_viajantes("[10, 49, 46]"), [10, 49, 46])

    def test_lista_python(self):
        self.assertEqual(normalizar_lista_cod_viajantes([10, "49"]), [10, 49])

    def test_vacio(self):
        self.assertEqual(normalizar_lista_cod_viajantes(""), [])


class TestResolverViajanteOperativo(unittest.TestCase):
    def test_default_sin_operativo(self):
        ctx = {"id_vendedor_usr": 42}
        self.assertEqual(resolver_viajante_operativo(ctx), 42)

    def test_operativo_valido_en_cartera(self):
        ctx = {
            "id_vendedor_usr": 10,
            "supervisor_venta": "Si",
            "vendedor_a_cargo": [20, 21],
            "cod_viajante_operativo": 21,
        }
        self.assertEqual(resolver_viajante_operativo(ctx), 21)

    def test_operativo_invalido_fallback_propio(self):
        ctx = {
            "id_vendedor_usr": 10,
            "vendedor_a_cargo": [20],
            "cod_viajante_operativo": 99,
        }
        self.assertEqual(resolver_viajante_operativo(ctx), 10)

    def test_cartera_incluye_propio(self):
        ctx = {"id_vendedor_usr": 5, "vendedor_a_cargo": [7]}
        self.assertEqual(cartera_permitida_legacy(ctx), [5, 7])
        self.assertEqual(cartera_permitida(ctx), [5, 7])


class TestLeerVendedoresACargoConfig(unittest.TestCase):
    @patch("ecom.services.vendedor_operativo.leer_valor_configuracion_ecom")
    def test_fallback_solo_propio(self, mock_leer):
        mock_leer.return_value = ""
        self.assertEqual(leer_vendedores_a_cargo_config("emp1", 16), [16])

    @patch("ecom.services.vendedor_operativo.leer_valor_configuracion_ecom")
    def test_json_config(self, mock_leer):
        mock_leer.return_value = "[10,49,46,54]"
        self.assertEqual(leer_vendedores_a_cargo_config("emp1", 16), [16, 10, 49, 46, 54])


def _request_con_sesion(user: dict, mayoristapp: dict | None = None):
    factory = RequestFactory()
    req = factory.get("/")
    middleware = SessionMiddleware(lambda r: HttpResponse())
    middleware.process_request(req)
    req.session["user"] = user
    if mayoristapp is not None:
        req.session["mayoristapp"] = mayoristapp
    req.session.save()
    return req


class TestSesionOperativo(unittest.TestCase):
    def test_guardar_y_reset_operativo(self):
        req = _request_con_sesion(
            {"id_vendedor_usr": 10, "vendedor_a_cargo": [10, 20]},
            {},
        )
        self.assertTrue(guardar_cod_viajante_operativo(req, 20))
        self.assertEqual(req.session["mayoristapp"]["cod_viajante_operativo"], 20)
        reset_cod_viajante_operativo(req)
        self.assertNotIn("cod_viajante_operativo", req.session.get("mayoristapp") or {})

    def test_rechaza_fuera_cartera(self):
        req = _request_con_sesion(
            {"id_vendedor_usr": 10, "vendedor_a_cargo": [20]},
            {},
        )
        self.assertFalse(guardar_cod_viajante_operativo(req, 99))


class TestCheckoutCodViajante(unittest.TestCase):
    def test_session_cod_viajante_usa_operativo(self):
        req = _request_con_sesion(
            {"id_vendedor_usr": 10, "vendedor_a_cargo": [10, 21]},
            {"cod_viajante_operativo": 21},
        )
        self.assertEqual(_session_cod_viajante(req), 21)

    def test_session_cod_viajante_id_vendedor_usr(self):
        req = _request_con_sesion({"id_vendedor_usr": 7}, {})
        self.assertEqual(_session_cod_viajante(req), 7)
