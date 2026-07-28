"""Tests Consulta de partes y cupo Fabricando live."""

from datetime import date
from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from mpr.views import (
    ParteCupoFabricandoView,
    PartesConsultaView,
    _abrir_url_parte_consulta,
    _usuario_puede_consultar_partes,
    _usuario_ve_todos_los_partes,
)


def _mock_user(*permisos: str):
    user = MagicMock(is_authenticated=True)
    user.is_admin.return_value = False
    user.cod_usuario = "test"
    user.roles.all.return_value = []
    perm_set = set(permisos)

    def tiene_permiso(p):
        return p in perm_set

    user.tiene_permiso.side_effect = tiene_permiso
    return user


class TestHelpersConsultaPartes(SimpleTestCase):
    def test_puede_consultar_con_ver_aprobar_o_parte_operario(self):
        self.assertTrue(_usuario_puede_consultar_partes(_mock_user("mpr.ver")))
        self.assertTrue(_usuario_puede_consultar_partes(_mock_user("mpr.aprobar_parte")))
        self.assertTrue(_usuario_puede_consultar_partes(_mock_user("mpr.parte_operario")))
        self.assertFalse(_usuario_puede_consultar_partes(_mock_user()))

    def test_supervisor_ve_todos(self):
        self.assertTrue(_usuario_ve_todos_los_partes(_mock_user("mpr.ver")))
        self.assertTrue(_usuario_ve_todos_los_partes(_mock_user("mpr.aprobar_parte")))
        self.assertFalse(_usuario_ve_todos_los_partes(_mock_user("mpr.parte_operario")))

    def test_abrir_url_movil_mismo_usuario(self):
        parte = {
            "origen": "movil_operario",
            "id_usuario": 42,
            "fecha_str": "21/07/2026",
        }
        url = _abrir_url_parte_consulta(parte, 42)
        self.assertEqual(url, reverse("mpr:parte_movil_operario"))

    def test_abrir_url_escritorio_o_otro_usuario(self):
        parte = {
            "origen": "movil_operario",
            "id_usuario": 99,
            "fecha_str": "21/07/2026",
        }
        url = _abrir_url_parte_consulta(parte, 42)
        self.assertIn(reverse("mpr:parte_produccion"), url)
        self.assertIn("fecha=21%2F07%2F2026", url)

        parte2 = {"origen": "directo_supervisor", "id_usuario": 1, "fecha_str": "01/01/2026"}
        url2 = _abrir_url_parte_consulta(parte2, 1)
        self.assertIn("fecha=01%2F01%2F2026", url2)


class ListarPartesConsultaFechaStrTest(SimpleTestCase):
    """to_date_or_none devuelve ISO str; fecha_str debe ser dd/MM/yyyy."""

    @patch("mpr.repositories.parte.mysql_cursor")
    def test_fecha_str_ddmmyyyy_desde_iso(self, mock_cursor_ctx):
        from mpr.repositories.parte import listar_partes_consulta

        cursor = mock_cursor_ctx.return_value.__enter__.return_value
        cursor.fetchone.return_value = None  # sin tabla usuarios
        cursor.fetchall.return_value = [
            {
                "id_mpr_parte": 1,
                "fecha_produccion": date(2026, 7, 22),
                "id_mpr_turno": 1,
                "origen": "directo_supervisor",
                "estado": "aprobado",
                "id_usuario": 5,
                "registrado_en": None,
                "turno_nombre": "Mañana",
                "usuario_nombre": "Sup",
                "total_pares": 12,
            }
        ]
        filas = listar_partes_consulta("emp")
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["fecha_str"], "22/07/2026")
        self.assertEqual(filas[0]["fecha_produccion"], "2026-07-22")


class PartesConsultaViewTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.services.listar_partes_consulta")
    def test_supervisor_ve_todos_sin_filtro_usuario(
        self, mock_listar, _base
    ):
        mock_listar.return_value = [
            {
                "id_parte": 1,
                "fecha_produccion": date(2026, 7, 21),
                "fecha_str": "21/07/2026",
                "turno_nombre": "Mañana",
                "origen": "directo_supervisor",
                "estado": "aprobado",
                "id_usuario": 5,
                "usuario_nombre": "Supervisor",
                "total_pares": 24.0,
            }
        ]
        request = self.factory.get("/mpr/partes-consulta/")
        request.session = {"user": {"base_empresa": "empresa_test", "id_usuario": 5}}
        request.user = _mock_user("mpr.ver")

        view = PartesConsultaView()
        view.setup(request)
        context = view.get_context_data()

        mock_listar.assert_called_once()
        kwargs = mock_listar.call_args.kwargs
        self.assertIsNone(kwargs.get("id_usuario"))
        self.assertTrue(context["es_supervisor_partes"])
        self.assertEqual(len(context["partes"]), 1)
        self.assertIn("abrir_url", context["partes"][0])

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.services.listar_partes_consulta")
    def test_operario_filtra_por_id_usuario_sesion(self, mock_listar, _base):
        mock_listar.return_value = []
        request = self.factory.get(
            "/mpr/partes-consulta/?fecha_desde=2026-07-01&fecha_hasta=2026-07-31&estado=pendiente"
        )
        request.session = {"user": {"base_empresa": "empresa_test", "id_usuario": 77}}
        request.user = _mock_user("mpr.parte_operario")

        view = PartesConsultaView()
        view.setup(request)
        view.get_context_data()

        kwargs = mock_listar.call_args.kwargs
        self.assertEqual(kwargs["id_usuario"], 77)
        self.assertEqual(kwargs["fecha_desde"], date(2026, 7, 1))
        self.assertEqual(kwargs["fecha_hasta"], date(2026, 7, 31))
        self.assertEqual(kwargs["estado"], "pendiente")

    def test_sin_permiso_lanza_permission_denied(self):
        request = self.factory.get("/mpr/partes-consulta/")
        request.session = {"user": {"base_empresa": "empresa_test", "id_usuario": 1}}
        request.user = _mock_user()

        view = PartesConsultaView.as_view()
        with self.assertRaises(PermissionDenied):
            view(request)


class ParteCupoFabricandoViewTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.services.cupo_fabricando_por_articulo", return_value={1459: 102.0, 2: 0.0})
    def test_get_json_cupos(self, mock_cupo, _base):
        request = self.factory.get("/mpr/parte-produccion/cupo-fabricando/?ids=1459,2,xx")
        request.session = {"user": {"base_empresa": "empresa_test", "id_usuario": 1}}
        request.user = _mock_user("mpr.ver")

        response = ParteCupoFabricandoView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        import json

        data = json.loads(response.content.decode())
        self.assertEqual(data["cupos"]["1459"], 102.0)
        self.assertEqual(data["cupos"]["2"], 0.0)
        mock_cupo.assert_called_once_with("empresa_test", [1459, 2])

    @patch("mpr.views._get_base_empresa", return_value="")
    def test_sin_empresa_devuelve_vacio(self, _base):
        request = self.factory.get("/mpr/parte-produccion/cupo-fabricando/?ids=1")
        request.session = {"user": {}}
        request.user = _mock_user("mpr.ver")

        response = ParteCupoFabricandoView.as_view()(request)
        import json

        data = json.loads(response.content.decode())
        self.assertEqual(data, {"cupos": {}})


class PartesConsultaIntegracionTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        patcher_perm = patch("mpr.views._usuario_tiene_permiso_mpr", return_value=True)
        patcher_perm.start()
        self.addCleanup(patcher_perm.stop)

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.services.listar_partes_consulta", return_value=[])
    def test_get_consulta_200(self, _listar, _base):
        request = self.factory.get(reverse("mpr:partes_consulta"))
        request.session = {"user": {"base_empresa": "empresa_test", "id_usuario": 1}}
        request.user = _mock_user("mpr.ver")

        response = PartesConsultaView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "mpr/partes_consulta.html")

    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    @patch("mpr.services.cupo_fabricando_por_articulo", return_value={10: 55.0})
    def test_get_cupo_json_200(self, _cupo, _base):
        request = self.factory.get(
            reverse("mpr:parte_cupo_fabricando"), {"ids": "10"}
        )
        request.session = {"user": {"base_empresa": "empresa_test", "id_usuario": 1}}
        request.user = _mock_user("mpr.ver")

        response = ParteCupoFabricandoView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        import json

        data = json.loads(response.content.decode())
        self.assertEqual(data["cupos"]["10"], 55.0)
