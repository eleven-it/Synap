"""Tests de la UI de asignación de permisos por puesto (solo supervisor)."""

from unittest.mock import MagicMock, patch

from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from core.views.views_permisos_puesto import (
    permisos_puesto_gestionar_view,
    permisos_puesto_lista_view,
)


class PermisosPuestoSupervisorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, user_cod="supervisor", session_user=None):
        request = self.factory.get("/core/permisos-puesto/")
        request.session = {
            "user": session_user
            or {"base_empresa": "test_empresa", "id_puesto": 1},
        }
        user = MagicMock()
        user.is_authenticated = True
        user.cod_usuario = user_cod
        request.user = user
        return request

    def test_lista_rechaza_no_supervisor(self):
        request = self._request(user_cod="vendedor")
        with self.assertRaises(PermissionDenied):
            permisos_puesto_lista_view(request)

    @patch("core.views.views_permisos_puesto.AdministraNETPermisosSistemaService")
    def test_lista_ok_supervisor(self, mock_ps_cls):
        mock_ps_cls.return_value.listar_puestos.return_value = [
            {"id": 2, "nombre": "Ventas"},
        ]
        request = self._request()
        response = permisos_puesto_lista_view(request)
        self.assertEqual(response.status_code, 200)

    @patch("core.views.views_permisos_puesto.sincronizar_permisos_synap_para_empresa")
    @patch("core.views.views_permisos_puesto.AdministraNETPermisosMenuService")
    @patch("core.views.views_permisos_puesto.AdministraNETPermisoSistemaService")
    @patch("core.views.views_permisos_puesto.AdministraNETPuestosService")
    def test_gestionar_ok_supervisor(
        self, mock_puestos_cls, mock_perm_cls, mock_menu_cls, _mock_sync
    ):
        mock_puestos_cls.return_value.obtener_puesto.return_value = {
            "id": 2,
            "nombre": "Ventas",
        }
        mock_perm_cls.return_value.listar_permisos.return_value = []
        mock_perm_cls.return_value.obtener_grupos.return_value = ["Synap"]
        mock_menu_cls.return_value.obtener_estructura_menu.return_value = {}
        mock_menu_cls.return_value.obtener_permisos_puesto.return_value = set()

        request = self._request()
        response = permisos_puesto_gestionar_view(request, id_puesto=2)
        self.assertEqual(response.status_code, 200)
