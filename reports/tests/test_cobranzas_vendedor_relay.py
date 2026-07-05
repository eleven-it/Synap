# Tests — Informe cobranzas por vendedor
# (reports.services.cobranzas_vendedor + vistas relay operativo/gerencial).

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from reports.services.cobranzas_vendedor import (
    MODO_MES,
    MODO_TOTALIZADO,
    get_cobranzas_vendedor,
)
from reports.cobranzas_vendedor_relay_views import (
    CobranzasVendedorGerenciaRelayAPIView,
    CobranzasVendedorRelayAPIView,
)


class TestGetCobranzasVendedorMocked(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor

    def _desc_mes(self):
        return [
            ("aaaa",), ("m",), ("totalEfectivo",), ("totalDolar",),
            ("totalCheque",), ("totalTransferencia",), ("totalPercep",), ("total",),
        ]

    def _desc_totalizado(self):
        return [
            ("totalEfectivo",), ("totalDolar",), ("totalCheque",),
            ("totalTransferencia",), ("totalPercep",), ("total",),
        ]

    def _wire(self, mock_pool, rows, desc):
        self.mock_cursor.description = desc
        self.mock_cursor.fetchall.return_value = rows
        mock_pool.return_value.get_connection.return_value = self.mock_cm

    @patch("reports.services.cobranzas_vendedor.get_mysql_pool")
    def test_modo_mes_formato_y_totales(self, mock_pool):
        rows = [
            (2026, 1, Decimal("150.00"), Decimal("0"), Decimal("10.00"), Decimal("20.00"), Decimal("5.00"), Decimal("200.00")),
            (2026, 2, Decimal("100.00"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("250.00")),
        ]
        self._wire(mock_pool, rows, self._desc_mes())

        out = get_cobranzas_vendedor(
            "emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 2, 28),
            modo="mes",
        )

        self.assertEqual(out["modo"], MODO_MES)
        self.assertEqual(len(out["filas"]), 2)
        self.assertEqual(out["filas"][0]["periodo"], "Enero 2026")
        self.assertEqual(out["filas"][1]["periodo"], "Febrero 2026")
        self.assertEqual(out["filas"][0]["efectivo"], 150.0)
        # Pie = suma de columnas.
        self.assertEqual(out["totales"]["total"], 450.0)
        self.assertEqual(out["totales"]["efectivo"], 250.0)
        self.assertEqual(out["totales"]["periodo"], "Total Gral")
        self.assertEqual([c["data"] for c in out["columns"]][0], "periodo")

    @patch("reports.services.cobranzas_vendedor.get_mysql_pool")
    def test_sql_parametrizado_y_comprobantes(self, mock_pool):
        self._wire(mock_pool, [], self._desc_mes())
        get_cobranzas_vendedor(
            "emp_test",
            fecha_desde=date(2026, 3, 1),
            fecha_hasta=date(2026, 3, 31),
        )
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("cuentacliente.TipoComprobante IN (%s, %s, %s, %s, %s, %s)", sql)
        self.assertIn("cuentacliente.Fecha BETWEEN %s AND %s", sql)
        self.assertIn("cuentacliente.Anulado = 'No'", sql)
        self.assertIn("CondVenta = 'Contado'", sql)
        # Los 6 tipos + fecha desde/hasta como parámetros vinculados.
        self.assertEqual(params[:6], ["REC", "FA", "FB", "FM", "FE", "FC"])
        self.assertEqual(params[6], "2026-03-01")
        self.assertEqual(params[7], "2026-03-31")

    @patch("reports.services.cobranzas_vendedor.get_mysql_pool")
    def test_restringe_por_cod_viajantes(self, mock_pool):
        self._wire(mock_pool, [], self._desc_mes())
        get_cobranzas_vendedor(
            "emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            cod_viajantes=[7],
        )
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("cuentacliente.CodViajante IN (%s)", sql)
        self.assertIn(7, params)

    @patch("reports.services.cobranzas_vendedor.get_mysql_pool")
    def test_modo_totalizado_una_fila(self, mock_pool):
        rows = [(Decimal("500.00"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("500.00"))]
        self._wire(mock_pool, rows, self._desc_totalizado())
        out = get_cobranzas_vendedor(
            "emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 3, 31),
            modo="totalizado",
        )
        self.assertEqual(out["modo"], MODO_TOTALIZADO)
        self.assertEqual(len(out["filas"]), 1)
        self.assertEqual(out["filas"][0]["periodo"], "01/01/2026 al 31/03/2026")
        self.assertEqual(out["filas"][0]["total"], 500.0)
        # SQL totalizado no agrupa por mes.
        sql = self.mock_cursor.execute.call_args[0][0]
        self.assertNotIn("GROUP BY", sql)

    @patch("reports.services.cobranzas_vendedor.get_mysql_pool")
    def test_totalizado_sin_datos_descarta_fila_nula(self, mock_pool):
        rows = [(None, None, None, None, None, None)]
        self._wire(mock_pool, rows, self._desc_totalizado())
        out = get_cobranzas_vendedor(
            "emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 3, 31),
            modo="totalizado",
        )
        self.assertEqual(out["filas"], [])
        self.assertEqual(out["totales"]["total"], 0.0)

    def test_fechas_obligatorias(self):
        with self.assertRaises(ValueError):
            get_cobranzas_vendedor("e", fecha_desde=None, fecha_hasta=None)


def _request_with_session(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestCobranzasVendedorRelayViews(unittest.TestCase):
    def _user_perm(self, perm: str):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        u.tiene_permiso = lambda p, _perm=perm: p == _perm
        return u

    @patch("reports.cobranzas_vendedor_relay_views.get_cobranzas_vendedor")
    def test_operativo_scope_propio(self, mock_get):
        mock_get.return_value = {"columns": [], "filas": [], "totales": {}, "modo": "mes"}
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = CobranzasVendedorRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        args, kw = mock_get.call_args
        self.assertEqual(kw["cod_viajantes"], [3])
        self.assertEqual(args[0], "emp1")

    @patch("reports.cobranzas_vendedor_relay_views.get_cobranzas_vendedor")
    def test_operativo_anti_bypass_codviajante_ajeno(self, mock_get):
        mock_get.return_value = {"columns": [], "filas": [], "totales": {}, "modo": "mes"}
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31", "codViajante": "99"},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = CobranzasVendedorRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertEqual(kw["cod_viajantes"], [3])

    def test_operativo_sin_base(self):
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = CobranzasVendedorRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    def test_operativo_sin_fechas(self):
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/",
            {},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = CobranzasVendedorRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    def test_operativo_sin_codviajante_403(self):
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = CobranzasVendedorRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 403)

    @patch("reports.cobranzas_vendedor_relay_views.get_cobranzas_vendedor")
    def test_gerencia_sin_filtro_todos(self, mock_get):
        mock_get.return_value = {"columns": [], "filas": [], "totales": {}, "modo": "mes"}
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/gerencia/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = CobranzasVendedorGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertIsNone(kw["cod_viajantes"])

    @patch("reports.cobranzas_vendedor_relay_views.get_cobranzas_vendedor")
    def test_gerencia_filtra_por_codviajante(self, mock_get):
        mock_get.return_value = {"columns": [], "filas": [], "totales": {}, "modo": "mes"}
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/gerencia/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31", "codViajante": "10"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = CobranzasVendedorGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertEqual(kw["cod_viajantes"], [10])

    @patch("reports.cobranzas_vendedor_relay_views.listado_vendedores_seleccion")
    def test_seleccion_devuelve_lista(self, mock_sel):
        mock_sel.return_value = [{"label": "Ana", "value": "7|Ana"}]
        req = _request_with_session(
            "/api/reports/cobranzas-vendedor/relay/gerencia/",
            {"queInforme": "seleccion"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = CobranzasVendedorGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [{"label": "Ana", "value": "7|Ana"}])
