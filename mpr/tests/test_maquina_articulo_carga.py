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
    MaquinasCargaArticulosView,
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


class OperariosRosterPorFranjaTest(SimpleTestCase):
    """Operadores de la planilla CQ tomados del roster (Planificación de turnos)."""

    def test_franja_por_nombre_turno(self):
        from mpr.services import _franja_horaria_turno

        self.assertEqual(_franja_horaria_turno("Turno Mañana", None), "manana")
        self.assertEqual(_franja_horaria_turno("MANANA", None), "manana")
        self.assertEqual(_franja_horaria_turno("Tarde", None), "tarde")
        self.assertEqual(_franja_horaria_turno("Nocturno... noche", None), "noche")

    def test_franja_por_hora_inicio_fallback(self):
        from mpr.services import _franja_horaria_turno

        self.assertEqual(_franja_horaria_turno("Turno A", "06:00"), "manana")
        self.assertEqual(_franja_horaria_turno("Turno B", "14:00"), "tarde")
        self.assertEqual(_franja_horaria_turno("Turno C", "22:00"), "noche")
        self.assertIsNone(_franja_horaria_turno("Turno D", None))

    @patch("mpr.services.listar_empleados_operarios")
    @patch("mpr.services.listar_turnos")
    @patch("mpr.repositories.turno_roster.listar_roster_rango")
    def test_agrupa_nombres_en_mayusculas_por_franja(
        self, mock_roster, mock_turnos, mock_operarios
    ):
        from mpr.services import operarios_roster_por_franja

        mock_roster.return_value = [
            {"id_operario": 1, "id_mpr_turno": 10, "nombre_turno": "Mañana"},
            {"id_operario": 2, "id_mpr_turno": 10, "nombre_turno": "Mañana"},
            {"id_operario": 3, "id_mpr_turno": 20, "nombre_turno": "Turno B"},
        ]
        mock_turnos.return_value = [
            {"id": 10, "nombre": "Mañana", "hora_inicio": "06:00"},
            {"id": 20, "nombre": "Turno B", "hora_inicio": "22:00"},
        ]
        mock_operarios.return_value = [
            {"id": 1, "label": "Juan Pérez"},
            {"id": 2, "label": "Ana Gómez"},
            {"id": 3, "label": "Luis Díaz"},
        ]
        out = operarios_roster_por_franja("emp", date(2026, 7, 21))
        self.assertEqual(out["manana"], "JUAN PÉREZ, ANA GÓMEZ")
        self.assertEqual(out["tarde"], "")
        self.assertEqual(out["noche"], "LUIS DÍAZ")

    @patch("mpr.repositories.turno_roster.listar_roster_rango", return_value=[])
    def test_roster_vacio_devuelve_franjas_vacias(self, _mock_roster):
        from mpr.services import operarios_roster_por_franja

        out = operarios_roster_por_franja("emp", date(2026, 7, 21))
        self.assertEqual(out, {"manana": "", "tarde": "", "noche": ""})

    def test_empresa_invalida_devuelve_franjas_vacias(self):
        from mpr.services import operarios_roster_por_franja

        out = operarios_roster_por_franja("", date(2026, 7, 21))
        self.assertEqual(out, {"manana": "", "tarde": "", "noche": ""})

    @patch(
        "mpr.repositories.operario_linea.lineas_habituales_vigentes",
        return_value={1: 1, 2: 1},
    )
    @patch("mpr.services.listar_empleados_operarios")
    @patch("mpr.services.listar_turnos")
    @patch("mpr.repositories.turno_roster.listar_roster_rango")
    def test_resuelve_override_antes_de_linea_habitual(
        self, mock_roster, mock_turnos, mock_operarios, _mock_habituales
    ):
        from mpr.services import operarios_roster_por_linea

        mock_roster.return_value = [
            {
                "id_operario": 1,
                "id_mpr_turno": 10,
                "nombre_turno": "Mañana",
                "id_mpr_linea": 2,
            },
            {
                "id_operario": 2,
                "id_mpr_turno": 10,
                "nombre_turno": "Mañana",
                "id_mpr_linea": None,
            },
        ]
        mock_turnos.return_value = [
            {"id": 10, "nombre": "Mañana", "hora_inicio": "06:00"},
        ]
        mock_operarios.return_value = [
            {"id": 1, "label": "Juan Pérez"},
            {"id": 2, "label": "Ana Gómez"},
        ]

        out = operarios_roster_por_linea("emp", date(2026, 7, 21), [1, 2])

        self.assertEqual(out[1]["manana"], "ANA GÓMEZ")
        self.assertEqual(out[2]["manana"], "JUAN PÉREZ")

    @patch("mpr.services.operarios_roster_por_linea")
    @patch("mpr.services_maquina_linea.construir_grilla_carga_articulos")
    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_vista_entrega_operadores_solo_de_lineas_en_grilla(
        self, _base, mock_grilla, mock_operarios_por_linea
    ):
        mock_grilla.return_value = {
            "maquinas": [
                {"id": 10, "id_linea_actual": 1},
                {"id": 20, "id_linea_actual": 2},
                {"id": 30, "id_linea_actual": None},
            ],
            "lineas": [],
            "id_linea_filtro": None,
            "fecha_hoy": date.today(),
        }
        mock_operarios_por_linea.return_value = {
            1: {"manana": "ANA GÓMEZ", "tarde": "", "noche": ""},
            2: {"manana": "JUAN PÉREZ", "tarde": "", "noche": ""},
        }
        request = RequestFactory().get("/mpr/maquinas/carga-articulos/")
        request.session = {}
        view = MaquinasCargaArticulosView()
        view.setup(request)

        context = view.get_context_data()

        self.assertEqual(context["operadores_por_linea"], mock_operarios_por_linea.return_value)
        mock_operarios_por_linea.assert_called_once_with(
            "emp", date.today(), {1, 2}
        )
