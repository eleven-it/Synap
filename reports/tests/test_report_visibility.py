"""Visibilidad ReportDefinition.is_visible (solo usuario cod_usuario supervisor)."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from core.utils.permissions import user_has_full_access
from reports.services.report_visibility import (
    COMMAND_CENTER_SLUG,
    command_center_visible_for_user,
    report_visible_for_user,
)


class _UserStub:
    is_authenticated = True

    def __init__(self, permisos=None, cod_usuario="vendedor"):
        self.cod_usuario = cod_usuario
        self._permisos = set(permisos or [])

    def get_permisos_totales(self):
        return self._permisos

    def tiene_permiso(self, code):
        if user_has_full_access(self):
            return True
        if code in self._permisos:
            return True
        for perm in self._permisos:
            if perm.endswith(".*"):
                mod = perm[:-2]
                if code.startswith(mod + ".") or code.startswith(mod + "_"):
                    return True
        return False


class ReportVisibleForUserTests(SimpleTestCase):
    def test_activado_visible_para_cualquiera(self):
        report = MagicMock(is_visible=True)
        user = _UserStub(permisos={"reports.ver"})
        self.assertTrue(report_visible_for_user(report, user))

    def test_desactivado_oculto_sin_usuario_supervisor(self):
        report = MagicMock(is_visible=False)
        user = _UserStub(permisos={"reports.view_managerial"}, cod_usuario="lvillanueva")
        self.assertFalse(report_visible_for_user(report, user))

    def test_desactivado_visible_usuario_supervisor(self):
        report = MagicMock(is_visible=False)
        user = _UserStub(cod_usuario="supervisor")
        self.assertTrue(report_visible_for_user(report, user))

    def test_sin_reporte(self):
        user = _UserStub(cod_usuario="supervisor")
        self.assertFalse(report_visible_for_user(None, user))


class CommandCenterVisibleTests(SimpleTestCase):
    @patch("reports.services.report_visibility.get_report_definition")
    def test_puesto_supervisor_gerencial_reporte_desactivado(self, mock_get):
        from core.services.administranet_permisos_usuario import get_permisos_totales_administranet

        mock_get.return_value = MagicMock(slug=COMMAND_CENTER_SLUG, is_visible=False)
        permisos = get_permisos_totales_administranet(
            base_empresa="",
            id_puesto=None,
            cod_usuario="lvillanueva",
            nombre_puesto="Supervisor",
        )
        user = _UserStub(permisos=permisos)
        self.assertFalse(command_center_visible_for_user(user))

    @patch("reports.services.report_visibility.get_report_definition")
    def test_puesto_supervisor_reporte_activado(self, mock_get):
        from core.services.administranet_permisos_usuario import get_permisos_totales_administranet

        mock_get.return_value = MagicMock(slug=COMMAND_CENTER_SLUG, is_visible=True)
        permisos = get_permisos_totales_administranet(
            base_empresa="",
            id_puesto=None,
            cod_usuario="lvillanueva",
            nombre_puesto="Supervisor",
        )
        user = _UserStub(permisos=permisos)
        self.assertTrue(command_center_visible_for_user(user))

    @patch("reports.services.report_visibility.get_report_definition")
    def test_usuario_supervisor_reporte_desactivado(self, mock_get):
        mock_get.return_value = MagicMock(slug=COMMAND_CENTER_SLUG, is_visible=False)
        user = _UserStub(cod_usuario="supervisor", permisos={"reports.view_managerial"})
        self.assertTrue(command_center_visible_for_user(user))

    def test_sin_permiso_gerencial(self):
        user = _UserStub(permisos={"reports.ver"})
        self.assertFalse(command_center_visible_for_user(user))
