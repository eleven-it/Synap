"""Config global de áreas del Command Center."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from reports.models import ReportCategory, ReportDefinition
from reports.services.executive_dashboard.area_visibility import (
    CC_AREA_KEYS,
    DEFAULT_CC_AREAS,
    DETAIL_KEY_TO_AREA,
    filter_urls_by_areas,
    read_cc_areas_config,
    resolve_cc_areas,
    set_cc_areas,
)
from reports.services.report_visibility import COMMAND_CENTER_SLUG


class AreaVisibilityUnitTests(SimpleTestCase):
    def test_defaults_todas_true(self):
        self.assertEqual(set(DEFAULT_CC_AREAS), set(CC_AREA_KEYS))
        self.assertTrue(all(DEFAULT_CC_AREAS.values()))

    @patch(
        "reports.services.executive_dashboard.area_visibility.get_cc_report_definition",
        return_value=None,
    )
    def test_resolve_sin_report_usa_defaults_y_gate_mpr(self, _get):
        areas = resolve_cc_areas(mpr_active=False)
        self.assertTrue(areas["ventas"])
        self.assertFalse(areas["manufactura"])

    @patch(
        "reports.services.executive_dashboard.area_visibility.get_cc_report_definition",
        return_value=None,
    )
    def test_resolve_con_mpr_mantiene_manufactura(self, _get):
        areas = resolve_cc_areas(mpr_active=True)
        self.assertTrue(areas["manufactura"])

    def test_filter_urls_by_areas(self):
        urls = {
            "ventas": "/v/",
            "inventario": "/i/",
            "existencias": "/e/",
        }
        areas = {**DEFAULT_CC_AREAS, "inventario": False}
        out = filter_urls_by_areas(
            urls,
            areas,
            key_to_area={**{k: k for k in urls}, **DETAIL_KEY_TO_AREA},
        )
        self.assertIn("ventas", out)
        self.assertNotIn("inventario", out)
        self.assertNotIn("existencias", out)


class AreaVisibilityPersistTests(TestCase):
    def test_set_cc_areas_persiste_global(self):
        stored = set_cc_areas({"inventario": False, "cruzados": False})
        self.assertFalse(stored["inventario"])
        self.assertFalse(stored["cruzados"])
        self.assertTrue(stored["ventas"])
        report = ReportDefinition.objects.get(
            slug=COMMAND_CENTER_SLUG, empresa__isnull=True
        )
        self.assertEqual(report.category, ReportCategory.MANAGERIAL)
        self.assertFalse(read_cc_areas_config(report)["inventario"])
        effective = resolve_cc_areas(mpr_active=True, report=report)
        self.assertFalse(effective["inventario"])
        self.assertTrue(effective["ventas"])

    def test_set_cc_areas_rechaza_keys_desconocidas(self):
        with self.assertRaises(ValueError):
            set_cc_areas({"foo": True})


class AreaVisibilityApiTests(TestCase):
    def setUp(self):
        ReportDefinition.objects.create(
            empresa=None,
            slug=COMMAND_CENTER_SLUG,
            name="Command Center",
            category=ReportCategory.MANAGERIAL,
            config={"command_center": {"areas": dict(DEFAULT_CC_AREAS)}},
            is_active=True,
            is_visible=True,
        )

    def _user(self, *, supervisor=False, managerial=True):
        user = MagicMock()
        user.is_authenticated = True
        user.is_superuser = False
        user.is_admin = MagicMock(return_value=False)
        user.cod_usuario = "supervisor" if supervisor else "vendedor"
        user.empresa_activa = None
        perms = set()
        if managerial:
            perms.add("reports.view_managerial")
        if supervisor:
            perms.add("*")

        def tiene(code):
            if supervisor or "*" in perms:
                return True
            return code in perms

        user.tiene_permiso = tiene
        user.get_permisos_totales = MagicMock(return_value=perms)
        return user

    @patch(
        "reports.services.report_visibility.command_center_visible_for_user",
        return_value=True,
    )
    @patch(
        "reports.executive_dashboard_api_views.mpr_modulo_activo",
        return_value=True,
    )
    @patch(
        "core.utils.permissions.user_has_permission",
        return_value=True,
    )
    def test_get_areas_ok(self, _perm, _mpr, _vis):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from reports.executive_dashboard_api_views import ExecutiveDashboardAreasAPIView

        factory = APIRequestFactory()
        request = factory.get("/api/reports/executive-dashboard/areas/")
        force_authenticate(request, user=self._user())
        response = ExecutiveDashboardAreasAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("areas", response.data)
        self.assertIn("areas_config", response.data)
        self.assertFalse(response.data["can_edit"])

    @patch(
        "reports.services.report_visibility.command_center_visible_for_user",
        return_value=True,
    )
    @patch(
        "reports.executive_dashboard_api_views.mpr_modulo_activo",
        return_value=True,
    )
    @patch(
        "reports.executive_dashboard_api_views.user_has_full_access",
        return_value=True,
    )
    @patch(
        "core.utils.permissions.user_has_permission",
        return_value=True,
    )
    def test_patch_areas_supervisor(self, _perm, _full, _mpr, _vis):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from reports.executive_dashboard_api_views import ExecutiveDashboardAreasAPIView

        factory = APIRequestFactory()
        request = factory.patch(
            "/api/reports/executive-dashboard/areas/",
            {"areas": {"compras": False}},
            format="json",
        )
        force_authenticate(request, user=self._user(supervisor=True))
        response = ExecutiveDashboardAreasAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["areas_config"]["compras"])

    @patch(
        "reports.services.report_visibility.command_center_visible_for_user",
        return_value=True,
    )
    @patch(
        "reports.executive_dashboard_api_views.user_has_full_access",
        return_value=False,
    )
    @patch(
        "core.utils.permissions.user_has_permission",
        return_value=True,
    )
    def test_patch_areas_no_supervisor_403(self, _perm, _full, _vis):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from reports.executive_dashboard_api_views import ExecutiveDashboardAreasAPIView

        factory = APIRequestFactory()
        request = factory.patch(
            "/api/reports/executive-dashboard/areas/",
            {"areas": {"compras": False}},
            format="json",
        )
        force_authenticate(request, user=self._user())
        response = ExecutiveDashboardAreasAPIView.as_view()(request)
        self.assertEqual(response.status_code, 403)
