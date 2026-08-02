"""Visibilidad de tarjetas en /core/dashboard/ según permisos."""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from core.utils.permissions import user_has_permission
from core.views.views_general import get_dashboard_home_visibility


class _UserStub:
    is_authenticated = True

    def __init__(self, permisos=None, cod_usuario="vendedor"):
        self.cod_usuario = cod_usuario
        self._permisos = set(permisos or [])

    def get_permisos_totales(self):
        return self._permisos

    def tiene_permiso(self, code):
        if "*" in self._permisos or self.cod_usuario.lower() == "supervisor":
            return True
        if code in self._permisos:
            return True
        for perm in self._permisos:
            if perm.endswith(".*"):
                mod = perm[:-2]
                if code.startswith(mod + ".") or code.startswith(mod + "_"):
                    return True
        return False


class UserHasPermissionTests(SimpleTestCase):
    def test_comodin_reports(self):
        user = _UserStub(permisos={"reports.*"})
        self.assertTrue(user_has_permission(user, "reports.view_managerial"))
        self.assertTrue(user_has_permission(user, "reports.ver"))

    def test_sin_permiso(self):
        user = _UserStub(permisos={"reports.ver"})
        self.assertFalse(user_has_permission(user, "reports.view_managerial"))


class DashboardHomeVisibilityTests(SimpleTestCase):
    def test_sin_gerencial_ni_reports_en_menu(self):
        user = _UserStub(permisos={"reports.ver"})
        vis = get_dashboard_home_visibility(user, [])
        self.assertFalse(vis["show_command_center"])
        self.assertFalse(vis["show_reports"])
        self.assertFalse(vis["show_workspace"])
        self.assertFalse(vis["show_mpr"])

    def test_con_mpr_ver_muestra_tarjeta_mpr(self):
        user = _UserStub(permisos={"mpr.ver"})
        with patch(
            "reports.services.report_visibility.command_center_visible_for_user",
            return_value=False,
        ):
            vis = get_dashboard_home_visibility(user, [])
        self.assertTrue(vis["show_mpr"])

    def test_supervisor_muestra_tarjeta_mpr(self):
        user = _UserStub(cod_usuario="supervisor")
        with patch(
            "reports.services.report_visibility.command_center_visible_for_user",
            return_value=False,
        ):
            vis = get_dashboard_home_visibility(user, [])
        self.assertTrue(vis["show_mpr"])

    @patch("reports.services.report_visibility.command_center_visible_for_user", return_value=True)
    def test_con_gerencial_y_reports_en_menu(self, _cc):
        user = _UserStub(permisos={"reports.view_managerial", "reports.ver"})
        apps = [{"id": "reports", "nombre": "Reports", "url": "/reports/"}]
        vis = get_dashboard_home_visibility(user, apps)
        self.assertTrue(vis["show_command_center"])
        self.assertTrue(vis["show_reports"])
        self.assertTrue(vis["show_workspace"])

    @patch("reports.services.report_visibility.command_center_visible_for_user", return_value=False)
    def test_puesto_supervisor_reporte_desactivado_no_muestra_hero(self, _cc):
        from core.services.administranet_permisos_usuario import get_permisos_totales_administranet

        permisos = get_permisos_totales_administranet(
            base_empresa="",
            id_puesto=None,
            cod_usuario="lvillanueva",
            nombre_puesto="Supervisor",
        )
        user = _UserStub(permisos=permisos)
        apps = [{"id": "reports", "nombre": "Reports", "url": "/reports/"}]
        vis = get_dashboard_home_visibility(user, apps)
        self.assertFalse(vis["show_command_center"])
        self.assertTrue(vis["show_reports"])

    def test_usuario_anonimo(self):
        user = SimpleNamespace(is_authenticated=False)
        vis = get_dashboard_home_visibility(user, [{"id": "reports"}])
        self.assertFalse(vis["show_command_center"])
