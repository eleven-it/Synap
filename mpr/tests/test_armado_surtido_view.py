"""Tests vista Armado surtido — POST lote, sesión y API (Fases 4 y 7)."""
import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from mpr.views import (
    ArmadoSurtidoView,
    ArmadoSurtidoValidarItemLoteAPIView,
    _fallidos_para_carrito_armado_surtido,
    _resolver_post_armado_surtido,
)
from mpr.services import construir_armados_desde_post_tablero


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

    @patch(
        "mpr.services.lineas_bom_pack_1ra",
        return_value=[{"id_articulo": 813, "cantidad_por_pack": 12}],
    )
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.services.articulo_habilitado_armado_1ra", return_value=True)
    def test_tablero_post_armar_columna(self, *_mocks):
        request = self.factory.post(
            "/mpr/armado/",
            {
                "vista": "tablero",
                "modo": "1ra",
                "deposito_origen": "3",
                "deposito_destino": "5",
                "armar_1342": "4",
            },
        )
        cabecera, armados, err = _resolver_post_armado_surtido(request)
        self.assertIsNone(err)
        self.assertEqual(len(armados), 1)
        self.assertEqual(armados[0]["id_articulo_pack"], 1342)
        self.assertEqual(armados[0]["cantidad_packs"], 4)
        self.assertEqual(armados[0]["lineas"][0]["cantidad_por_pack"], 12)


class ConstruirArmadosTableroTest(SimpleTestCase):
    @patch(
        "mpr.services.lineas_bom_pack_1ra",
        return_value=[{"id_articulo": 10, "cantidad_por_pack": 6}],
    )
    def test_solo_filas_con_cantidad_positiva(self, _bom):
        post = {"armar_100": "2", "armar_200": "0", "armar_": "1"}
        items = construir_armados_desde_post_tablero("emp", post, modo="1ra")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id_articulo_pack"], 100)

    @patch(
        "mpr.services.lineas_bom_pack_1ra",
        return_value=[{"id_articulo": 10, "cantidad_por_pack": 6}],
    )
    def test_ignora_cantidades_negativas_y_vacias(self, _bom):
        post = {"armar_100": "-3", "armar_200": "", "armar_300": "1"}
        items = construir_armados_desde_post_tablero("emp", post, modo="1ra")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id_articulo_pack"], 300)
        self.assertEqual(items[0]["cantidad_packs"], 1)


class ArmadoSurtidoViewPostTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ArmadoSurtidoView()

    @patch("mpr.views.ejecutar_lote_armado")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.validar_reglas_lote_armado", return_value=(True, None))
    def test_post_guarda_sesion_y_resultado_modal(self, *_mocks):
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
            "/mpr/armado/?modo=2da",
            {
                "modo": "2da",
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
        self.assertIn("modo=2da", response.url)
        self.assertIn("armado_surtido_resultado_lote", request.session)
        self.assertEqual(request.session.get("armado_surtido_lote_fallidos"), [])
        resultado = request.session["armado_surtido_resultado_lote"]
        self.assertEqual(len(resultado.get("exitosos") or []), 1)
        self.assertEqual(resultado.get("exitosos")[0].get("nro_comprobante"), "0001-00000017")

    @patch("mpr.views.ejecutar_lote_armado")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.validar_reglas_lote_armado", return_value=(True, None))
    def test_post_parcial_guarda_resultado_modal(self, *_mocks):
        ejecutar_lote = _mocks[2]
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
            "/mpr/armado/?modo=2da",
            {
                "modo": "2da",
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
        resultado = request.session.get("armado_surtido_resultado_lote") or {}
        self.assertEqual(len(resultado.get("exitosos") or []), 1)
        self.assertEqual(len(resultado.get("fallidos") or []), 1)


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


class ArmadoTableroFechaContextTest(SimpleTestCase):
    """La fecha del chrome se lee de GET y alimenta filtros + historial del día."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view = ArmadoSurtidoView()

    @patch("mpr.views.listar_armados_realizados_por_fecha", return_value=[
        {
            "id_articulo_pack": 100,
            "descripcion_articulo": "Pack demo",
            "cantidad_packs": 3,
            "nro_comprobante": "A-1",
        },
    ])
    @patch("mpr.views.listar_tablero_armado", return_value=[])
    @patch("mpr.views.get_depositos_con_suma_stock", return_value=[])
    @patch("mpr.views.get_deposito_terminado_mpr", return_value=5)
    @patch("mpr.views.get_deposito_semi_elaborado_mpr", return_value=3)
    @patch("mpr.views._usuario_puede_imputar_pedido", return_value=False)
    @patch("mpr.views._context_filtro_marcas", return_value={"marcas_catalogo": [], "marcas_incluidos": []})
    @patch("mpr.views._get_id_puesto", return_value=None)
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_preserva_fecha_realizado_en_filtros_y_historial(self, *_mocks):
        request = self.factory.get(
            "/mpr/armado/",
            {
                "vista": "tablero",
                "modo": "1ra",
                "fecha_realizado": "31/07/2026",
                "presentacion": "unidades",
            },
        )
        request.session = {}
        self.view.request = request
        context = self.view._context_armado_tablero({
            "base_empresa": "empresa_test",
            "modo": "1ra",
        })
        self.assertEqual(context["fecha_realizado_default"], "31/07/2026")
        self.assertIn("fecha_realizado=31%2F07%2F2026", context["filtros_qs"])
        self.assertEqual(len(context["armados_del_dia"]), 1)
        self.assertEqual(context["armados_del_dia_total_packs"], 3)
