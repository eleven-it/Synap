"""Tests PWA Tablero KPIs e Inventario MPR."""

from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from mpr.views import InventarioMprView, TableroView


def _mock_user(*permisos: str):
    user = MagicMock(is_authenticated=True)
    user.is_admin.return_value = False
    user.is_superuser = False
    user.cod_usuario = "supervisor_mpr"
    user.roles.all.return_value = []
    perm_set = set(permisos)

    def tiene_permiso(p):
        return p in perm_set

    user.tiene_permiso.side_effect = tiene_permiso
    user.get_permisos_totales.return_value = perm_set
    return user


class TestPwaTableroInventario(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("mpr.services.contar_pedidos_fabrica", return_value=0)
    @patch("mpr.services.construir_resumen_tablero_kpi")
    @patch(
        "mpr.presentacion_operativa.enriquecer_resumen_tablero_kpi_presentacion",
        side_effect=lambda r, _m: r,
    )
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_tablero_usa_template_mobile_cuando_is_mobile(
        self, _base, _enrich, mock_resumen, _contar
    ):
        mock_resumen.return_value = {
            "kpi_componentes_pendientes": 0,
            "kpi_pending_units": 0,
            "kpi_pending_units_ped": 0,
            "kpi_packs_demanda": 0,
            "kpi_urgent_items": 0,
            "componentes_pendientes": [],
            "top_packs_pendientes": [],
        }
        request = self.factory.get(reverse("mpr:tablero"))
        request.is_mobile = True
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.ver")

        view = TableroView()
        view.setup(request)
        names = view.get_template_names()
        self.assertEqual(names, ["mpr/mobile/tablero.html"])

    @patch("mpr.services.contar_pedidos_fabrica", return_value=0)
    @patch("mpr.services.construir_resumen_tablero_kpi")
    @patch(
        "mpr.presentacion_operativa.enriquecer_resumen_tablero_kpi_presentacion",
        side_effect=lambda r, _m: r,
    )
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_tablero_usa_template_desktop_sin_is_mobile(
        self, _base, _enrich, mock_resumen, _contar
    ):
        mock_resumen.return_value = {
            "kpi_componentes_pendientes": 0,
            "kpi_pending_units": 0,
            "kpi_pending_units_ped": 0,
            "kpi_packs_demanda": 0,
            "kpi_urgent_items": 0,
            "componentes_pendientes": [],
            "top_packs_pendientes": [],
        }
        request = self.factory.get(reverse("mpr:tablero"))
        request.is_mobile = False
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.ver")

        view = TableroView()
        view.setup(request)
        names = view.get_template_names()
        self.assertEqual(names, ["mpr/tablero.html"])

    def test_inventario_403_sin_mpr_ver(self):
        request = self.factory.get(reverse("mpr:inventario"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user()
        with self.assertRaises(PermissionDenied):
            InventarioMprView.as_view()(request)

    @patch("stock.services.inventario_tabla.preparar_filas_inventario_presentacion", return_value=[])
    @patch("stock.services.inventario_tabla.consultar_inventario_tabla")
    @patch("stock.services.inventario_tabla.listar_marcas_catalogo", return_value=[])
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_inventario_200_con_mpr_ver(
        self, _base, _marcas, mock_consultar, _preparar
    ):
        mock_consultar.return_value = {
            "filas": [],
            "total_registros": 0,
            "filas_cargadas": 0,
            "truncado": False,
            "sin_config_mpr": False,
            "etapas": [("Terminado", "Terminado")],
        }
        request = self.factory.get(reverse("mpr:inventario"))
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.ver")
        response = InventarioMprView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    @patch("stock.services.inventario_tabla.preparar_filas_inventario_presentacion", return_value=[])
    @patch("stock.services.inventario_tabla.consultar_inventario_tabla")
    @patch("stock.services.inventario_tabla.listar_marcas_catalogo", return_value=[])
    @patch("mpr.views._get_base_empresa", return_value="empresa_test")
    def test_inventario_template_mobile_cuando_is_mobile(
        self, _base, _marcas, mock_consultar, _preparar
    ):
        mock_consultar.return_value = {
            "filas": [],
            "total_registros": 0,
            "filas_cargadas": 0,
            "truncado": False,
            "sin_config_mpr": False,
            "etapas": [("Terminado", "Terminado")],
        }
        request = self.factory.get(reverse("mpr:inventario"))
        request.is_mobile = True
        request.session = {"user": {"id_usuario": 1, "base_empresa": "empresa_test"}}
        request.user = _mock_user("mpr.ver")

        view = InventarioMprView()
        view.setup(request)
        names = view.get_template_names()
        self.assertEqual(names, ["mpr/mobile/inventario.html"])

    def test_reverse_mpr_inventario(self):
        self.assertEqual(reverse("mpr:inventario"), "/mpr/inventario/")
