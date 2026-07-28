# Tests — Informe DABRA consolidado remitos
# (helpers, servicio mock cursor, relay y exporter).

from __future__ import annotations

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from rest_framework.test import force_authenticate

from reports.dabra_consolidado_remitos_relay_views import (
    DabraConsolidadoRemitosExportAPIView,
    DabraConsolidadoRemitosRelayAPIView,
)
from reports.services.dabra_consolidado_remitos import (
    CODIGO_CLIENTE_DABRA,
    _sql_remitos_por_fa,
    bonificacion_linea,
    calcular_tolerancia,
    format_comprobante_string,
    format_punto_venta,
    get_dabra_consolidado_remitos,
    letra_por_tipo,
    normalizar_cuit,
    parse_cod_art_prov,
    parse_nro_comprobante,
    resolver_categoria,
    validar_totales_fa,
)
from reports.services.dabra_consolidado_remitos_export import (
    REPORTE_HEADERS,
    TOTAL_FACTURAS_HEADERS,
    exportar_dabra_xlsx,
    inspeccionar_workbook,
)


class TestParseNroComprobante(unittest.TestCase):
    def test_pv_pad5_y_legal(self):
        pv, legal = parse_nro_comprobante("0008-00000004")
        self.assertEqual(pv, 8)
        self.assertEqual(legal, 4)
        self.assertEqual(format_punto_venta(pv), "00008")

    def test_string_total_pv4_legal8(self):
        self.assertEqual(
            format_comprobante_string("FA", 8, 4),
            "A000800000004",
        )


class TestSqlRemitosPorFa(unittest.TestCase):
    """Paridad con trz_trazabilidad.frm: cabecera REM en comp_ped."""

    def test_join_comp_ped_no_cuentacliente(self):
        sql = _sql_remitos_por_fa(2)
        self.assertIn("FROM rem_fact rf", sql)
        self.assertIn("INNER JOIN comp_ped rem", sql)
        self.assertIn("rem.TipoComprobante = 'REM'", sql)
        self.assertNotIn("JOIN cuentacliente rem", sql)
        self.assertEqual(
            format_comprobante_string("FA", 4, 20777),
            "A000400020777",
        )


class TestCompRefRemito(unittest.TestCase):
    def test_letra_rem_r(self):
        self.assertEqual(letra_por_tipo("REM"), "R")

    def test_comp_ref_pad5_numero_ref(self):
        pv, legal = parse_nro_comprobante("0001-00027655")
        self.assertEqual(format_punto_venta(pv), "00001")
        self.assertEqual(legal, 27655)
        self.assertEqual(
            format_comprobante_string("REM", pv, legal),
            "R000100027655",
        )


class TestBonificacion(unittest.TestCase):
    def test_pordesc_bonif_prioritario(self):
        self.assertEqual(bonificacion_linea(15, 20), Decimal("15"))

    def test_fallback_por_desc(self):
        self.assertEqual(bonificacion_linea(0, 20), Decimal("20"))
        self.assertEqual(bonificacion_linea(None, 10), Decimal("10"))

    def test_ambos_cero(self):
        self.assertEqual(bonificacion_linea(0, 0), Decimal("0"))


class TestCodArtProvYCategoria(unittest.TestCase):
    def test_primeros_9_y_talle(self):
        self.assertEqual(parse_cod_art_prov("950058-01 T110"), ("950058-01", "T110"))

    def test_split_ultimo_espacio(self):
        self.assertEqual(parse_cod_art_prov("888869-10 XL"), ("888869-10", "XL"))

    def test_categoria_default(self):
        self.assertEqual(resolver_categoria(None), "ACCESORIOS")
        self.assertEqual(resolver_categoria("Rubro 1"), "ACCESORIOS")
        self.assertEqual(resolver_categoria("Calzado"), "CALZADO")


class TestToleranciaSigma(unittest.TestCase):
    def test_tolerancia_formula(self):
        self.assertEqual(calcular_tolerancia(1), Decimal("0.05"))
        self.assertEqual(calcular_tolerancia(10), Decimal("0.10"))

    def test_mismatch_genera_errores(self):
        lineas = [
            {
                "codigo_movimiento": 1200,
                "cantidad": Decimal("1"),
                "precio_netox_u": Decimal("100"),
                "precio_ivax_u": Decimal("21"),
            }
        ]
        errs = validar_totales_fa(lineas, Decimal("200"), Decimal("200"))
        self.assertTrue(errs)
        self.assertEqual(len(errs), 2)

    def test_dentro_tolerancia_ok(self):
        lineas = [
            {
                "codigo_movimiento": 1200,
                "cantidad": Decimal("31"),
                "precio_netox_u": Decimal("1"),
                "precio_ivax_u": Decimal("0.21"),
            }
        ]
        errs = validar_totales_fa(lineas, Decimal("31"), Decimal("37.53"))
        self.assertEqual(errs, [])


class TestGetDabraConsolidadoRemitosMocked(unittest.TestCase):
    def setUp(self):
        self.mock_cm = MagicMock()
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_cm.__enter__.return_value = self.mock_conn
        self.mock_cm.__exit__.return_value = False
        self.mock_conn.cursor.return_value = self.mock_cursor

    @patch("reports.services.dabra_consolidado_remitos.get_mysql_pool")
    def test_sql_filtros_dabra(self, mock_pool):
        desc_lineas = [
            ("codigo_movimiento_fa",),
            ("fa_nro_comprobante",),
            ("fa_tipo",),
            ("fa_fecha",),
            ("fe_cae",),
            ("fe_vto_cae",),
            ("SubTotal1",),
            ("ImporteVenta",),
            ("id_stock",),
            ("Cantidad",),
            ("PrecioVentaxU",),
            ("PrecioNetoxU",),
            ("PrecioIVAxU",),
            ("pordesc_bonif",),
            ("PorDesc",),
            ("imp_alicuota_iva",),
            ("NombreArticulo",),
            ("CodArtProv",),
            ("categoria_nombre",),
        ]

        def execute_side_effect(sql, params):
            if "FROM cuentacliente cc" in sql and "INNER JOIN stock" in sql:
                self.mock_cursor.description = desc_lineas
                self.mock_cursor.fetchall.return_value = []
            elif "FROM datosempresa" in sql:
                self.mock_cursor.description = [("CUIT",)]
                self.mock_cursor.fetchall.return_value = [("30-69074961-7",)]

        self.mock_cursor.execute.side_effect = execute_side_effect
        mock_pool.return_value.get_connection.return_value = self.mock_cm

        get_dabra_consolidado_remitos("emp_test", mes=7, anio=2026)

        sql_main, params_main = self.mock_cursor.execute.call_args_list[0][0]
        self.assertIn("cc.Codigo = %s", sql_main)
        self.assertIn("cc.TipoComprobante = 'FA'", sql_main)
        self.assertIn("cc.Anulado = 'No'", sql_main)
        self.assertIn("cc.Fecha BETWEEN %s AND %s", sql_main)
        self.assertEqual(params_main[0], CODIGO_CLIENTE_DABRA)
        self.assertEqual(params_main[1], "2026-07-01")
        self.assertEqual(params_main[2], "2026-07-31")

    @patch("reports.services.dabra_consolidado_remitos.get_mysql_pool")
    def test_expansion_multi_remito(self, mock_pool):
        desc_lineas = [
            ("codigo_movimiento_fa",),
            ("fa_nro_comprobante",),
            ("fa_tipo",),
            ("fa_fecha",),
            ("fe_cae",),
            ("fe_vto_cae",),
            ("SubTotal1",),
            ("ImporteVenta",),
            ("id_stock",),
            ("Cantidad",),
            ("PrecioVentaxU",),
            ("PrecioNetoxU",),
            ("PrecioIVAxU",),
            ("pordesc_bonif",),
            ("PorDesc",),
            ("imp_alicuota_iva",),
            ("NombreArticulo",),
            ("CodArtProv",),
            ("categoria_nombre",),
        ]
        desc_rem = [
            ("CodigoMovimientoF",),
            ("CodigoMovimientoR",),
            ("rem_nro",),
            ("rem_tipo",),
            ("rem_fecha",),
            ("NroCalle",),
        ]

        linea_row = (
            1200,
            "0008-00000004",
            "FA",
            "2026-07-24",
            "86184381365307",
            "2026-08-01",
            Decimal("100"),
            Decimal("121"),
            1,
            Decimal("2"),
            Decimal("50"),
            Decimal("50"),
            Decimal("10.5"),
            Decimal("0"),
            Decimal("0"),
            Decimal("21"),
            "Art test",
            "950058-01 T110",
            None,
        )

        def execute_side_effect(sql, params):
            if "INNER JOIN stock" in sql:
                self.mock_cursor.description = desc_lineas
                self.mock_cursor.fetchall.return_value = [linea_row]
            elif "FROM rem_fact" in sql:
                self.mock_cursor.description = desc_rem
                self.mock_cursor.fetchall.return_value = [
                    (1200, 1205, "0001-00027655", "REM", "2026-07-20", "178"),
                    (1200, 1206, "0001-00027656", "REM", "2026-07-21", "179"),
                ]
            elif "datosempresa" in sql:
                self.mock_cursor.description = [("CUIT",)]
                self.mock_cursor.fetchall.return_value = [("30-69074961-7",)]
            elif "cliente_domicilio" in sql:
                self.mock_cursor.description = [("CodigoMovimiento",), ("NroCalle",)]
                self.mock_cursor.fetchall.return_value = [(1200, "100")]

        self.mock_cursor.execute.side_effect = execute_side_effect
        mock_pool.return_value.get_connection.return_value = self.mock_cm

        out = get_dabra_consolidado_remitos("emp_test", mes=7, anio=2026)
        self.assertEqual(len(out["filas"]), 2)
        refs = {(f["comp_ref"], f["numero_ref"]) for f in out["filas"]}
        self.assertIn(("00001", 27655), refs)
        self.assertIn(("00001", 27656), refs)
        self.assertTrue(any("2 remitos" in a for a in out["alarmas"]))

    @patch("reports.services.dabra_consolidado_remitos.get_mysql_pool")
    def test_sin_remitos_refs_vacias_alarma(self, mock_pool):
        desc_lineas = [
            ("codigo_movimiento_fa",),
            ("fa_nro_comprobante",),
            ("fa_tipo",),
            ("fa_fecha",),
            ("fe_cae",),
            ("fe_vto_cae",),
            ("SubTotal1",),
            ("ImporteVenta",),
            ("id_stock",),
            ("Cantidad",),
            ("PrecioVentaxU",),
            ("PrecioNetoxU",),
            ("PrecioIVAxU",),
            ("pordesc_bonif",),
            ("PorDesc",),
            ("imp_alicuota_iva",),
            ("NombreArticulo",),
            ("CodArtProv",),
            ("categoria_nombre",),
        ]
        linea_row = (
            1200,
            "0008-00000004",
            "FA",
            "2026-07-24",
            "86184381365307",
            "2026-08-01",
            Decimal("100"),
            Decimal("121"),
            1,
            Decimal("1"),
            Decimal("100"),
            Decimal("100"),
            Decimal("21"),
            Decimal("0"),
            Decimal("0"),
            Decimal("21"),
            "Art",
            "950058-01 T110",
            None,
        )

        def execute_side_effect(sql, params):
            if "INNER JOIN stock" in sql:
                self.mock_cursor.description = desc_lineas
                self.mock_cursor.fetchall.return_value = [linea_row]
            elif "FROM rem_fact" in sql:
                self.mock_cursor.description = []
                self.mock_cursor.fetchall.return_value = []
            elif "datosempresa" in sql:
                self.mock_cursor.description = [("CUIT",)]
                self.mock_cursor.fetchall.return_value = [("30-69074961-7",)]
            else:
                self.mock_cursor.description = [("CodigoMovimiento",), ("NroCalle",)]
                self.mock_cursor.fetchall.return_value = []

        self.mock_cursor.execute.side_effect = execute_side_effect
        mock_pool.return_value.get_connection.return_value = self.mock_cm

        out = get_dabra_consolidado_remitos("emp_test", mes=7, anio=2026)
        self.assertEqual(len(out["filas"]), 1)
        self.assertEqual(out["filas"][0]["comp_ref"], "")
        self.assertEqual(out["filas"][0]["numero_ref"], "")
        self.assertTrue(any("sin remitos" in a.lower() for a in out["alarmas"]))

    @patch("reports.services.dabra_consolidado_remitos.get_mysql_pool")
    def test_fa_sin_cae_incluida_con_alarma(self, mock_pool):
        desc_lineas = [
            ("codigo_movimiento_fa",),
            ("fa_nro_comprobante",),
            ("fa_tipo",),
            ("fa_fecha",),
            ("fe_cae",),
            ("fe_vto_cae",),
            ("SubTotal1",),
            ("ImporteVenta",),
            ("id_stock",),
            ("Cantidad",),
            ("PrecioVentaxU",),
            ("PrecioNetoxU",),
            ("PrecioIVAxU",),
            ("pordesc_bonif",),
            ("PorDesc",),
            ("imp_alicuota_iva",),
            ("NombreArticulo",),
            ("CodArtProv",),
            ("categoria_nombre",),
        ]
        linea_row = (
            1200,
            "0008-00000004",
            "FA",
            "2026-07-24",
            "",
            "",
            Decimal("100"),
            Decimal("121"),
            1,
            Decimal("1"),
            Decimal("100"),
            Decimal("100"),
            Decimal("21"),
            Decimal("0"),
            Decimal("0"),
            Decimal("21"),
            "Art",
            "950058-01 T110",
            None,
        )

        def execute_side_effect(sql, params):
            if "INNER JOIN stock" in sql:
                self.mock_cursor.description = desc_lineas
                self.mock_cursor.fetchall.return_value = [linea_row]
            elif "datosempresa" in sql:
                self.mock_cursor.description = [("CUIT",)]
                self.mock_cursor.fetchall.return_value = [("30-69074961-7",)]
            else:
                self.mock_cursor.description = []
                self.mock_cursor.fetchall.return_value = []

        self.mock_cursor.execute.side_effect = execute_side_effect
        mock_pool.return_value.get_connection.return_value = self.mock_cm

        out = get_dabra_consolidado_remitos("emp_test", mes=7, anio=2026)
        self.assertEqual(len(out["filas"]), 1)
        self.assertEqual(out["filas"][0]["cae"], "")
        self.assertTrue(any("sin CAE" in a for a in out["alarmas"]))

    @patch("reports.services.dabra_consolidado_remitos.get_mysql_pool")
    def test_sigma_mismatch_en_errores(self, mock_pool):
        desc_lineas = [
            ("codigo_movimiento_fa",),
            ("fa_nro_comprobante",),
            ("fa_tipo",),
            ("fa_fecha",),
            ("fe_cae",),
            ("fe_vto_cae",),
            ("SubTotal1",),
            ("ImporteVenta",),
            ("id_stock",),
            ("Cantidad",),
            ("PrecioVentaxU",),
            ("PrecioNetoxU",),
            ("PrecioIVAxU",),
            ("pordesc_bonif",),
            ("PorDesc",),
            ("imp_alicuota_iva",),
            ("NombreArticulo",),
            ("CodArtProv",),
            ("categoria_nombre",),
        ]
        linea_row = (
            1200,
            "0008-00000004",
            "FA",
            "2026-07-24",
            "x",
            "2026-08-01",
            Decimal("999"),
            Decimal("1210"),
            1,
            Decimal("1"),
            Decimal("100"),
            Decimal("100"),
            Decimal("21"),
            Decimal("0"),
            Decimal("0"),
            Decimal("21"),
            "Art",
            "950058-01 T110",
            None,
        )

        def execute_side_effect(sql, params):
            if "INNER JOIN stock" in sql:
                self.mock_cursor.description = desc_lineas
                self.mock_cursor.fetchall.return_value = [linea_row]
            elif "datosempresa" in sql:
                self.mock_cursor.description = [("CUIT",)]
                self.mock_cursor.fetchall.return_value = [("30-69074961-7",)]
            else:
                self.mock_cursor.description = []
                self.mock_cursor.fetchall.return_value = []

        self.mock_cursor.execute.side_effect = execute_side_effect
        mock_pool.return_value.get_connection.return_value = self.mock_cm

        out = get_dabra_consolidado_remitos("emp_test", mes=7, anio=2026)
        self.assertTrue(out["errores"])


class TestCuitNormalizado(unittest.TestCase):
    def test_11_digitos(self):
        self.assertEqual(normalizar_cuit("30-69074961-7"), "30690749617")


def _request_with_session(path: str, query: dict, session_user: dict):
    factory = RequestFactory()
    req = factory.get(path, query)
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session["user"] = session_user
    req.session.save()
    return req


class TestDabraRelayViews(unittest.TestCase):
    PERM = "reports.dabra_consolidado_remitos"

    def _user_perm(self, perm: str):
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        u.tiene_permiso = lambda p, _perm=perm: p == _perm
        return u

    def test_403_sin_permiso(self):
        req = _request_with_session(
            "/api/reports/dabra-consolidado-remitos/relay/",
            {"mes": "7", "anio": "2026"},
            {"base_empresa": "emp1"},
        )
        u = MagicMock()
        u.is_authenticated = True
        u.is_superuser = False
        u.tiene_permiso = lambda p: False
        force_authenticate(req, user=u)
        resp = DabraConsolidadoRemitosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 403)

    def test_400_sin_mes_anio(self):
        req = _request_with_session(
            "/api/reports/dabra-consolidado-remitos/relay/",
            {},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm(self.PERM))
        resp = DabraConsolidadoRemitosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 400)

    @patch("reports.dabra_consolidado_remitos_relay_views.get_dabra_consolidado_remitos")
    def test_200_preview_ok(self, mock_get):
        mock_get.return_value = {
            "columns": [],
            "filas": [{"item": "x"}],
            "totales_facturas": [],
            "alarmas": [],
            "errores": [],
            "meta": {},
        }
        req = _request_with_session(
            "/api/reports/dabra-consolidado-remitos/relay/",
            {"mes": "7", "anio": "2026"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm(self.PERM))
        resp = DabraConsolidadoRemitosRelayAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        mock_get.assert_called_once_with("emp1", mes=7, anio=2026)

    @patch("reports.dabra_consolidado_remitos_relay_views.get_dabra_consolidado_remitos")
    def test_409_export_con_errores(self, mock_get):
        mock_get.return_value = {
            "columns": [],
            "filas": [],
            "totales_facturas": [],
            "alarmas": [],
            "errores": ["Mismatch"],
            "meta": {},
        }
        req = _request_with_session(
            "/api/reports/dabra-consolidado-remitos/relay/export/",
            {"mes": "7", "anio": "2026"},
            {"base_empresa": "emp1"},
        )
        force_authenticate(req, user=self._user_perm(self.PERM))
        resp = DabraConsolidadoRemitosExportAPIView.as_view()(req)
        self.assertEqual(resp.status_code, 409)


class TestDabraExporter(unittest.TestCase):
    def _payload_minimo(self):
        return {
            "filas": [
                {
                    "cuit_emisor": "30690749617",
                    "fecha": "06/05/2026",
                    "doc_type": 1,
                    "punto_venta": "00004",
                    "numero_legal": 20777,
                    "item": "950058-01",
                    "talle": "T110",
                    "cantidad": 6.0,
                    "precio_unitario": 4307.2,
                    "bonificacion": 20.0,
                    "importe_bonificacion": 861.44,
                    "importe": 20674.56,
                    "importe_iva": 4341.66,
                    "total_gravado": 1015069.92,
                    "total": 1228234.6,
                    "comp_ref": "00001",
                    "numero_ref": 27665,
                    "entrega": "133",
                    "cae": "86184381365307",
                    "vto_cae": "16/05/2026",
                    "suc": "133",
                    "categoria": "ACCESORIOS",
                    "nombre_articulo": "NO DEBE IR",
                }
            ],
            "totales_facturas": [
                {
                    "fecha": "06/05/2026",
                    "comprobante": "A000400020779",
                    "nro_remito": "R000100027655",
                    "imp_neto": 970018.56,
                    "imp_bruto": 1173722.46,
                }
            ],
        }

    def test_dos_hojas_nombre_archivo(self):
        resp = exportar_dabra_xlsx(self._payload_minimo(), mes=7, anio=2026)
        self.assertIn("DABRA 072026.xlsx", resp["Content-Disposition"])
        info = inspeccionar_workbook(resp.content)
        self.assertEqual(info["sheetnames"], ["REPORTE", "TOTAL FACTURAS"])

    def test_headers_sample_op_vacias_y_cero(self):
        resp = exportar_dabra_xlsx(self._payload_minimo(), mes=5, anio=2026)
        info = inspeccionar_workbook(resp.content)
        self.assertEqual(info["headers"]["REPORTE"], REPORTE_HEADERS)
        self.assertEqual(info["headers"]["TOTAL FACTURAS"], TOTAL_FACTURAS_HEADERS)
        self.assertNotIn("NombreArticulo", info["headers"]["REPORTE"])
        row = info["rows"]["REPORTE"][0]
        self.assertIn(row[14], (None, ""))
        self.assertIn(row[15], (None, ""))
        for idx in range(24, 49):
            self.assertEqual(row[idx], 0)
