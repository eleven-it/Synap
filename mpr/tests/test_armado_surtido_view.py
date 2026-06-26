"""Tests vista Armado surtido — POST lote, sesión y API (Fases 4 y 7)."""
import json
from unittest.mock import patch

from django.contrib.messages import get_messages
from django.test import RequestFactory, SimpleTestCase

from mpr.views import (
    ArmadoSurtidoView,
    ArmadoSurtidoValidarItemLoteAPIView,
    _fallidos_para_carrito_armado_surtido,
    _resolver_post_armado_surtido,
)


class FallidosCarritoTest(SimpleTestCase):
    def test_conserva_lineas_para_rehidratar(self):
        fallidos = [{
            "id_articulo_pack": 100,
            "cantidad_packs": 2,
            "lineas": [{"id_articulo": 813, "cantidad_por_pack": 3}],
            "error": "Stock insuficiente",
        }]
        carrito = _fallidos_para_carrito_armado_surtido(fallidos)
        self.assertEqual(len(carrito), 1)
        self.assertEqual(carrito[0]["id_articulo_pack"], 100)
        self.assertEqual(carrito[0]["lineas"][0]["id_articulo"], 813)


class ResolverPostArmadoSurtidoTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_legacy_single_pack(self):
        request = self.factory.post(
            "/mpr/armado-surtido/",
            {
                "id_articulo_pack": "1342",
                "cantidad_packs": "2",
                "deposito_origen": "3",
                "deposito_destino": "5",
                "id_operario": "10",
                "comp_id_articulo": ["813"],
                "comp_cantidad_por_pack": ["3"],
            },
        )
        cabecera, armados, err = _resolver_post_armado_surtido(request)
        self.assertIsNone(err)
        self.assertEqual(cabecera["deposito_origen"], 3)
        self.assertEqual(len(armados), 1)
        self.assertEqual(armados[0]["id_articulo_pack"], 1342)
        self.assertEqual(armados[0]["cantidad_packs"], 2)


class ArmadoSurtidoViewPostTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ArmadoSurtidoView()

    @patch("mpr.views.ejecutar_lote_armado_surtido")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.opt_puede_armado_surtido", return_value=(True, ""))
    @patch("mpr.views.validar_reglas_lote_armado_surtido", return_value=(True, None))
    def test_post_guarda_sesion_y_mensaje_exito(self, *_mocks):
        ejecutar_lote = _mocks[3]
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
            "/mpr/armado-surtido/",
            {
                "id_articulo_pack": "100",
                "cantidad_packs": "1",
                "deposito_origen": "3",
                "deposito_destino": "5",
                "id_operario": "10",
                "comp_id_articulo": ["813"],
                "comp_cantidad_por_pack": ["1"],
            },
        )
        request.session = {"user": {"id_usuario": 5}}
        request._messages = []
        from django.contrib.messages.storage.fallback import FallbackStorage
        request._messages = FallbackStorage(request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("armado_surtido_resultado_lote", request.session)
        self.assertEqual(request.session.get("armado_surtido_lote_fallidos"), [])
        msgs = [m.message for m in get_messages(request)]
        self.assertTrue(any("Comprobante" in m for m in msgs))

    @patch("mpr.views.ejecutar_lote_armado_surtido")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.opt_puede_armado_surtido", return_value=(True, ""))
    @patch("mpr.views.validar_reglas_lote_armado_surtido", return_value=(True, None))
    def test_post_parcial_mensaje_warning(self, *_mocks):
        ejecutar_lote = _mocks[3]
        ejecutar_lote.return_value = {
            "exitosos": [{"id_articulo_pack": 100, "cantidad_packs": 1, "codigo_movimiento": 1, "nro_comprobante": "A"}],
            "fallidos": [{
                "id_articulo_pack": 200,
                "cantidad_packs": 1,
                "lineas": [{"id_articulo": 813, "cantidad_por_pack": 1}],
                "error": "Stock insuficiente",
            }],
        }
        request = self.factory.post(
            "/mpr/armado-surtido/",
            {
                "lote_json": '{"armados":[{"id_articulo_pack":100,"cantidad_packs":1,"lineas":[{"id_articulo":813,"cantidad_por_pack":1}]}]}',
                "deposito_origen": "3",
                "deposito_destino": "5",
                "id_operario": "10",
            },
        )
        request.session = {"user": {"id_usuario": 5}}
        from django.contrib.messages.storage.fallback import FallbackStorage
        request._messages = FallbackStorage(request)

        response = self.view.post(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(request.session.get("armado_surtido_lote_fallidos") or []), 1)
        msgs = [m.message for m in get_messages(request)]
        self.assertTrue(any("no se pudieron grabar" in m.lower() for m in msgs))


class ArmadoSurtidoValidarItemLoteAPITest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ArmadoSurtidoValidarItemLoteAPIView()

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_rechaza_sin_item_json(self, *_mocks):
        request = self.factory.get("/mpr/api/armado-surtido/validar-item-lote/", {"deposito": "3"})
        response = self.view.get(request)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
        self.assertIn("candidato", (data.get("error") or "").lower())

    @patch("mpr.views.validar_stock_agregado_lote", return_value=(True, []))
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_acepta_item_valido(self, *_mocks):
        item = {
            "id_articulo_pack": 100,
            "cantidad_packs": 1,
            "lineas": [{"id_articulo": 813, "cantidad_por_pack": 2}],
        }
        request = self.factory.get(
            "/mpr/api/armado-surtido/validar-item-lote/",
            {
                "deposito": "3",
                "lote_json": json.dumps({"armados": []}),
                "item_json": json.dumps(item),
            },
        )
        response = self.view.get(request)
        data = json.loads(response.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["conflictos"], [])

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.validar_stock_agregado_lote")
    def test_devuelve_conflictos_stock(self, mock_stock, _mock_base):
        mock_stock.return_value = (
            False,
            [{
                "id_articulo": 813,
                "codigo_articulo": "1.1.813",
                "necesario": 8.0,
                "disponible": 5.0,
                "mensaje": "Stock insuficiente para agregar al lote.",
            }],
        )
        item = {
            "id_articulo_pack": 100,
            "cantidad_packs": 2,
            "lineas": [{"id_articulo": 813, "cantidad_por_pack": 4}],
        }
        request = self.factory.get(
            "/mpr/api/armado-surtido/validar-item-lote/",
            {"deposito": "3", "item_json": json.dumps(item)},
        )
        response = self.view.get(request)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
        self.assertEqual(len(data["conflictos"]), 1)
        self.assertEqual(data["conflictos"][0]["id_articulo"], 813)

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_rechaza_pack_duplicado_en_lote(self, *_mocks):
        lote = {
            "armados": [{
                "id_articulo_pack": 100,
                "cantidad_packs": 1,
                "lineas": [{"id_articulo": 813, "cantidad_por_pack": 1}],
            }],
        }
        item = {
            "id_articulo_pack": 100,
            "cantidad_packs": 2,
            "lineas": [{"id_articulo": 813, "cantidad_por_pack": 1}],
        }
        request = self.factory.get(
            "/mpr/api/armado-surtido/validar-item-lote/",
            {
                "deposito": "3",
                "lote_json": json.dumps(lote),
                "item_json": json.dumps(item),
            },
        )
        response = self.view.get(request)
        data = json.loads(response.content)
        self.assertFalse(data["ok"])
        self.assertIn("fila existente", (data.get("error") or "").lower())
