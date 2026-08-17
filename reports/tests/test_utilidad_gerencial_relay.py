# Tests — Informe utilidad gerencial (+ inflación)
# (reports.services.utilidad_gerencial + vistas relay operativo/gerencial).

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from reports.services.utilidad_gerencial import get_utilidad_gerencial
from reports.utilidad_gerencial_relay_views import (
    UtilidadGerencialGerenciaRelayAPIView,
    UtilidadGerencialRelayAPIView,
    parse_filtrar_por,
    parse_punto_venta,
)


_DESC_STD = [("cod",), ("nombre",), ("venta",), ("neto",), ("costo",), ("utilidad",)]
_DESC_INF = _DESC_STD + [("neto2",)]


class TestGetUtilidadGerencialMocked(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor

    def _wire(self, mock_pool, desc, fetch_side_effect):
        self.mock_cursor.description = desc
        self.mock_cursor.fetchall.side_effect = fetch_side_effect
        mock_pool.return_value.get_connection.return_value = self.mock_cm

    @patch("reports.services.utilidad_gerencial.get_mysql_pool")
    def test_cliente_con_nc(self, mock_pool):
        main = [(7, "Cliente X (Cod: 7)", Decimal("130"), Decimal("125"), Decimal("100"), Decimal("25"))]
        nc = [(7, Decimal("-25"))]
        self._wire(mock_pool, _DESC_STD, [main, nc])

        out = get_utilidad_gerencial(
            "emp", fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 1, 31),
            listar_por="cliente",
        )
        fila = out["filas"][0]
        self.assertEqual(fila["desc"], -25.0)
        self.assertEqual(fila["venta_neta"], 100.0)
        self.assertEqual(fila["utilidad"], 0.0)
        self.assertEqual(fila["utilidad_pct"], 1.0)
        self.assertTrue(out["meta"]["nc_aplica"])
        # Total gral con Utilidad % recalculado sobre agregados.
        self.assertEqual(out["totales"]["venta_neta"], 100.0)

    @patch("reports.services.utilidad_gerencial.get_mysql_pool")
    def test_articulo_no_aplica_nc(self, mock_pool):
        main = [(5, "Artículo A", Decimal("200"), Decimal("150"), Decimal("100"), Decimal("50"))]
        self._wire(mock_pool, _DESC_STD, [main])

        out = get_utilidad_gerencial(
            "emp", fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 1, 31),
            listar_por="articulo",
        )
        fila = out["filas"][0]
        self.assertEqual(fila["desc"], 0.0)
        self.assertEqual(fila["venta_neta"], 150.0)
        self.assertEqual(fila["utilidad_pct"], 1.5)
        self.assertFalse(out["meta"]["nc_aplica"])
        # Solo consulta principal (sin NC ni índice).
        self.assertEqual(self.mock_cursor.execute.call_count, 1)

    @patch("reports.services.utilidad_gerencial.get_mysql_pool")
    def test_costo_cero_pct_cero(self, mock_pool):
        main = [(9, "Cliente Z", Decimal("100"), Decimal("100"), Decimal("0"), Decimal("100"))]
        self._wire(mock_pool, _DESC_STD, [main, []])
        out = get_utilidad_gerencial(
            "emp", fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 1, 31),
            listar_por="cliente",
        )
        self.assertEqual(out["filas"][0]["utilidad_pct"], 0.0)

    @patch("reports.services.utilidad_gerencial.get_mysql_pool")
    def test_sql_parametrizado_y_signo(self, mock_pool):
        self._wire(mock_pool, _DESC_STD, [[], []])
        get_utilidad_gerencial(
            "emp", fecha_desde=date(2026, 3, 1), fecha_hasta=date(2026, 3, 31),
            listar_por="cliente",
        )
        sql, params = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("st.TipoComp IN (%s, %s, %s, %s)", sql)
        self.assertIn("st.visualiza_ensamble = 'No'", sql)
        self.assertIn("st.Anulado = 'No'", sql)
        self.assertIn("arti.tipo_art <> 'Gasto'", sql)
        self.assertIn("PrecioCostoxR", sql)
        self.assertIn("st.PrecioVentaxR", sql)
        self.assertIn("Venta", params)
        self.assertIn("Devol - Cliente", params)
        self.assertIn("2026-03-01", params)

    @patch("reports.services.utilidad_gerencial.get_mysql_pool")
    def test_scope_vendedor_forzado(self, mock_pool):
        self._wire(mock_pool, _DESC_STD, [[], []])
        get_utilidad_gerencial(
            "emp", fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 1, 31),
            listar_por="cliente", vendedor_id=3,
        )
        sql, params = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("cc.CodViajante = %s", sql)
        self.assertIn(3, params)

    @patch("reports.services.utilidad_gerencial.get_mysql_pool")
    def test_inflacion(self, mock_pool):
        main = [(7, "Cliente X", Decimal("160"), Decimal("150"), Decimal("100"), Decimal("50"), Decimal("100"))]
        nc1 = [(7, Decimal("0"))]
        nc2 = [(7, Decimal("0"))]
        indice = [(7, Decimal("1.5"))]
        self._wire(mock_pool, _DESC_INF, [main, nc1, nc2, indice])

        out = get_utilidad_gerencial(
            "emp", fecha_desde=date(2026, 2, 1), fecha_hasta=date(2026, 2, 28),
            listar_por="cliente", con_inflacion=True, tipo_inflacion="mensual",
        )
        fila = out["filas"][0]
        self.assertEqual(fila["venta_ant"], 100.0)
        self.assertEqual(fila["indice"], 1.5)
        self.assertEqual(fila["venta_esp"], 150.0)
        self.assertEqual(fila["resultado"], 1.0)
        self.assertEqual(fila["utilidad_pct"], 1.5)
        titulos = [c["title"] for c in out["columns"]]
        self.assertIn("Venta Esp", titulos)
        self.assertIsNotNone(out["meta"]["rango_anterior"])

    def test_fechas_obligatorias(self):
        with self.assertRaises(ValueError):
            get_utilidad_gerencial("e", fecha_desde=None, fecha_hasta=None)

    def test_listar_por_invalido(self):
        with self.assertRaises(ValueError):
            get_utilidad_gerencial(
                "e", fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 1, 31),
                listar_por="inexistente",
            )


class TestParsers(unittest.TestCase):
    def test_parse_filtrar_por(self):
        out = parse_filtrar_por("cliente|7|Ana||vendedor|3|Luis")
        self.assertEqual(out, {"cliente": [7], "vendedor": [3]})

    def test_parse_filtrar_por_ignora_no_numerico_y_todos(self):
        self.assertEqual(parse_filtrar_por("cliente|todos|X"), {})
        self.assertEqual(parse_filtrar_por("cliente|abc|X"), {})
        self.assertEqual(parse_filtrar_por(""), {})

    def test_parse_punto_venta(self):
        self.assertEqual(parse_punto_venta("2|Central|1"), [2])
        self.assertEqual(parse_punto_venta("|Todos|1"), [])
        self.assertEqual(parse_punto_venta(""), [])


def _request_with_session(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestUtilidadGerencialRelayViews(unittest.TestCase):
    def _user_perm(self, perm: str):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        u.tiene_permiso = lambda p, _perm=perm: p == _perm
        return u

    @patch("reports.utilidad_gerencial_relay_views.get_utilidad_gerencial")
    def test_operativo_scope_propio(self, mock_get):
        mock_get.return_value = {"columns": [], "filas": [], "totales": {}, "meta": {}}
        req = _request_with_session(
            "/api/reports/utilidad-gerencial/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31", "filtrarPor": "vendedor|99|X"},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = UtilidadGerencialRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        args, kw = mock_get.call_args
        self.assertEqual(kw["vendedor_id"], 3)
        self.assertEqual(args[0], "emp1")

    def test_operativo_sin_fechas_400(self):
        req = _request_with_session(
            "/api/reports/utilidad-gerencial/relay/", {},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = UtilidadGerencialRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    def test_operativo_sin_vendedor_403(self):
        req = _request_with_session(
            "/api/reports/utilidad-gerencial/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = UtilidadGerencialRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 403)

    @patch("reports.utilidad_gerencial_relay_views.get_utilidad_gerencial")
    def test_gerencia_todos(self, mock_get):
        mock_get.return_value = {"columns": [], "filas": [], "totales": {}, "meta": {}}
        req = _request_with_session(
            "/api/reports/utilidad-gerencial/relay/gerencia/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = UtilidadGerencialGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertIsNone(kw["vendedor_id"])

    @patch("reports.utilidad_gerencial_relay_views.get_utilidad_gerencial")
    def test_gerencia_inflacion_param(self, mock_get):
        mock_get.return_value = {"columns": [], "filas": [], "totales": {}, "meta": {}}
        req = _request_with_session(
            "/api/reports/utilidad-gerencial/relay/gerencia/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31",
             "queInforme": "uti", "tipoInflacion": "anual", "listarPor": "vendedor"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = UtilidadGerencialGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertTrue(kw["con_inflacion"])
        self.assertEqual(kw["tipo_inflacion"], "anual")
        self.assertEqual(kw["listar_por"], "vendedor")

    @patch("reports.utilidad_gerencial_relay_views.listado_seleccion_ventas_netas")
    def test_seleccion(self, mock_sel):
        mock_sel.return_value = {"data": [{"label": "Ana", "value": "7|Ana"}]}
        req = _request_with_session(
            "/api/reports/utilidad-gerencial/relay/gerencia/",
            {"queInforme": "seleccion", "tabla": "vendedor"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = UtilidadGerencialGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["data"][0]["label"], "Ana")
