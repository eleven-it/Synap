"""Tests backend carga en grilla de artículos por máquina (MPR)."""
import inspect
import json
from datetime import date, timedelta
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from mpr.repositories import maquina_articulo as repo_art
from mpr.services_maquina_linea import (
    buscar_articulos,
    cantidades_parte_planilla_por_fecha,
    construir_datos_planilla_control_calidad,
    construir_grilla_carga_articulos,
    deshabilitar_articulo_maquina,
    guardar_observacion_planilla_maquina,
    habilitar_articulo_maquina,
)
from mpr.views import (
    MaquinaArticuloAccionAPIView,
    MaquinaArticuloBuscarAPIView,
    MaquinaObservacionPlanillaAPIView,
    MaquinaPlanillaControlCalidadAPIView,
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
        self.assertEqual(out["fecha"], date.today())
        self.assertFalse(out["es_fecha_pasada"])
        mock_articulos.assert_called_once_with("emp", date.today())

    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    @patch("mpr.services_maquina_linea.listar_lineas")
    def test_usa_fecha_parametro_y_marca_pasada(
        self, mock_lineas, mock_maquinas, mock_articulos
    ):
        mock_lineas.return_value = []
        mock_maquinas.return_value = []
        mock_articulos.return_value = {}
        fecha = date.today() - timedelta(days=3)
        out = construir_grilla_carga_articulos("emp", fecha=fecha)
        self.assertEqual(out["fecha"], fecha)
        self.assertTrue(out["es_fecha_pasada"])
        mock_articulos.assert_called_once_with("emp", fecha)

    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    @patch("mpr.services_maquina_linea.listar_lineas")
    def test_fecha_futura_se_clampa_a_hoy(
        self, mock_lineas, mock_maquinas, mock_articulos
    ):
        mock_lineas.return_value = []
        mock_maquinas.return_value = []
        mock_articulos.return_value = {}
        futuro = date.today() + timedelta(days=5)
        out = construir_grilla_carga_articulos("emp", fecha=futuro)
        self.assertEqual(out["fecha"], date.today())
        mock_articulos.assert_called_once_with("emp", date.today())


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
        mock_hab.assert_called_once_with("emp", 1, 5, desde=date.today())

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_maquina")
    @patch("mpr.services_maquina_linea.habilitar_articulo_maquina", return_value=(True, None))
    def test_post_habilitar_con_fecha_pasada(self, mock_hab, mock_vigentes, _base):
        fecha = date(2026, 3, 10)
        mock_vigentes.return_value = [{"id_articulo": 5}]
        req = self.rf.post(
            "/mpr/maquinas/api/articulos/accion/",
            data=json.dumps({
                "accion": "habilitar",
                "id_maquina": 1,
                "id_articulo": 5,
                "fecha": "10/03/2026",
            }),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 200)
        mock_hab.assert_called_once_with("emp", 1, 5, desde=fecha)
        mock_vigentes.assert_called_once_with("emp", 1, fecha=fecha)

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
        mock_deshab.assert_called_once_with("emp", 2, 9, fecha=date.today())

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch(
        "mpr.services_maquina_linea.deshabilitar_articulo_maquina",
        return_value=(False, "No se puede quitar el artículo: hay parte de producción registrado para esa máquina y fecha."),
    )
    def test_post_deshabilitar_bloqueado_por_parte_400(self, _mock_deshab, _base):
        req = self.rf.post(
            "/mpr/maquinas/api/articulos/accion/",
            data=json.dumps({
                "accion": "deshabilitar",
                "id_maquina": 2,
                "id_articulo": 9,
                "fecha": date.today().strftime("%d/%m/%Y"),
            }),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertIn("parte de producción", data["error"].lower())

    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_post_fecha_futura_400(self, _base):
        futuro = (date.today() + timedelta(days=2)).strftime("%d/%m/%Y")
        req = self.rf.post(
            "/mpr/maquinas/api/articulos/accion/",
            data=json.dumps({
                "accion": "habilitar",
                "id_maquina": 1,
                "id_articulo": 5,
                "fecha": futuro,
            }),
            content_type="application/json",
        )
        resp = self.view.post(req)
        self.assertEqual(resp.status_code, 400)

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
            "fecha": date.today(),
            "es_fecha_pasada": False,
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

    @patch("mpr.services.operarios_roster_por_linea")
    @patch("mpr.services_maquina_linea.construir_grilla_carga_articulos")
    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_vista_parsea_fecha_get_ddmmyyyy(
        self, _base, mock_grilla, mock_operarios_por_linea
    ):
        fecha = date(2026, 3, 10)
        mock_grilla.return_value = {
            "maquinas": [],
            "lineas": [],
            "id_linea_filtro": None,
            "fecha_hoy": date.today(),
            "fecha": fecha,
            "es_fecha_pasada": True,
        }
        mock_operarios_por_linea.return_value = {}
        request = RequestFactory().get("/mpr/maquinas/carga-articulos/?fecha=10/03/2026")
        request.session = {}
        view = MaquinasCargaArticulosView()
        view.setup(request)

        context = view.get_context_data()

        self.assertEqual(context["fecha_str"], "10/03/2026")
        mock_grilla.assert_called_once_with("emp", id_linea=None, fecha=fecha)
        mock_operarios_por_linea.assert_called_once_with("emp", fecha, set())


class HabilitarDeshabilitarArticuloMaquinaServiceTest(SimpleTestCase):
    @patch("mpr.services_maquina_linea.repo_art.habilitar_articulo")
    @patch("mpr.services_maquina_linea.repo_art.articulo_vigente", return_value=False)
    @patch("mpr.services_maquina_linea.repo_art.articulos_por_ids", return_value={5: {}})
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 1})
    def test_habilitar_hoy_vigencia_abierta(self, *_mocks):
        ok, error = habilitar_articulo_maquina("emp", 1, 5, desde=date.today())
        self.assertTrue(ok)
        self.assertIsNone(error)
        from mpr.services_maquina_linea import repo_art

        repo_art.habilitar_articulo.assert_called_once_with(
            "emp", 1, 5, date.today(), hasta=None
        )

    @patch("mpr.services_maquina_linea.repo_art.habilitar_articulo")
    @patch("mpr.services_maquina_linea.repo_art.articulo_vigente", return_value=False)
    @patch("mpr.services_maquina_linea.repo_art.articulos_por_ids", return_value={5: {}})
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 1})
    def test_habilitar_fecha_pasada_solo_ese_dia(self, *_mocks):
        fecha = date.today() - timedelta(days=2)
        ok, error = habilitar_articulo_maquina("emp", 1, 5, desde=fecha)
        self.assertTrue(ok)
        from mpr.services_maquina_linea import repo_art

        repo_art.habilitar_articulo.assert_called_once_with(
            "emp", 1, 5, fecha, hasta=fecha + timedelta(days=1)
        )

    @patch("mpr.services_maquina_linea.repo_art.articulo_vigente", return_value=True)
    @patch("mpr.services_maquina_linea.repo_art.articulos_por_ids", return_value={5: {}})
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 1})
    def test_habilitar_ya_vigente_error(self, *_mocks):
        ok, error = habilitar_articulo_maquina("emp", 1, 5, desde=date.today())
        self.assertFalse(ok)
        self.assertIn("ya está habilitado", error.lower())

    @patch("mpr.services_maquina_linea.repo_art.habilitar_articulo")
    @patch("mpr.services_maquina_linea.repo_art.articulo_vigente", return_value=False)
    @patch("mpr.services_maquina_linea.repo_art.articulos_por_ids", return_value={5: {}})
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 1})
    def test_habilitar_fecha_futura_rechazada(self, *_mocks):
        futuro = date.today() + timedelta(days=1)
        ok, error = habilitar_articulo_maquina("emp", 1, 5, desde=futuro)
        self.assertFalse(ok)
        self.assertIn("futur", error.lower())

    @patch("mpr.services_maquina_linea.repo_art.deshabilitar_articulo", return_value=1)
    @patch("mpr.repositories.parte.tiene_parte_maquina_articulo_fecha", return_value=False)
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 1})
    def test_deshabilitar_hoy_cierra_vigencia(self, *_mocks):
        ok, error = deshabilitar_articulo_maquina("emp", 1, 5, fecha=date.today())
        self.assertTrue(ok)
        from mpr.services_maquina_linea import repo_art

        repo_art.deshabilitar_articulo.assert_called_once_with(
            "emp", 1, 5, date.today()
        )

    @patch("mpr.services_maquina_linea.repo_art.quitar_cobertura_fecha", return_value=True)
    @patch("mpr.repositories.parte.tiene_parte_maquina_articulo_fecha", return_value=False)
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 1})
    def test_deshabilitar_fecha_pasada_quita_cobertura(self, *_mocks):
        fecha = date.today() - timedelta(days=1)
        ok, error = deshabilitar_articulo_maquina("emp", 1, 5, fecha=fecha)
        self.assertTrue(ok)
        from mpr.services_maquina_linea import repo_art

        repo_art.quitar_cobertura_fecha.assert_called_once_with("emp", 1, 5, fecha)

    @patch("mpr.repositories.parte.tiene_parte_maquina_articulo_fecha", return_value=True)
    @patch("mpr.services_maquina_linea.repo.obtener_maquina", return_value={"id": 1})
    def test_deshabilitar_bloqueado_si_hay_parte(self, *_mocks):
        ok, error = deshabilitar_articulo_maquina("emp", 1, 5, fecha=date.today())
        self.assertFalse(ok)
        self.assertIn("parte de producción", error.lower())


class ConstruirDatosPlanillaControlCalidadTest(SimpleTestCase):
    @patch("mpr.services.operarios_roster_por_linea")
    @patch("mpr.services_maquina_linea.cantidades_parte_planilla_por_fecha")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    def test_fecha_futura_usa_hoy_para_articulos_y_cantidades_vacias(
        self, mock_maquinas, mock_articulos, mock_cantidades, mock_operarios
    ):
        hoy = date.today()
        futuro = date(hoy.year + 1, 1, 15)
        mock_maquinas.return_value = [
            {
                "id": 10,
                "codigo": "1",
                "nombre": "M1",
                "id_linea_actual": 1,
                "observacion_planilla": "",
            }
        ]
        mock_articulos.return_value = {
            10: [{"id_articulo": 100, "descripcion_articulo": "Art", "color": "", "talle": ""}],
        }
        mock_operarios.return_value = {1: {"manana": "JUAN", "tarde": "", "noche": ""}}

        out = construir_datos_planilla_control_calidad("emp", futuro)

        self.assertTrue(out["es_futuro"])
        self.assertEqual(out["fecha_articulos"], hoy.isoformat())
        mock_articulos.assert_called_once_with("emp", hoy)
        mock_cantidades.assert_not_called()
        cant = out["maquinas"][0]["articulos"][0]["cantidades"]
        self.assertIsNone(cant["manana"])
        self.assertIsNone(cant["tarde"])
        self.assertIsNone(cant["noche"])

    @patch("mpr.services.operarios_roster_por_linea")
    @patch("mpr.services_maquina_linea.cantidades_parte_planilla_por_fecha")
    @patch("mpr.services_maquina_linea.listar_articulos_vigentes_todas_maquinas")
    @patch("mpr.services_maquina_linea.listar_maquinas")
    def test_fecha_pasada_pide_vigentes_y_cantidades_a_esa_fecha(
        self, mock_maquinas, mock_articulos, mock_cantidades, mock_operarios
    ):
        fecha = date(2026, 3, 10)
        mock_maquinas.return_value = [
            {
                "id": 10,
                "codigo": "1",
                "nombre": "M1",
                "id_linea_actual": 1,
                "observacion_planilla": "Nota",
            }
        ]
        mock_articulos.return_value = {
            10: [{"id_articulo": 100, "descripcion_articulo": "Art", "color": "R", "talle": "M"}],
        }
        mock_cantidades.return_value = {(10, 100): {"manana": 12.0, "tarde": 0.0, "noche": 0.0}}
        mock_operarios.return_value = {1: {"manana": "ANA", "tarde": "", "noche": ""}}

        out = construir_datos_planilla_control_calidad("emp", fecha)

        self.assertFalse(out["es_futuro"])
        self.assertEqual(out["fecha_articulos"], fecha.isoformat())
        mock_articulos.assert_called_once_with("emp", fecha)
        mock_cantidades.assert_called_once_with("emp", fecha)
        self.assertEqual(out["maquinas"][0]["articulos"][0]["cantidades"]["manana"], 12)
        mock_operarios.assert_called_once_with("emp", fecha, {1})


class CantidadesPartePlanillaPorFechaTest(SimpleTestCase):
    @patch("mpr.services_maquina_linea.mysql_cursor")
    @patch("mpr.services.listar_turnos")
    def test_agrega_aprobado_y_declarado_por_franja(self, mock_turnos, mock_cursor_ctx):
        mock_turnos.return_value = [
            {"id": 10, "nombre": "Mañana", "hora_inicio": "06:00"},
            {"id": 20, "nombre": "Tarde", "hora_inicio": "14:00"},
        ]
        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            {
                "id_mpr_maquina": 1,
                "id_articulo": 100,
                "estado": "aprobado",
                "id_mpr_turno": 10,
                "cantidad_declarada": 5,
                "cantidad_aprobada": 4,
            },
            {
                "id_mpr_maquina": 1,
                "id_articulo": 100,
                "estado": "pendiente",
                "id_mpr_turno": 20,
                "cantidad_declarada": 3,
                "cantidad_aprobada": None,
            },
        ]

        out = cantidades_parte_planilla_por_fecha("emp", date(2026, 7, 21))

        self.assertEqual(out[(1, 100)]["manana"], 4.0)
        self.assertEqual(out[(1, 100)]["tarde"], 3.0)
        self.assertEqual(out[(1, 100)]["noche"], 0.0)


class MaquinaPlanillaControlCalidadAPIViewTest(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.view = MaquinaPlanillaControlCalidadAPIView()

    @patch("mpr.views._get_base_empresa", return_value="emp")
    def test_get_fecha_invalida_400(self, _base):
        req = self.rf.get("/mpr/maquinas/api/planilla-control-calidad/?fecha=31-07-2026")
        resp = self.view.get(req)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content)
        self.assertFalse(data["ok"])

    @patch("mpr.views._get_base_empresa", return_value="emp")
    @patch("mpr.services_maquina_linea.construir_datos_planilla_control_calidad")
    def test_get_ok_200(self, mock_construir, _base):
        mock_construir.return_value = {
            "fecha": "2026-07-21",
            "fecha_articulos": "2026-07-21",
            "es_futuro": False,
            "maquinas": [],
            "operadores_por_linea": {},
        }
        req = self.rf.get(
            "/mpr/maquinas/api/planilla-control-calidad/?fecha=2026-07-21&id_linea=1"
        )
        resp = self.view.get(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data["ok"])
        mock_construir.assert_called_once_with("emp", date(2026, 7, 21), id_linea=1)
