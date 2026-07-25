"""Tests — indicadores de máquina en columna Fabricando (tablero Par).

Comando:
    docker exec Synap_app python manage.py test mpr.tests.test_tablero_fabricando_maquina --keepdb
"""
from datetime import date
from html.parser import HTMLParser
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, TestCase

from mpr.services_maquina_linea import enriquecer_filas_tablero_indicadores_fabricando
from mpr.views import TableroProduccionView


class TestEnriquecerFilasTableroIndicadoresFabricando(SimpleTestCase):
    """Enriquecimiento batch de filas Par con máquinas vigentes."""

    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services_maquina_linea.cantidades_parte_planilla_por_fecha")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    def test_articulo_con_maquina_no_marca_sin_maquina(
        self, mock_maquinas, mock_articulos, mock_cantidades, mock_roster
    ):
        mock_maquinas.return_value = [
            {
                "id": 1,
                "codigo": "M1",
                "nombre": "Máquina 1",
                "id_linea_actual": 10,
                "linea_actual_nombre": "Línea A",
            }
        ]
        mock_articulos.return_value = {1: [{"id_articulo": 100}]}
        mock_cantidades.return_value = {}
        mock_roster.return_value = {10: {"manana": [], "tarde": [], "noche": []}}

        filas = [
            {
                "id_articulo": 100,
                "enviado": 24.0,
                "descripcion_articulo": "Componente",
                "codigo_manual": "C-100",
            }
        ]
        out = enriquecer_filas_tablero_indicadores_fabricando("emp", filas, fecha=date(2026, 7, 25))

        self.assertTrue(out[0]["tiene_maquina"])
        self.assertFalse(out[0]["fabricando_sin_maquina"])
        self.assertEqual(len(out[0]["maquinas_asignadas"]), 1)
        self.assertEqual(out[0]["maquinas_asignadas"][0]["codigo"], "M1")
        self.assertIn("fabricando_detalle", out[0])
        self.assertEqual(out[0]["fabricando_detalle"]["fabricando_pares"], 24.0)

    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services_maquina_linea.cantidades_parte_planilla_por_fecha")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    def test_articulo_sin_maquina_y_enviado_positivo(
        self, mock_maquinas, mock_articulos, mock_cantidades, mock_roster
    ):
        mock_maquinas.return_value = []
        mock_articulos.return_value = {}
        mock_cantidades.return_value = {}
        mock_roster.return_value = {}

        filas = [{"id_articulo": 200, "enviado": 12.0, "descripcion_articulo": "Sin máq"}]
        out = enriquecer_filas_tablero_indicadores_fabricando("emp", filas)

        self.assertFalse(out[0]["tiene_maquina"])
        self.assertTrue(out[0]["fabricando_sin_maquina"])
        self.assertEqual(out[0]["maquinas_asignadas"], [])

    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services_maquina_linea.cantidades_parte_planilla_por_fecha")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    def test_fila_sin_id_articulo_idempotente(
        self, mock_maquinas, mock_articulos, mock_cantidades, mock_roster
    ):
        mock_maquinas.return_value = []
        mock_articulos.return_value = {}
        mock_cantidades.return_value = {}
        mock_roster.return_value = {}
        filas = [{"enviado": 5.0, "descripcion_articulo": "Pack"}]
        out = enriquecer_filas_tablero_indicadores_fabricando("emp", filas)
        self.assertNotIn("tiene_maquina", out[0])
        self.assertEqual(out[0]["enviado"], 5.0)

    @patch("mpr.services_maquina_linea._operarios_roster_celda_por_linea")
    @patch("mpr.services_maquina_linea.cantidades_parte_planilla_por_fecha")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    def test_parte_hoy_por_maquina_y_fecha(
        self, mock_maquinas, mock_articulos, mock_cantidades, mock_roster
    ):
        mock_maquinas.return_value = [
            {
                "id": 5,
                "codigo": "2",
                "nombre": "Telar",
                "id_linea_actual": 3,
                "linea_actual_nombre": "L3",
            }
        ]
        mock_articulos.return_value = {5: [{"id_articulo": 50}]}
        mock_cantidades.return_value = {(5, 50): {"manana": 12.0, "tarde": 0.0, "noche": 0.0}}
        mock_roster.return_value = {
            3: {"manana": [{"id_operario": 1, "nombre": "JUAN"}], "tarde": [], "noche": []}
        }
        fecha = date(2026, 7, 21)
        filas = [{"id_articulo": 50, "enviado": 12.0, "codigo_manual": "X", "descripcion_articulo": "Art"}]
        out = enriquecer_filas_tablero_indicadores_fabricando("emp", filas, fecha=fecha)

        det = out[0]["fabricando_detalle"]
        self.assertEqual(det["fecha_ddmmyyyy"], "21/07/2026")
        self.assertEqual(det["parte_hoy"][0]["manana"], 12)
        self.assertIn("L3", det["roster_por_linea"])
        self.assertEqual(det["roster_por_linea"]["L3"]["manana"], ["JUAN"])


class TestTableroProduccionViewIndicadoresFabricando(TestCase):
    """La vista enriquece filas Par con indicadores de máquina."""

    def setUp(self):
        self.factory = RequestFactory()

    def _get(self, query=None):
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/mpr/tablero-produccion/", query or {})
        request.session = self.client.session
        request.user = AnonymousUser()
        view = TableroProduccionView()
        view.request = request
        return view, request

    @patch("mpr.services_maquina_linea.enriquecer_filas_tablero_indicadores_fabricando")
    @patch("mpr.presentacion_operativa.enriquecer_filas_tablero_presentacion")
    @patch("mpr.views._context_filtro_marcas", return_value={})
    @patch("mpr.views._usuario_puede_anular_envios", return_value=False)
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.listar_tablero_por_articulo", return_value=[{"id_articulo": 1}])
    def test_modo_par_llama_enriquecedor(
        self,
        mock_listar,
        mock_base,
        mock_anular,
        mock_marcas,
        mock_presentacion,
        mock_indicadores,
    ):
        mock_presentacion.return_value = [{"id_articulo": 1}]
        mock_indicadores.return_value = [{"id_articulo": 1, "tiene_maquina": True}]

        view, request = self._get({"modo": "par", "fecha_hasta": "2026-07-25"})
        response = view.get(request)

        mock_indicadores.assert_called_once()
        self.assertEqual(response.context_data["fecha_tablero_ddmmyyyy"], "25/07/2026")

    @patch("mpr.services_maquina_linea.enriquecer_filas_tablero_indicadores_fabricando")
    @patch("mpr.presentacion_operativa.enriquecer_filas_tablero_presentacion")
    @patch("mpr.views._context_filtro_marcas", return_value={})
    @patch("mpr.views._usuario_puede_anular_envios", return_value=False)
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.views.listar_tablero_por_articulo", return_value=[{"id_articulo": 1}])
    def test_x_data_del_tablero_conserva_las_acciones_de_fabricando(
        self,
        mock_listar,
        mock_base,
        mock_anular,
        mock_marcas,
        mock_presentacion,
        mock_indicadores,
    ):
        class XDataParser(HTMLParser):
            x_data = None

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "div" and "x-data" in attrs_dict:
                    self.x_data = attrs_dict["x-data"]

        mock_presentacion.return_value = [{"id_articulo": 1}]
        mock_indicadores.return_value = [{"id_articulo": 1, "tiene_maquina": True}]
        view, request = self._get({"modo": "par"})
        request.user.email = ""

        response = view.get(request)
        parser = XDataParser()
        parser.feed(response.render().content.decode())

        self.assertIsNotNone(parser.x_data)
        self.assertIn("JSON.parse(raw)", parser.x_data)
        self.assertIn("cerrarFabDetalle", parser.x_data)

    @patch("mpr.services_maquina_linea.enriquecer_filas_tablero_indicadores_fabricando")
    @patch("mpr.presentacion_operativa.enriquecer_filas_tablero_presentacion")
    @patch("mpr.views._context_filtro_marcas", return_value={})
    @patch("mpr.views._usuario_puede_anular_envios", return_value=False)
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.services.listar_tablero_pack", return_value=[{"id_articulo": 1}])
    def test_modo_pack_no_llama_enriquecedor(
        self,
        mock_listar_pack,
        mock_base,
        mock_anular,
        mock_marcas,
        mock_presentacion,
        mock_indicadores,
    ):
        mock_presentacion.return_value = [{"id_articulo": 1}]

        view, request = self._get({"modo": "pack"})
        view.get(request)

        mock_indicadores.assert_not_called()
