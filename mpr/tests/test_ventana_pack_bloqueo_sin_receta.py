"""Tests de bloqueo de packs sin receta en el flujo OPT (ventana-pack).

Escenarios cubiertos:
- Todos los packs con receta → redirige a ventana_pack_agrupar (flujo normal)
- Un pack sin receta → bloquea y redirige a ventana_pack con sesión temporal
- Selección mixta (packs con y sin receta) → bloquea, lista solo los sin receta
- receta_json=None → tratado como sin receta
- receta_json JSON inválido → tratado como sin receta
- POST directo (bypass) con pack sin receta → bloqueado por servidor
- GET ventana_pack limpia la sesión temporal y expone contexto para el modal
- Modal se renderiza cuando hay packs sin receta en sesión
"""
import json
from unittest.mock import MagicMock, patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from mpr.views import VentanaPackAgruparView, VentanaPackView, _tiene_receta


# ---------------------------------------------------------------------------
# Tests unitarios del helper _tiene_receta
# ---------------------------------------------------------------------------

class TieneRecetaHelperTest(SimpleTestCase):
    """Verifica el criterio de detección de receta en el helper privado."""

    def test_lista_con_componente_es_verdadero(self):
        fila = {"receta_json": '[{"articulo": "X", "cantidad": 1}]'}
        self.assertTrue(_tiene_receta(fila))

    def test_lista_vacia_es_falso(self):
        fila = {"receta_json": "[]"}
        self.assertFalse(_tiene_receta(fila))

    def test_none_es_falso(self):
        fila = {"receta_json": None}
        self.assertFalse(_tiene_receta(fila))

    def test_ausente_es_falso(self):
        fila = {}
        self.assertFalse(_tiene_receta(fila))

    def test_string_vacio_es_falso(self):
        fila = {"receta_json": ""}
        self.assertFalse(_tiene_receta(fila))

    def test_json_invalido_es_falso(self):
        fila = {"receta_json": "INVALID_JSON"}
        self.assertFalse(_tiene_receta(fila))

    def test_multiples_componentes_es_verdadero(self):
        fila = {"receta_json": '[{"articulo": "A", "cantidad": 2}, {"articulo": "B", "cantidad": 3}]'}
        self.assertTrue(_tiene_receta(fila))


# ---------------------------------------------------------------------------
# Helpers para los tests de vista
# ---------------------------------------------------------------------------

def _fila_con_receta(id_articulo, receta_json='[{"articulo": "X", "cantidad": 1}]'):
    """Genera una fila de listar_ventana_pack con receta definida."""
    return {
        "id_articulo": id_articulo,
        "codigo_articulo": f"COD-{id_articulo}",
        "codigo_manual": f"PKG-{id_articulo:03d}",
        "descripcion_articulo": f"Pack artículo {id_articulo}",
        "receta_json": receta_json,
        "stock_terminado": 0,
        "cantidad_pedida_pedido": 10,
        "cantidad_urgente": 5,
        "cantidad_a_fabricar": 10,
        "cantidad_promedio_bulto": 12,
        "cantidad_demanda_reserva": 0,
        "cantidad_parcial_fabricada": 0,
        "cantidad_urgente_abs": 5,
        "stock_reserva": 0,
        "origen_demanda_etiqueta": "Pedido",
        "pedidos_resumen": [],
        "detalle_stock_depositos_json": "{}",
        "pedidos_resumen_json": "[]",
    }


def _fila_sin_receta(id_articulo, receta_json="[]"):
    """Genera una fila de listar_ventana_pack sin receta (o receta inválida)."""
    return _fila_con_receta(id_articulo, receta_json=receta_json)


def _make_post_request(factory, filas_ids, cantidades=None):
    """Construye un POST a ventana_pack_agrupar con los IDs y cantidades dados."""
    if cantidades is None:
        cantidades = {id_art: 10 for id_art in filas_ids}
    data = {"sel": [str(i) for i in filas_ids]}
    for id_art, qty in cantidades.items():
        data[f"cant_{id_art}"] = str(qty)
    request = factory.post("/mpr/demanda/ventana-pack/agrupar/", data)
    request.session = {"user": {"base_empresa": "empresa_test", "id_usuario": 1}}
    request._messages = FallbackStorage(request)
    request.user = MagicMock(is_authenticated=True)
    return request


# ---------------------------------------------------------------------------
# Tests de VentanaPackAgruparView.post — validación de receta
# ---------------------------------------------------------------------------

class VentanaPackAgruparPostRecetaTest(SimpleTestCase):
    """Verifica el bloqueo de packs sin receta en el POST de VentanaPackAgruparView."""

    def setUp(self):
        self.factory = RequestFactory()
        self.view = VentanaPackAgruparView()

    @patch("mpr.views.listar_ventana_pack")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_todos_con_receta_continua(self, _mock_empresa, mock_listar):
        """Cuando todos los packs tienen receta, el flujo avanza a ventana_pack_agrupar."""
        filas = [
            _fila_con_receta(101),
            _fila_con_receta(102),
            _fila_con_receta(103),
        ]
        mock_listar.return_value = filas

        request = _make_post_request(self.factory, [101, 102, 103])
        response = self.view.post(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("agrupar", response.url)
        self.assertIn("ventana_pack_seleccion", request.session)
        self.assertNotIn("ventana_pack_sin_receta", request.session)
        seleccion = request.session["ventana_pack_seleccion"]
        self.assertEqual(len(seleccion["filas"]), 3)

    @patch("mpr.views.listar_ventana_pack")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_uno_sin_receta_bloquea(self, _mock_empresa, mock_listar):
        """Cuando un pack no tiene receta, se bloquea y redirige a ventana_pack."""
        mock_listar.return_value = [_fila_sin_receta(201, receta_json="[]")]

        request = _make_post_request(self.factory, [201])
        response = self.view.post(request)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("agrupar", response.url)
        self.assertNotIn("ventana_pack_seleccion", request.session)
        self.assertIn("ventana_pack_sin_receta", request.session)
        sin_receta = request.session["ventana_pack_sin_receta"]
        self.assertEqual(len(sin_receta), 1)
        self.assertEqual(sin_receta[0]["id_articulo"], 201)

    @patch("mpr.views.listar_ventana_pack")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_mixto_bloquea_y_lista_solo_sin_receta(self, _mock_empresa, mock_listar):
        """Selección mixta: bloquea y lista únicamente los packs sin receta."""
        filas = [
            _fila_con_receta(301),
            _fila_con_receta(302),
            _fila_con_receta(303),
            _fila_sin_receta(304, receta_json="[]"),
        ]
        mock_listar.return_value = filas

        request = _make_post_request(self.factory, [301, 302, 303, 304])
        response = self.view.post(request)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("agrupar", response.url)
        self.assertNotIn("ventana_pack_seleccion", request.session)
        sin_receta = request.session["ventana_pack_sin_receta"]
        self.assertEqual(len(sin_receta), 1)
        self.assertEqual(sin_receta[0]["id_articulo"], 304)
        ids_bloqueados = [p["id_articulo"] for p in sin_receta]
        self.assertNotIn(301, ids_bloqueados)
        self.assertNotIn(302, ids_bloqueados)
        self.assertNotIn(303, ids_bloqueados)

    @patch("mpr.views.listar_ventana_pack")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_receta_json_none_se_trata_como_sin_receta(self, _mock_empresa, mock_listar):
        """receta_json=None debe tratarse como sin receta y bloquear."""
        mock_listar.return_value = [_fila_sin_receta(401, receta_json=None)]

        request = _make_post_request(self.factory, [401])
        response = self.view.post(request)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("ventana_pack_seleccion", request.session)
        sin_receta = request.session.get("ventana_pack_sin_receta", [])
        self.assertEqual(len(sin_receta), 1)
        self.assertEqual(sin_receta[0]["id_articulo"], 401)

    @patch("mpr.views.listar_ventana_pack")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_receta_json_invalido_se_trata_como_sin_receta(self, _mock_empresa, mock_listar):
        """receta_json con JSON malformado debe tratarse como sin receta."""
        mock_listar.return_value = [_fila_sin_receta(501, receta_json="INVALID_JSON")]

        request = _make_post_request(self.factory, [501])
        response = self.view.post(request)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("ventana_pack_seleccion", request.session)
        sin_receta = request.session.get("ventana_pack_sin_receta", [])
        self.assertEqual(len(sin_receta), 1)
        self.assertEqual(sin_receta[0]["id_articulo"], 501)

    @patch("mpr.views.listar_ventana_pack")
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_post_directo_sin_receta_bloqueado(self, _mock_empresa, mock_listar):
        """POST directo a ventana_pack_agrupar con pack sin receta no puede bypassear la validación."""
        mock_listar.return_value = [_fila_sin_receta(601, receta_json="[]")]

        request = _make_post_request(self.factory, [601])
        response = self.view.post(request)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("ventana_pack_seleccion", request.session)
        sin_receta = request.session.get("ventana_pack_sin_receta", [])
        self.assertGreater(len(sin_receta), 0)
        self.assertEqual(sin_receta[0]["id_articulo"], 601)


# ---------------------------------------------------------------------------
# Tests de VentanaPackView.get_context_data — sesión temporal y modal
# ---------------------------------------------------------------------------

class VentanaPackGetContextTest(SimpleTestCase):
    """Verifica que get_context_data lea y limpie la sesión temporal de packs sin receta."""

    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.views.listar_ventana_pack_unidades", return_value=[])
    @patch("mpr.views.listar_ventana_pack", return_value=[])
    @patch("mpr.views.actualizar_pedidos_produccion", return_value=(True, "ok"))
    @patch("mpr.views.get_deposito_semi_elaborado_mpr", return_value=None)
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_get_limpia_sesion_sin_receta(self, *_mocks):
        """GET a ventana_pack expone packs_sin_receta en contexto y limpia la sesión."""
        pack_bloqueado = {"id_articulo": 123, "codigo_manual": "PKG-001", "descripcion_articulo": "Pack Test"}

        view = VentanaPackView()
        request = self.factory.get("/mpr/demanda/ventana-pack/")
        request.session = {
            "user": {"base_empresa": "empresa_test"},
            "ventana_pack_sin_receta": [pack_bloqueado],
        }
        request.user = MagicMock(is_authenticated=True)
        view.request = request
        view.kwargs = {}
        view.args = ()

        context = view.get_context_data()

        self.assertIn("packs_sin_receta", context)
        self.assertEqual(len(context["packs_sin_receta"]), 1)
        self.assertEqual(context["packs_sin_receta"][0]["id_articulo"], 123)
        self.assertNotIn("ventana_pack_sin_receta", request.session)

    @patch("mpr.views.listar_ventana_pack_unidades", return_value=[])
    @patch("mpr.views.listar_ventana_pack", return_value=[])
    @patch("mpr.views.actualizar_pedidos_produccion", return_value=(True, "ok"))
    @patch("mpr.views.get_deposito_semi_elaborado_mpr", return_value=None)
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_get_sin_sesion_temporal_devuelve_lista_vacia(self, *_mocks):
        """GET a ventana_pack sin sesión temporal devuelve packs_sin_receta vacío."""
        view = VentanaPackView()
        request = self.factory.get("/mpr/demanda/ventana-pack/")
        request.session = {"user": {"base_empresa": "empresa_test"}}
        request.user = MagicMock(is_authenticated=True)
        view.request = request
        view.kwargs = {}
        view.args = ()

        context = view.get_context_data()

        self.assertIn("packs_sin_receta", context)
        self.assertEqual(context["packs_sin_receta"], [])

    @patch("mpr.views.listar_ventana_pack_unidades", return_value=[])
    @patch("mpr.views.listar_ventana_pack", return_value=[])
    @patch("mpr.views.actualizar_pedidos_produccion", return_value=(True, "ok"))
    @patch("mpr.views.get_deposito_semi_elaborado_mpr", return_value=None)
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_modal_renderizado_cuando_hay_sin_receta(self, *_mocks):
        """El contexto packs_sin_receta permite renderizar el modal con datos del artículo."""
        pack_bloqueado = {
            "id_articulo": 999,
            "codigo_manual": "PKG-TEST",
            "descripcion_articulo": "Pack de prueba",
        }

        view = VentanaPackView()
        request = self.factory.get("/mpr/demanda/ventana-pack/")
        request.session = {
            "user": {"base_empresa": "empresa_test"},
            "ventana_pack_sin_receta": [pack_bloqueado],
        }
        request.user = MagicMock(is_authenticated=True)
        view.request = request
        view.kwargs = {}
        view.args = ()

        context = view.get_context_data()

        packs = context["packs_sin_receta"]
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0]["id_articulo"], 999)
        self.assertEqual(packs[0]["codigo_manual"], "PKG-TEST")
        self.assertEqual(packs[0]["descripcion_articulo"], "Pack de prueba")
