"""Tests backend carga en grilla de artículos por máquina (MPR)."""
import inspect
import json
from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from mpr.repositories import maquina_articulo as repo_art
from mpr.services_maquina_linea import (
    buscar_articulos,
    construir_grilla_carga_articulos,
    guardar_observacion_planilla_maquina,
)
from mpr.views import (
    MaquinaArticuloAccionAPIView,
    MaquinaArticuloBuscarAPIView,
    MaquinaObservacionPlanillaAPIView,
)


class BuscarArticulosServiceTest(SimpleTestCase):
    @patch("mpr.services_maquina_linea.repo_art.buscar_articulos")
    def test_pasa_tipo_art_fab_al_repo(self, mock_repo):
        mock_repo.return_value = []
        buscar_articulos("emp", "abc", limit=10, tipo_art_fab="Fabricado")
        mock_repo.assert_called_once_with(
            "emp", "abc", limit=10, tipo_art_fab="Fabricado"
        )


class ConstruirGrillaCargaArticulosTest(SimpleTestCase):
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    @patch("mpr.services_maquina_linea.listar_lineas")
    def test_filtra_por_linea_y_cuenta_con_articulos(
        self, mock_lineas, mock_maquinas, mock_articulos
    ):
        mock_lineas.return_value = [{"id": 1, "nombre": "L1", "activo": True}]
        mock_maquinas.return_value = [
            {
                "id": 10,
                "codigo": "1",
                "nombre": "M1",
                "activo": True,
                "id_linea_actual": 1,
                "observacion_planilla": "Nota previa",
            },
            {"id": 20, "codigo": "2", "nombre": "M2", "activo": True, "id_linea_actual": 2},
        ]
        mock_articulos.return_value = {
            10: [{"id_articulo": 100, "codigo_articulo": "A", "descripcion_articulo": "Art A"}],
        }
        out = construir_grilla_carga_articulos("emp", id_linea=1)
        self.assertEqual(out["total_maquinas"], 1)
        self.assertEqual(out["con_articulos"], 1)
        self.assertEqual(out["maquinas"][0]["id"], 10)
        self.assertEqual(out["maquinas"][0]["observacion_planilla"], "Nota previa")
        self.assertEqual(len(out["maquinas"][0]["articulos"]), 1)
        self.assertIn("codigo_search", out["maquinas"][0])
        self.assertEqual(out["id_linea_filtro"], 1)
        self.assertEqual(out["fecha_hoy"], date.today())


class ListarArticulosVigentesOrdenTest(SimpleTestCase):
    def test_orden_por_antiguedad_en_sql(self):
        src_vig = inspect.getsource(repo_art.listar_articulos_vigentes)
        src_todas = inspect.getsource(repo_art.listar_articulos_vigentes_todas_maquinas)
        for src in (src_vig, src_todas):
            self.assertIn("ma.vigencia_desde ASC", src)
            self.assertIn("ma.creado_en ASC", src)
            self.assertIn("ma.id_mpr_maquina_articulo ASC", src)


class GuardarObservacionPlanillaMaquinaTest(SimpleTestCase):
    @patch("mpr.services_maquina_linea.repo.actualizar_observacion_planilla")
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 5})
    def test_ok_guarda_texto(self, _obtener, mock_actualizar):
        ok, error, normalizada = guardar_observacion_planilla_maquina(
            "emp", 5, "  Revisar talle  "
        )
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertEqual(normalizada, "Revisar talle")
        mock_actualizar.assert_called_once_with("emp", 5, "Revisar talle")

    @patch("mpr.services_maquina_linea.repo.actualizar_observacion_planilla")
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 5})
    def test_vacio_ok(self, _obtener, mock_actualizar):
        ok, error, normalizada = guardar_observacion_planilla_maquina("emp", 5, "   ")
        self.assertTrue(ok)
        self.assertIsNone(error)
        self.assertEqual(normalizada, "")
        mock_actualizar.assert_called_once_with("emp", 5, "")

    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 5})
    def test_rechaza_mas_de_220(self, _obtener):
        ok, error, normalizada = guardar_observacion_planilla_maquina("emp", 5, "x" * 221)
        self.assertFalse(ok)
        self.assertIn("220", error)
        self.assertEqual(normalizada, "")

    def test_rechaza_empresa_invalida(self):
        ok, error, _normalizada = guardar_observacion_planilla_maquina("", 5, "texto")
        self.assertFalse(ok)
        self.assertIn("Empresa", error)

    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value=None)
    def test_rechaza_maquina_inexistente(self, _obtener):
        ok, error, _normalizada = guardar_observacion_planilla_maquina("emp", 99, "texto")
        self.assertFalse(ok)
        self.assertIn("no encontrada", error.lower())


class MaquinaArticuloBuscarAPIViewTest(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = MaquinaArticuloBuscarAPIView()

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch("mpr.services_maquina_linea.buscar_articulos")
    def test_get_pasa_fabricado(self, mock_buscar, _base):
        mock_buscar.return_value = [
            {
                "id_articulo": 1,
                "codigo_manual": "M1",
                "codigo_articulo": "ART1",
                "descripcion_articulo": "Calcetín",
            }
        ]
        req = self.rf.get("/mpr/maquinas/api/articulos/buscar/?q=calc")
        resp = self.view.get(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertEqual(len(data["articulos"]), 1)
        mock_buscar.assert_called_once_with(
            "emp", "calc", limit=25, tipo_art_fab="Fabricado"
        )

    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_get_q_vacio_devuelve_lista_vacia(self, _base):
        req = self.rf.get("/mpr/maquinas/api/articulos/buscar/?q=")
        resp = self.view.get(req)
        data = json.loads(resp.content)
        self.assertEqual(data["articulos"], [])


class MaquinaArticuloAccionAPIViewTest(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = MaquinaArticuloAccionAPIView()

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_maquina")
    @patch("mpr.services_maquina_linea.habilitar_articulo_maquina", return_value=(True, None))
    def test_post_habilitar_ok(self, mock_hab, mock_vigentes, _base):
        mock_vigentes.return_value = [
            {
                "id_articulo": 5,
                "codigo_articulo": "X",
                "descripcion_articulo": "Y",
                "vigencia_desde": date.today(),
            }
        ]
        req = self.rf.post(
            "/mpr/maquinas/api/articulos/accion/",
            data=json.dumps({"accion": "habilitar", "id_maquina": 1, "id_articulo": 5}),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["articulo"]["id_articulo"], 5)
        mock_hab.assert_called_once_with("emp", 1, 5)

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch(
        "mpr.services_maquina_linea.deshabilitar_articulo_maquina",
        return_value=(True, None),
    )
    def test_post_deshabilitar_ok(self, mock_deshab, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/articulos/accion/",
            data={"accion": "deshabilitar", "id_maquina": 2, "id_articulo": 9},
        )
        resp = self.view.post(req)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertNotIn("articulo", data)
        mock_deshab.assert_called_once_with("emp", 2, 9)

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch(
        "mpr.services_maquina_linea.deshabilitar_articulo_maquina",
        return_value=(False, "El artículo no estaba habilitado en esta máquina."),
    )
    def test_post_deshabilitar_error_400(self, _mock_deshab, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/articulos/accion/",
            data=json.dumps({"accion": "deshabilitar", "id_maquina": 2, "id_articulo": 9}),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertFalse(data["ok"])


class MaquinaObservacionPlanillaAPIViewTest(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = MaquinaObservacionPlanillaAPIView()

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch(
        "mpr.services_maquina_linea.guardar_observacion_planilla_maquina",
        return_value=(True, None, "Observación OK"),
    )
    def test_post_ok(self, mock_guardar, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/observacion-planilla/",
            data=json.dumps({"id_maquina": 3, "observacion": "Observación OK"}),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["observacion_planilla"], "Observación OK")
        mock_guardar.assert_called_once_with("emp", 3, "Observación OK")

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch(
        "mpr.services_maquina_linea.guardar_observacion_planilla_maquina",
        return_value=(True, None, ""),
    )
    def test_post_vacio_ok(self, mock_guardar, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/observacion-planilla/",
            data=json.dumps({"id_maquina": 3, "observacion": "   "}),
            content_type="application/json",
        )
        resp = self.view.post(req)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        self.assertEqual(data["observacion_planilla"], "")
        mock_guardar.assert_called_once_with("emp", 3, "   ")

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch(
        "mpr.services_maquina_linea.guardar_observacion_planilla_maquina",
        return_value=(False, "La observación no puede superar 220 caracteres.", ""),
    )
    def test_post_error_longitud_400(self, _mock_guardar, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/observacion-planilla/",
            data=json.dumps({"id_maquina": 3, "observacion": "x" * 221}),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertFalse(data["ok"])

    @patch("mpr.views._get_base_empresa", return_value="")
    def test_post_empresa_invalida_400(self, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/observacion-planilla/",
            data=json.dumps({"id_maquina": 3, "observacion": "texto"}),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertFalse(data["ok"])

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch(
        "mpr.services_maquina_linea.guardar_observacion_planilla_maquina",
        return_value=(False, "Máquina no encontrada.", ""),
    )
    def test_post_maquina_inexistente_400(self, _mock_guardar, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/observacion-planilla/",
            data=json.dumps({"id_maquina": 999, "observacion": "texto"}),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertIn("no encontrada", data["error"].lower())
