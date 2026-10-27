# -*- coding: utf-8 -*-
"""Tests filtros UX, APIs predictivas y rango → meses (fabricados_superart)."""
from datetime import date
from unittest.mock import MagicMock, patch

from django.http import QueryDict
from django.test import RequestFactory, SimpleTestCase

from mpr.services_fabricados_superart import (
    buscar_marcas_predictivo,
    buscar_superart_predictivo,
    meses_en_rango,
    parse_filtros_fabricados_superart,
    primer_dia_mes_calendario,
)
from mpr.views import (
    ReportesMarcasBuscarAPIView,
    ReportesMPRView,
    ReportesSuperartBuscarAPIView,
)


def _mock_user_reportes(*permisos: str):
    user = MagicMock(is_authenticated=True)
    user.is_admin.return_value = False
    user.is_superuser = False
    perm_set = set(permisos)

    def tiene_permiso(p):
        return p in perm_set

    user.tiene_permiso.side_effect = tiene_permiso
    user.get_permisos_totales.return_value = perm_set
    return user


class MesesEnRangoTest(SimpleTestCase):
    def test_mes_unico(self):
        self.assertEqual(
            meses_en_rango(date(2026, 10, 1), date(2026, 10, 31)),
            ["2026-10"],
        )

    def test_varios_meses(self):
        self.assertEqual(
            meses_en_rango(date(2026, 8, 15), date(2026, 10, 3)),
            ["2026-08", "2026-09", "2026-10"],
        )

    def test_invierte_si_hasta_antes(self):
        self.assertEqual(
            meses_en_rango(date(2026, 12, 1), date(2026, 1, 31)),
            ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06",
             "2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"],
        )


class ParseFiltrosRangoTest(SimpleTestCase):
    def test_desde_hasta_deriva_meses(self):
        q = QueryDict("desde=2026-10-01&hasta=2026-11-15")
        f = parse_filtros_fabricados_superart(q, hoy=date(2026, 11, 20))
        self.assertEqual(f["desde_iso"], "2026-10-01")
        self.assertEqual(f["hasta_iso"], "2026-11-15")
        self.assertEqual(f["meses"], ["2026-10", "2026-11"])

    def test_sin_fechas_usa_mes_actual(self):
        f = parse_filtros_fabricados_superart(QueryDict(""), hoy=date(2026, 7, 9))
        self.assertEqual(f["desde_iso"], primer_dia_mes_calendario(date(2026, 7, 9)).isoformat())
        self.assertEqual(f["hasta_iso"], "2026-07-09")
        self.assertEqual(f["meses"], ["2026-07"])


class BuscarPredictivoTest(SimpleTestCase):
    @patch("stock.services.inventario_tabla.listar_marcas_catalogo")
    def test_buscar_marcas_filtra_label(self, mock_cat):
        mock_cat.return_value = [
            {"value": 1, "label": "Best Sox"},
            {"value": 2, "label": "Otra"},
        ]
        out = buscar_marcas_predictivo("emp", "best")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["label"], "Best Sox")

    @patch("mpr.services_fabricados_superart.mysql_cursor")
    def test_buscar_superart_sql(self, mock_ctx):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{"codigo": "SA-01"}]
        mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
        out = buscar_superart_predictivo("emp", "SA")
        self.assertEqual(out[0]["codigo"], "SA-01")
        mock_cursor.execute.assert_called_once()


class ReportesPredictivoAPITest(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    @patch("mpr.views._get_base_empresa", return_value="empresa92")
    @patch("mpr.services_fabricados_superart.buscar_marcas_predictivo")
    def test_api_marcas_json(self, mock_buscar, _base):
        mock_buscar.return_value = [{"value": 3, "label": "Marca"}]
        req = self.rf.get("/mpr/reportes/api/marcas/buscar/?q=mar")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("mpr.reportes")
        resp = ReportesMarcasBuscarAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        import json

        data = json.loads(resp.content)
        self.assertEqual(data["marcas"][0]["label"], "Marca")
        mock_buscar.assert_called_once()

    @patch("mpr.views._get_base_empresa", return_value="empresa92")
    @patch("mpr.services_fabricados_superart.buscar_superart_predictivo")
    def test_api_superart_json(self, mock_buscar, _base):
        mock_buscar.return_value = [{"codigo": "X", "descripcion": "X"}]
        req = self.rf.get("/mpr/reportes/api/superart/buscar/?q=x")
        req.session = {"user": {"base_empresa": "empresa92"}}
        req.user = _mock_user_reportes("mpr.reportes")
        resp = ReportesSuperartBuscarAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        import json

        data = json.loads(resp.content)
        self.assertEqual(data["superarts"][0]["codigo"], "X")


class ReportesFabricadosSuperartViewTest(SimpleTestCase):
    def _context(self, get_params):
        view = ReportesMPRView()
        view.request = MagicMock()
        view.request.session = {"user": {"base_empresa": "empresa92"}}
        view.request.GET = get_params
        payload = {
            "meses": ["2026-10"],
            "mes_labels": {},
            "filas_superart": [],
            "totales_por_mes": {},
            "total_general": 0.0,
            "kpis": {},
        }
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch(
                "stock.services.inventario_tabla.listar_marcas_catalogo",
                return_value=[],
            ):
                with patch(
                    "mpr.services_fabricados_superart.reporte_mpr_fabricados_superart",
                    return_value=payload,
                ):
                    return view.get_context_data()

    def test_vista_fabricados_con_rango(self):
        ctx = self._context(
            QueryDict("grupo=produccion&reporte=fabricados_superart&desde=2026-10-01&hasta=2026-10-31")
        )
        self.assertEqual(ctx["reporte"], "fabricados_superart")
        self.assertTrue(ctx["ignora_periodo_shell"])
        fab = ctx["filtros_fabricados_superart"]
        self.assertEqual(fab["meses"], ["2026-10"])
        self.assertEqual(ctx["fecha_desde_iso"], "2026-10-01")
