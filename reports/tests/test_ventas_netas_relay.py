# Tests relay ventas netas (reports.services.ventas_netas + vistas GET).

import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from reports.services.ventas_netas import (
    get_ventas_netas,
    listado_seleccion_ventas_netas,
    parse_filtrar_por,
)
from reports.ventas_netas_relay_views import (
    VentasNetasGerenciaRelayAPIView,
    VentasNetasRelayAPIView,
)


class TestParseFiltrarPor(unittest.TestCase):
    def test_vacio(self):
        self.assertEqual(parse_filtrar_por(None), {})
        self.assertEqual(parse_filtrar_por(""), {})

    def test_cliente_varios(self):
        d = parse_filtrar_por("cliente|10|20||")
        self.assertEqual(d, {"cliente": [10, 20]})


class TestListadoSeleccionVentasNetas(unittest.TestCase):
    @patch("reports.services.ventas_netas.listado_filtros_estadisticas")
    def test_listado_seleccion_reutiliza_filtros_estadisticas(self, mock_listado):
        mock_listado.return_value = [{"label": "C1", "value": "1|C1"}]
        out = listado_seleccion_ventas_netas(
            base_empresa="emp_test",
            tabla="cliente",
            usa_id_manual=False,
            vendedor_a_cargo=[1, "2"],
        )
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["cabeceras"], ["label", "value"])
        mock_listado.assert_called_once()


class TestGetVentasNetasMocked(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_mes_devuelve_filas(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("periodo",),
            ("periodo_etiqueta",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            ("2026-01", "01/2026", Decimal("150.25")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            vendedor_id=7,
            listar_por="mes",
            tipo="monto",
        )
        self.assertEqual(len(out["data"]), 1)
        self.assertEqual(out["data"][0]["ventas_netas"], 150.25)
        self.assertEqual(out["cabeceras"], ["periodo", "periodo_etiqueta", "ventas_netas"])
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args
        self.assertIn("%s", args[0])
        self.assertIn("CodViajante = %s", args[0])
        self.assertIn(7, args[1])

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_tipo_peso_vacio_con_nota(self, mock_pool):
        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            vendedor_id=1,
            tipo="peso",
        )
        self.assertEqual(out["data"], [])
        self.assertIn("nota", out["meta"])
        mock_pool.assert_not_called()

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_vendedor_devuelve_filas(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("cod_vendedor",),
            ("nombre_vendedor",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (2, "Juan Perez", Decimal("99.50")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 2, 1),
            fecha_hasta=date(2026, 2, 28),
            vendedor_id=None,
            listar_por="vendedor",
            tipo="monto",
        )
        self.assertEqual(out["cabeceras"], ["cod_vendedor", "nombre_vendedor", "ventas_netas"])
        self.assertEqual(out["data"][0]["cod_vendedor"], 2)
        self.assertEqual(out["data"][0]["ventas_netas"], 99.5)
        args, _ = self.mock_cursor.execute.call_args
        self.assertIn("LEFT JOIN viajantes", args[0])
        self.assertIn("GROUP BY cc.CodViajante", args[0])

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_rubro_usa_stock_y_rubro(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("codigo_rubro",),
            ("nombre_rubro",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (5, "Rubro X", Decimal("10.00")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 3, 1),
            fecha_hasta=date(2026, 3, 31),
            vendedor_id=1,
            listar_por="rubro",
            tipo="monto",
        )
        self.assertEqual(out["cabeceras"], ["codigo_rubro", "nombre_rubro", "ventas_netas"])
        self.assertIn("nota", out["meta"])
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("FROM stock st", sql)
        self.assertIn("INNER JOIN cuentacliente cc", sql)
        self.assertIn("LEFT JOIN rubro ru", sql)
        self.assertIn("st.PrecioNetoxR", sql)
        self.assertIn("GROUP BY ru.CodigoRubro", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_articulo_usa_stock(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("id_articulo",),
            ("id_manual",),
            ("nombre_articulo",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (100, "ART1", "Producto", Decimal("25.00")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 3, 1),
            fecha_hasta=date(2026, 3, 31),
            vendedor_id=None,
            listar_por="articulo",
            tipo="monto",
        )
        self.assertEqual(
            out["cabeceras"],
            ["id_articulo", "id_manual", "nombre_articulo", "ventas_netas"],
        )
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("FROM stock st", sql)
        self.assertIn("GROUP BY art.IDArt", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_subrubro_usa_stock_y_subrubro(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("id_subrubro",),
            ("nombre_subrubro",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (11, "Sub X", Decimal("18.75")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 4, 1),
            fecha_hasta=date(2026, 4, 30),
            vendedor_id=None,
            listar_por="subrubro",
            tipo="monto",
        )
        self.assertEqual(out["cabeceras"], ["id_subrubro", "nombre_subrubro", "ventas_netas"])
        self.assertEqual(out["data"][0]["id_subrubro"], 11)
        self.assertEqual(out["data"][0]["ventas_netas"], 18.75)
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("FROM stock st", sql)
        self.assertIn("LEFT JOIN subrubro sr", sql)
        self.assertIn("GROUP BY art.IDSubRubro", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_marca_usa_stock_y_marca(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("codigo_marca",),
            ("nombre_marca",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (3, "Marca A", Decimal("45.10")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 5, 1),
            fecha_hasta=date(2026, 5, 31),
            vendedor_id=None,
            listar_por="marca",
            tipo="monto",
        )
        self.assertEqual(out["cabeceras"], ["codigo_marca", "nombre_marca", "ventas_netas"])
        self.assertEqual(out["data"][0]["codigo_marca"], 3)
        self.assertEqual(out["data"][0]["ventas_netas"], 45.1)
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("FROM stock st", sql)
        self.assertIn("LEFT JOIN marca", sql)
        self.assertIn("GROUP BY art.CodigoMarca", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_zona_usa_cliente_y_erp_zona(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("id_zona",),
            ("nombre_zona",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (8, "Centro", Decimal("70.00")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 6, 1),
            fecha_hasta=date(2026, 6, 30),
            vendedor_id=None,
            listar_por="zona",
            tipo="monto",
        )
        self.assertEqual(out["cabeceras"], ["id_zona", "nombre_zona", "ventas_netas"])
        self.assertEqual(out["data"][0]["id_zona"], 8)
        self.assertEqual(out["data"][0]["ventas_netas"], 70.0)
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("FROM stock st", sql)
        self.assertIn("LEFT JOIN cliente cli", sql)
        self.assertIn("LEFT JOIN erp_zona zonas", sql)
        self.assertIn("GROUP BY cli.id_zona", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_tipocliente_usa_tipo_cliente(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("id_tipo_cliente",),
            ("nombre_tipo_cliente",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (2, "Minorista", Decimal("88.40")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 7, 1),
            fecha_hasta=date(2026, 7, 31),
            vendedor_id=None,
            listar_por="tipocliente",
            tipo="monto",
        )
        self.assertEqual(
            out["cabeceras"],
            ["id_tipo_cliente", "nombre_tipo_cliente", "ventas_netas"],
        )
        self.assertEqual(out["data"][0]["id_tipo_cliente"], 2)
        self.assertEqual(out["data"][0]["ventas_netas"], 88.4)
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("LEFT JOIN cliente cli", sql)
        self.assertIn("LEFT JOIN tipo_cliente tpcli", sql)
        self.assertIn("GROUP BY cli.TipoCliente", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_listar_por_proveedor_usa_proveedor(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("codigo_proveedor",),
            ("nombre_proveedor",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (10, "Proveedor SA", Decimal("132.00")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 7, 1),
            fecha_hasta=date(2026, 7, 31),
            vendedor_id=None,
            listar_por="proveedor",
            tipo="monto",
        )
        self.assertEqual(
            out["cabeceras"],
            ["codigo_proveedor", "nombre_proveedor", "ventas_netas"],
        )
        self.assertEqual(out["data"][0]["codigo_proveedor"], 10)
        self.assertEqual(out["data"][0]["ventas_netas"], 132.0)
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("LEFT JOIN proveedor prov", sql)
        self.assertIn("GROUP BY art.CodigoProveedor", sql)
        self.assertIn("art.tipo_art <> 'Gasto'", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_tipo_unidades_en_rubro_usa_cantidad(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("codigo_rubro",),
            ("nombre_rubro",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (4, "Farmacia", Decimal("12.00")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 8, 1),
            fecha_hasta=date(2026, 8, 31),
            vendedor_id=None,
            listar_por="rubro",
            tipo="unidades",
        )
        self.assertEqual(out["data"][0]["ventas_netas"], 12.0)
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("COALESCE(st.Cantidad, 0)", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_tipo_peso_en_articulo_usa_coeficiente_kg(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("id_articulo",),
            ("id_manual",),
            ("nombre_articulo",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (90, "A90", "Prod 90", Decimal("21.50")),
        ]

        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 8, 1),
            fecha_hasta=date(2026, 8, 31),
            vendedor_id=None,
            listar_por="articulo",
            tipo="peso",
        )
        self.assertEqual(out["data"][0]["ventas_netas"], 21.5)
        args, _ = self.mock_cursor.execute.call_args
        sql = args[0]
        self.assertIn("COALESCE(st.Cantidad, 0) * COALESCE(kg.valor, 0)", sql)
        self.assertIn("LEFT JOIN articulo_val_ce kg", sql)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_tipo_unidades_en_mes_devuelve_vacio_con_nota(self, mock_pool):
        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 8, 1),
            fecha_hasta=date(2026, 8, 31),
            vendedor_id=1,
            listar_por="mes",
            tipo="unidades",
        )
        self.assertEqual(out["data"], [])
        self.assertIn("nota", out["meta"])
        mock_pool.assert_not_called()

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_utilidades_en_rubro_usa_precio_costo(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [
            ("codigo_rubro",),
            ("nombre_rubro",),
            ("ventas_netas",),
        ]
        self.mock_cursor.fetchall.return_value = [(1, "R1", Decimal("5.00"))]
        out = get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 9, 1),
            fecha_hasta=date(2026, 9, 30),
            vendedor_id=None,
            listar_por="rubro",
            tipo="monto",
            incluir_utilidades=True,
            tipoInflacion="10",
        )
        self.assertEqual(out["data"][0]["ventas_netas"], 5.0)
        self.assertEqual(out["meta"]["metrica"], "utilidad_neta")
        args, _ = self.mock_cursor.execute.call_args
        self.assertIn("art.PrecioCosto", args[0])


def _request_with_session(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestVentasNetasRelayViews(unittest.TestCase):
    def _user_perm(self, perm: str):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        u.tiene_permiso = lambda p, _perm=perm: p == _perm
        return u

    @patch("reports.ventas_netas_relay_views.get_ventas_netas")
    def test_relay_vendedor_ok(self, mock_gvn):
        mock_gvn.return_value = {
            "data": [],
            "cabeceras": [],
            "titulos": [],
            "meta": {"listar_por": "mes"},
        }
        req = _request_with_session(
            "/api/reports/ventas-netas/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = VentasNetasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_gvn.assert_called_once()
        _, call_kw = mock_gvn.call_args
        self.assertEqual(call_kw["vendedor_id"], 3)
        self.assertEqual(call_kw["base_empresa"], "emp1")

    def test_relay_vendedor_sin_base(self):
        req = _request_with_session(
            "/api/reports/ventas-netas/relay/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31"},
            {"id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = VentasNetasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("reports.ventas_netas_relay_views.get_ventas_netas")
    def test_relay_gerencia_sin_codviajante(self, mock_gvn):
        mock_gvn.return_value = {
            "data": [{"x": 1}],
            "cabeceras": ["x"],
            "titulos": ["X"],
            "meta": {},
        }
        req = _request_with_session(
            "/api/reports/ventas-netas/relay/gerencia/",
            {"fechaDesde": "2026-01-01", "fechaHasta": "2026-01-31", "puntoVenta": "2"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = VentasNetasGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, call_kw = mock_gvn.call_args
        self.assertIsNone(call_kw["vendedor_id"])
        self.assertEqual(call_kw["punto_venta_id"], 2)

    @patch("reports.ventas_netas_relay_views.listado_seleccion_ventas_netas")
    def test_relay_gerencia_seleccion_sin_fechas(self, mock_sel):
        mock_sel.return_value = {
            "data": [{"label": "C1", "value": "1|C1"}],
            "cabeceras": ["label", "value"],
            "titulos": ["Etiqueta", "Valor"],
            "meta": {},
        }
        req = _request_with_session(
            "/api/reports/ventas-netas/relay/gerencia/",
            {"queInforme": "seleccion", "tabla": "cliente"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = VentasNetasGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data["data"]), 1)
        mock_sel.assert_called_once()

    @patch("reports.ventas_netas_relay_views.get_ventas_netas")
    def test_relay_grafico_agrega_gdata(self, mock_gvn):
        mock_gvn.return_value = {
            "data": [{"periodo": "2026-01", "ventas_netas": 10.0}],
            "cabeceras": ["periodo", "ventas_netas"],
            "titulos": ["Período", "Ventas netas"],
            "meta": {},
        }
        req = _request_with_session(
            "/api/reports/ventas-netas/relay/",
            {
                "fechaDesde": "2026-01-01",
                "fechaHasta": "2026-01-31",
                "grafico": "1",
            },
            {"base_empresa": "emp1", "id_vendedor_usr": 3},
        )
        force_authenticate(req, user=self._user_perm("reports.view_operational"))
        resp = VentasNetasRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("gdata", resp.data)
        self.assertEqual(resp.data["gdata"][0], ["label", "value"])

    @patch("reports.ventas_netas_relay_views.get_ventas_netas")
    def test_relay_acepta_listas_sucursales_pv(self, mock_gvn):
        mock_gvn.return_value = {
            "data": [],
            "cabeceras": [],
            "titulos": [],
            "meta": {},
        }
        req = _request_with_session(
            "/api/reports/ventas-netas/relay/gerencia/",
            {
                "fechaDesde": "2026-01-01",
                "fechaHasta": "2026-01-31",
                "sucursales": "2,3",
                "punto_venta": ["10", "11"],
            },
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm("reports.view_managerial"))
        resp = VentasNetasGerenciaRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        _, call_kw = mock_gvn.call_args
        self.assertEqual(call_kw["sucursales"], [2, 3])
        self.assertEqual(call_kw["punto_venta"], [10, 11])


class TestVentasNetasFiltrosSucursalPv(unittest.TestCase):
    """Filtros explícitos sucursales / punto_venta en get_ventas_netas (Oleada 3)."""

    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_get_ventas_netas_sql_sucursales_punto_venta(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [("periodo",), ("periodo_etiqueta",), ("ventas_netas",)]
        self.mock_cursor.fetchall.return_value = []

        get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            vendedor_id=None,
            sucursales=[2],
            punto_venta=[10, 11],
        )
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("cc.CodSucursal IN (%s)", sql)
        self.assertIn("cc.id_pv IN (%s,%s)", sql)
        self.assertNotIn("cc.id_pv = %s", sql)
        self.assertIn(2, params)
        self.assertIn(10, params)
        self.assertIn(11, params)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_relay_compat_escalar_punto_venta_id_to_list(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [("periodo",), ("periodo_etiqueta",), ("ventas_netas",)]
        self.mock_cursor.fetchall.return_value = []

        get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            vendedor_id=None,
            punto_venta_id=2,
            punto_venta=[10, 11],
        )
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertEqual(sql.count("cc.id_pv"), 1)
        self.assertIn("cc.id_pv IN (%s,%s,%s)", sql)
        self.assertNotIn("cc.id_pv = %s", sql)
        self.assertIn(2, params)
        self.assertIn(10, params)
        self.assertIn(11, params)

    @patch("reports.services.ventas_netas.get_mysql_pool")
    def test_punto_venta_id_duplicado_en_lista_sin_repetir_id(self, mock_pool):
        mock_pool.return_value.get_connection.return_value = self.mock_cm
        self.mock_cursor.description = [("periodo",), ("periodo_etiqueta",), ("ventas_netas",)]
        self.mock_cursor.fetchall.return_value = []

        get_ventas_netas(
            base_empresa="emp_test",
            fecha_desde=date(2026, 1, 1),
            fecha_hasta=date(2026, 1, 31),
            vendedor_id=None,
            punto_venta_id=10,
            punto_venta=[10, 11],
        )
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("cc.id_pv IN (%s,%s)", sql)
        self.assertEqual(params.count(10), 1)
        self.assertIn(11, params)
