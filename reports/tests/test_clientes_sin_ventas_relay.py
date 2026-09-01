# Tests — Informe clientes sin ventas por vendedor
# (reports.services.clientes_sin_ventas + vistas relay operativo/gerencial).

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from reports.services.clientes_sin_ventas import (
    _cc_periodo_scope_on_clause,
    get_clientes_sin_ventas,
    listado_vendedores_seleccion,
    parse_filtrar_por,
)
from reports.clientes_sin_ventas_relay_views import (
    ClientesSinVentasGerenciaRelayAPIView,
    ClientesSinVentasRelayAPIView,
    _parse_int_list_qs,
)


class TestParseFiltrarPor(unittest.TestCase):
    def test_vacio(self):
        self.assertEqual(parse_filtrar_por(None), [])
        self.assertEqual(parse_filtrar_por(""), [])

    def test_vendedores_validos(self):
        self.assertEqual(
            parse_filtrar_por("vendedor|10|Ana|0||vendedor|11|Beto|1"),
            [10, 11],
        )

    def test_descarta_no_numerico_e_inyeccion(self):
        # 'todos' y valores no numéricos (incluida inyección textual) se descartan.
        self.assertEqual(parse_filtrar_por("vendedor|todos|x|0"), [])
        self.assertEqual(parse_filtrar_por("vendedor|DROP TABLE|x|0"), [])

    def test_unicos_preserva_orden(self):
        self.assertEqual(parse_filtrar_por("vendedor|5|a|0||vendedor|5|a|1||vendedor|3|b|2"), [5, 3])


class TestGetClientesSinVentasMocked(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_cursor.description = [
            ("CodViajante",),
            ("NombreViajante",),
            ("Codigo",),
            ("IdManual",),
            ("Nombre_cliente",),
            ("CodigoDisplay",),
            ("UltimaCompra",),
        ]

    def _wire(self, mock_pool, main_rows, resumen_rows):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.fetchall.side_effect = [main_rows, resumen_rows]

    @patch("reports.services.clientes_sin_ventas.get_mysql_pool")
    def test_formato_filas_y_resumen(self, mock_pool):
        main_rows = [
            (7, "Ana", 100, "M100", "Cliente Uno", "M100", date(2025, 11, 19)),
            (7, "Ana", 101, None, "Cliente Dos", 101, None),
        ]
        resumen_rows = [
            (7, "Ana", 10, 4, 6),
            (8, "Beto", 5, 5, 0),
        ]
        self._wire(mock_pool, main_rows, resumen_rows)

        out = get_clientes_sin_ventas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
        )

        self.assertEqual(len(out["datos"]), 2)
        self.assertEqual(out["datos"][0]["UltimaCompra"], "19/11/2025")
        self.assertEqual(out["datos"][1]["UltimaCompra"], "-")
        self.assertEqual(out["datos"][1]["UltimaCompraOrden"], "9999-12-31")
        self.assertEqual(out["datos"][0]["VendedorLabel"], "Ana (Cod: 7)")
        self.assertEqual(
            out["resumenGlobal"], {"total": 15, "activos": 6, "noActivos": 9}
        )
        self.assertTrue(out["modoTodosVendedores"])
        self.assertEqual([c["data"] for c in out["columns"]],
                         ["CodigoDisplay", "Nombre_cliente", "UltimaCompra", "VendedorLabel"])

    @patch("reports.services.clientes_sin_ventas.get_mysql_pool")
    def test_sql_parametrizado_fechas(self, mock_pool):
        self._wire(mock_pool, [], [])
        get_clientes_sin_ventas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 3, 1),
            fecha_hasta=date(2026, 3, 31),
        )
        first_sql, first_params = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("cliente.Estado = 'Activo'", first_sql)
        self.assertIn("cc_periodo.Fecha BETWEEN %s AND %s", first_sql)
        self.assertIn("cc_periodo.Codigo IS NULL", first_sql)
        self.assertEqual(first_params[0], "2026-03-01")
        self.assertEqual(first_params[1], "2026-03-31")

    @patch("reports.services.clientes_sin_ventas.get_mysql_pool")
    def test_filtros_en_on_clause_anti_join(self, mock_pool):
        self._wire(mock_pool, [], [])
        get_clientes_sin_ventas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 3, 1),
            fecha_hasta=date(2026, 3, 31),
            sucursales=[2],
            puntos_venta=[10, 11],
        )
        main_sql, main_params = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("cc_periodo.CodSucursal IN (%s)", main_sql)
        self.assertIn("cc_periodo.id_pv IN (%s, %s)", main_sql)
        self.assertIn("cc2.CodSucursal IN (%s)", main_sql)
        self.assertIn("cc2.id_pv IN (%s, %s)", main_sql)
        self.assertNotIn("WHERE cc_periodo.CodSucursal", main_sql)
        self.assertIn(2, main_params)
        self.assertIn(10, main_params)
        self.assertIn(11, main_params)
        resumen_sql = self.mock_cursor.execute.call_args_list[1][0][0]
        self.assertIn("cc_periodo.CodSucursal IN (%s)", resumen_sql)

    @patch("reports.services.clientes_sin_ventas.get_mysql_pool")
    def test_cliente_venta_otra_sucursal_sin_ventas_en_filtrada(self, mock_pool):
        """Cliente con venta en sucursal 99 no matchea ON de sucursal 2 → anti-join lo incluye."""
        self._wire(mock_pool, [(7, "Ana", 100, "M100", "Cliente Sur", "M100", None)], [])
        out = get_clientes_sin_ventas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            sucursales=[2],
        )
        self.assertEqual(len(out["datos"]), 1)
        self.assertEqual(out["datos"][0]["Nombre_cliente"], "Cliente Sur")
        main_sql = self.mock_cursor.execute.call_args_list[0][0][0]
        on_clause, _ = _cc_periodo_scope_on_clause(sucursales=[2])
        self.assertIn(on_clause.strip(), main_sql.replace("\n", " "))

    @patch("reports.services.clientes_sin_ventas.get_mysql_pool")
    def test_restringe_por_cod_viajantes(self, mock_pool):
        self._wire(mock_pool, [], [])
        get_clientes_sin_ventas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            cod_viajantes=[7],
        )
        first_sql, first_params = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("cliente.CodViajante IN (%s)", first_sql)
        self.assertIn(7, first_params)

    @patch("reports.services.clientes_sin_ventas.get_mysql_pool")
    def test_incluir_domicilio_anexa_al_nombre(self, mock_pool):
        # Con domicilio, la columna extra 'DomicilioSimple' precede a UltimaCompra.
        self.mock_cursor.description = [
            ("CodViajante",),
            ("NombreViajante",),
            ("Codigo",),
            ("IdManual",),
            ("Nombre_cliente",),
            ("CodigoDisplay",),
            ("DomicilioSimple",),
            ("UltimaCompra",),
        ]
        main_rows = [(7, "Ana", 100, "M100", "Cliente Uno", "M100", "Av Siempreviva 742", None)]
        self._wire(mock_pool, main_rows, [])
        out = get_clientes_sin_ventas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            incluir_domicilio=True,
        )
        self.assertEqual(out["datos"][0]["Nombre_cliente"], "Cliente Uno | Av Siempreviva 742")
        first_sql = self.mock_cursor.execute.call_args_list[0][0][0]
        self.assertIn("DomicilioSimple", first_sql)

    def test_fechas_obligatorias(self):
        with self.assertRaises(ValueError):
            get_clientes_sin_ventas(base_empresa="e", fecha_desde=None, fecha_hasta=None)


class TestListadoVendedoresSeleccion(unittest.TestCase):
    @patch("reports.services.clientes_sin_ventas.get_mysql_pool")
    def test_seleccion_restringida(self, mock_pool):
        cm = MagicMock()
        conn = MagicMock()
        cursor = MagicMock()
        cm.__enter__.return_value = conn
        cm.__exit__.return_value = False
        conn.cursor.return_value = cursor
        cursor.fetchall.return_value = [(7, "Ana (cod:7)")]
        mock_pool.return_value.get_connection.return_value = cm

        out = listado_vendedores_seleccion("emp_test", cod_viajantes=[7])
        self.assertEqual(out, [{"label": "Ana (cod:7)", "value": "7|Ana (cod:7)"}])
        sql = cursor.execute.call_args[0][0]
        self.assertIn("viajantes.Anulado = 'No'", sql)
        self.assertIn("viajantes.CodViajante IN (%s)", sql)


def _request_with_session(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestClientesSinVentasRelayViews(unittest.TestCase):
    def _user_perm(self, perm: str):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        u.tiene_permiso = lambda p, _perm=perm: p == _perm
        return u

    @patch("reports.clientes_sin_ventas_relay_views.get_clientes_sin_ventas")
    def test_operativo_scope_propio(self, mock_get):
        mock_get.return_value = {"columns": [], "datos": [], "resumenVendedores": [], "resumenGlobal": {}, "modoTodosVendedores": False}
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = ClientesSinVentasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        args, kw = mock_get.call_args
        self.assertEqual(kw["cod_viajantes"], [3])
        self.assertEqual(args[0], "emp1")

    @patch("reports.clientes_sin_ventas_relay_views.get_clientes_sin_ventas")
    def test_operativo_anti_bypass_filtro_ajeno(self, mock_get):
        mock_get.return_value = {"columns": [], "datos": [], "resumenVendedores": [], "resumenGlobal": {}, "modoTodosVendedores": False}
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31", "filtrarPor": "vendedor|99|X|0"},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = ClientesSinVentasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        # No puede ver al vendedor 99: cae a su propio alcance [3].
        self.assertEqual(kw["cod_viajantes"], [3])

    def test_operativo_sin_base(self):
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = ClientesSinVentasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    def test_operativo_sin_fechas(self):
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/",
            {},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = ClientesSinVentasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    def test_operativo_sin_codviajante_403(self):
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = ClientesSinVentasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 403)

    @patch("reports.clientes_sin_ventas_relay_views.get_clientes_sin_ventas")
    def test_gerencia_sin_filtro_todos(self, mock_get):
        mock_get.return_value = {"columns": [], "datos": [], "resumenVendedores": [], "resumenGlobal": {}, "modoTodosVendedores": False}
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/gerencia/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = ClientesSinVentasGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertIsNone(kw["cod_viajantes"])

    @patch("reports.clientes_sin_ventas_relay_views.get_clientes_sin_ventas")
    def test_gerencia_respeta_filtro(self, mock_get):
        mock_get.return_value = {"columns": [], "datos": [], "resumenVendedores": [], "resumenGlobal": {}, "modoTodosVendedores": False}
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/gerencia/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31", "filtrarPor": "vendedor|10|A|0||vendedor|11|B|1"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = ClientesSinVentasGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertEqual(kw["cod_viajantes"], [10, 11])

    @patch("reports.clientes_sin_ventas_relay_views.listado_vendedores_seleccion")
    def test_seleccion_devuelve_lista(self, mock_sel):
        mock_sel.return_value = [{"label": "Ana", "value": "7|Ana"}]
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/gerencia/",
            {"queInforme": "seleccion"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = ClientesSinVentasGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, [{"label": "Ana", "value": "7|Ana"}])


class TestClientesSinVentasRelayScopeFilters(unittest.TestCase):
    def test_relay_clientes_sin_ventas_query_params_normalization(self):
        factory = RequestFactory()
        req = factory.get(
            "/api/reports/clientes-sin-ventas/relay/gerencia/",
            {"sucursales": "2,3", "puntoVenta": ["10", "11"]},
        )
        self.assertEqual(_parse_int_list_qs(req, "sucursales"), [2, 3])
        self.assertEqual(_parse_int_list_qs(req, "puntoVenta", "punto_venta"), [10, 11])

    @patch("reports.clientes_sin_ventas_relay_views.get_clientes_sin_ventas")
    def test_gerencia_pasa_sucursales_pv_al_servicio(self, mock_get):
        mock_get.return_value = {
            "columns": [],
            "datos": [],
            "resumenVendedores": [],
            "resumenGlobal": {},
            "modoTodosVendedores": False,
        }
        req = _request_with_session(
            "/api/reports/clientes-sin-ventas/relay/gerencia/",
            {
                "fechaDesde": "2026-01-01",
                "fechaHasta": "2026-01-31",
                "sucursales": "2",
                "puntoVenta": "10",
            },
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=MagicMock(is_authenticated=True, is_superuser=False, tiene_permiso=lambda p: p == "reports.view_managerial"))
        resp = ClientesSinVentasGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, kw = mock_get.call_args
        self.assertEqual(kw["sucursales"], [2])
        self.assertEqual(kw["puntos_venta"], [10])


class TestClientesSinVentasTemplateFilters(unittest.TestCase):
    def test_template_clientes_sin_ventas_tags_sucursal_pv(self):
        from django.template.loader import render_to_string

        html_pv = render_to_string(
            "reports/includes/filters_sucursal_punto_venta.html",
            {"ocultar_clientes_excluidos": True},
        )
        self.assertIn('id="sucursales"', html_pv)
        self.assertIn('id="punto_venta"', html_pv)
        self.assertNotIn('id="clientes_excluidos"', html_pv)

        tpl_path = (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "reports"
            / "dashboard_clientes_sin_ventas_vendedor.html"
        )
        tpl = tpl_path.read_text(encoding="utf-8")
        self.assertIn("filters_sucursal_punto_venta.html", tpl)
        self.assertIn('params.append("sucursales"', tpl)
        self.assertIn('params.append("puntoVenta"', tpl)
        self.assertIn("csv-alcance-sucursal-pv", tpl)
        self.assertIn("formatSucursalPvScopeText", tpl)
