"""Tests armado unificado 1ra/2da — redirects, reglas modo."""
import json
from unittest.mock import MagicMock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase

from mpr.services import validar_reglas_lote_armado
from mpr.views import (
    ArmadoOptView,
    ArmadoSurtidoRedirectView,
    ArmadoSurtidoView,
)


class ValidarReglasModoTest(SimpleTestCase):
    @patch("mpr.services.validar_composicion_bom_1ra", return_value=(True, None))
    @patch("mpr.services.articulo_habilitado_armado_1ra", return_value=True)
    @patch("mpr.services.get_deposito_semi_elaborado_mpr", return_value=3)
    def test_1ra_rechaza_deposito_origen_incorrecto(self, *_mocks):
        armados = [
            {"id_articulo_pack": 100, "cantidad_packs": 1, "lineas": [{"id_articulo": 813, "cantidad_por_pack": 1}]},
        ]
        ok, err = validar_reglas_lote_armado(
            armados,
            modo="1ra",
            deposito_origen=99,
            deposito_destino=5,
            id_operario=10,
            require_non_empty=True,
            base_empresa="emp",
        )
        self.assertFalse(ok)
        self.assertIn("Semi", err or "")


class ArmadoRedirectTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_armado_surtido_redirect_a_2da(self):
        request = self.factory.get("/mpr/armado-surtido/")
        request.session = {"user": {"id_usuario": 1}}
        request.user = MagicMock(is_authenticated=True)
        response = ArmadoSurtidoRedirectView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("modo=2da", response.url)

    def test_armado_opt_redirect_a_1ra(self):
        request = self.factory.get("/mpr/opt/5/armado/")
        request.session = {"user": {"id_usuario": 1}}
        request.user = MagicMock(is_authenticated=True)
        request._messages = FallbackStorage(request)
        response = ArmadoOptView.as_view()(request, id_lista=5)
        self.assertEqual(response.status_code, 302)
        self.assertIn("modo=1ra", response.url)

    def test_armado_sin_modo_redirect_a_1ra(self):
        request = self.factory.get("/mpr/armado/")
        request.session = {"user": {"id_usuario": 1, "base_empresa": "emp"}}
        request.user = MagicMock(is_authenticated=True)
        response = ArmadoSurtidoView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("modo=1ra", response.url)


class ArmadoSurtidoViewModoTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ArmadoSurtidoView()

    @patch("mpr.views.ejecutar_lote_armado")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.validar_reglas_lote_armado", return_value=(True, None))
    def test_post_modo_1ra_sin_gate_opt(self, *_mocks):
        ejecutar_lote = _mocks[2]
        ejecutar_lote.return_value = {
            "exitosos": [{
                "id_articulo_pack": 100,
                "cantidad_packs": 1,
                "codigo_movimiento": 17,
                "nro_comprobante": "0001-00000017",
            }],
            "fallidos": [],
        }
        request = self.factory.post(
            "/mpr/armado/?modo=1ra",
            {
                "modo": "1ra",
                "lote_json": json.dumps({
                    "armados": [{
                        "id_articulo_pack": 100,
                        "cantidad_packs": 1,
                        "lineas": [{"id_articulo": 813, "cantidad_por_pack": 1}],
                    }],
                }),
                "deposito_origen": "3",
                "deposito_destino": "5",
                "id_operario": "10",
            },
        )
        request.session = {"user": {"id_usuario": 5}}
        request._messages = FallbackStorage(request)
        response = self.view.post(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("modo=1ra", response.url)
        ejecutar_lote.assert_called_once()
