# -*- coding: utf-8 -*-
"""Tests informe ventas-marcas-mensual (factor U.M., matriz, export)."""

from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase, TestCase

from reports.models import ReportDefinition
from reports.services.export_service import ExportService
from reports.services.ventas_marcas_mensual_runner import (
    _compute_kpis_licencia,
    _delta_pct_facturacion,
    _parse_tasa_regalia,
    _resolve_tc,
    aplicar_proyeccion_filas,
    build_filas_matriz,
    build_filas_matriz_compare,
    build_filas_planas_compare_export,
    build_filas_planas_export,
    ceil_proy_unidades,
    factor_docenas_unimed,
    round_proy_facturacion,
    run_ventas_marcas_mensual,
    sort_filas_vendedores,
)
from reports.services.ventas_marcas_mensual_export import (
    DETALLE_EXPORT_HEADERS,
    fetch_detalle_renglones,
    resolve_detalle_headers,
)
from reports.services.ventas_marcas_mensual_seed import _report_defaults


class FactorDocenasUnimedTest(SimpleTestCase):
    def test_mapa_p1_a_p6_y_cu(self):
        self.assertEqual(factor_docenas_unimed("P1"), 12.0)
        self.assertEqual(factor_docenas_unimed("p2"), 6.0)
        self.assertEqual(factor_docenas_unimed("P3"), 4.0)
        self.assertEqual(factor_docenas_unimed("P6"), 2.0)
        self.assertEqual(factor_docenas_unimed("CU"), 1.0)
        self.assertEqual(factor_docenas_unimed("UNIDAD"), 1.0)
        self.assertEqual(factor_docenas_unimed("unidad"), 1.0)

    def test_desconocido_usa_uno(self):
        self.assertEqual(factor_docenas_unimed("XX"), 1.0)
        self.assertEqual(factor_docenas_unimed(None), 1.0)


class BuildFilasMatrizTest(SimpleTestCase):
    def _rows_mock(self):
        return [
            {
                "ven": 10,
                "vend_nombre": "Vendedor A",
                "codigo_cliente": "C1",
                "nombre_cliente": "Cliente Uno",
                "anio_mes": "202601",
                "packs": 12.0,
                "docenas": 1.0,
                "facturacion": 1000.0,
            },
            {
                "ven": 10,
                "vend_nombre": "Vendedor A",
                "codigo_cliente": "C1",
                "nombre_cliente": "Cliente Uno",
                "anio_mes": "202602",
                "packs": 6.0,
                "docenas": 0.5,
                "facturacion": 500.0,
            },
            {
                "ven": 10,
                "vend_nombre": "Vendedor A",
                "codigo_cliente": "C2",
                "nombre_cliente": "Cliente Dos",
                "anio_mes": "202601",
                "packs": 4.0,
                "docenas": 4.0,
                "facturacion": 200.0,
            },
        ]

    def test_armado_arbol_packs(self):
        meses = ["202601", "202602"]
        filas, kpis = build_filas_matriz(self._rows_mock(), meses, "packs")
        self.assertEqual(len(filas), 1)
        vend = filas[0]
        self.assertEqual(vend["cod"], 10)
        self.assertEqual(len(vend["clientes"]), 2)
        self.assertAlmostEqual(vend["total"]["u"], 22.0)
        self.assertAlmostEqual(vend["total"]["f"], 1700.0)
        self.assertAlmostEqual(kpis["unidades"], 22.0)
        self.assertAlmostEqual(kpis["facturacion"], 1700.0)
        self.assertAlmostEqual(kpis["precio_medio"], 1700.0 / 22.0)

    def test_armado_arbol_docenas(self):
        meses = ["202601", "202602"]
        filas, kpis = build_filas_matriz(self._rows_mock(), meses, "docenas")
        self.assertAlmostEqual(kpis["unidades"], 5.5)

    def test_truncado_meses_en_matriz(self):
        rows = [
            {
                "ven": 1,
                "vend_nombre": "V",
                "codigo_cliente": "X",
                "nombre_cliente": "X",
                "anio_mes": "202603",
                "packs": 1,
                "docenas": 1,
                "facturacion": 10,
            }
        ]
        filas, _ = build_filas_matriz(rows, ["202601", "202602"], "packs")
        self.assertEqual(len(filas), 0)


class BuildFilasPlanasExportTest(SimpleTestCase):
    def test_filas_planas_respetan_modo(self):
        rows = [
            {
                "ven": 5,
                "vend_nombre": "V",
                "codigo_cliente": "C",
                "nombre_cliente": "Cliente",
                "anio_mes": "202607",
                "packs": 24.0,
                "docenas": 2.0,
                "facturacion": 300.0,
            }
        ]
        planas_p = build_filas_planas_export(rows, ["202607"], "packs")
        self.assertAlmostEqual(planas_p[0]["unidades"], 24.0)
        planas_d = build_filas_planas_export(rows, ["202607"], "docenas")
        self.assertAlmostEqual(planas_d[0]["unidades"], 2.0)

    def test_filas_planas_con_proyeccion(self):
        rows = [
            {
                "ven": 5,
                "vend_nombre": "V",
                "codigo_cliente": "C",
                "nombre_cliente": "Cliente",
                "anio_mes": "202607",
                "packs": 12.0,
                "docenas": 1.0,
                "facturacion": 100.0,
            }
        ]
        planas = build_filas_planas_export(rows, ["202607"], "packs", coef_proyeccion=1.07)
        self.assertEqual(planas[0]["unidades_proy"], 13)
        self.assertAlmostEqual(planas[0]["facturacion_proy"], 107.0)


class KpisLicenciaTest(SimpleTestCase):
    def test_tasa_13_pct_regalias(self):
        tasa = _parse_tasa_regalia({"tasa_regalia_pct": 13})
        self.assertAlmostEqual(tasa, 0.13)
        kpis = _compute_kpis_licencia({"unidades": 10, "facturacion": 1000.0, "precio_medio": 100}, tasa, 14.5817)
        self.assertAlmostEqual(kpis["regalias"], 130.0)
        self.assertAlmostEqual(kpis["regalias_tc"], 130.0 / 14.5817, places=4)

    def test_tasa_fraccion_backend(self):
        tasa = _parse_tasa_regalia({"tasa_regalia": 0.13})
        self.assertAlmostEqual(tasa, 0.13)

    def test_regalias_tc_cero_si_tc_cero(self):
        kpis = _compute_kpis_licencia({"facturacion": 100.0}, 0.13, 0.0)
        self.assertEqual(kpis["regalias_tc"], 0.0)


class ProyeccionTest(SimpleTestCase):
    def test_ceil_unidades(self):
        self.assertEqual(ceil_proy_unidades(12, 1.07), 13)

    def test_round_facturacion(self):
        self.assertAlmostEqual(round_proy_facturacion(100, 1.07), 107.0)
        self.assertAlmostEqual(round_proy_facturacion(10.555, 1.07), 11.29)

    def test_aplicar_proyeccion_en_matriz(self):
        filas = [
            {
                "totales_mes": {"202601": {"u": 12.0, "f": 100.0}},
                "total": {"u": 12.0, "f": 100.0},
                "clientes": [
                    {
                        "valores_mes": {"202601": {"u": 12.0, "f": 100.0}},
                        "total": {"u": 12.0, "f": 100.0},
                    }
                ],
            }
        ]
        aplicar_proyeccion_filas(filas, 1.07)
        celda = filas[0]["totales_mes"]["202601"]
        self.assertEqual(celda["pu"], 13)
        self.assertAlmostEqual(celda["pf"], 107.0)


class VentasMarcasMensualRunnerResilienceTest(SimpleTestCase):
    def test_normaliza_fechas_string_de_filtros_y_expone_periodo_aplicado(self):
        report = ReportDefinition(
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category="operational",
            version="1.0.0",
        )
        payload = {
            "filters": {
                "base_empresa": "administranet1",
                "fecha_inicio_facturacion": "2026-07-01",
                "fecha_fin_facturacion": "2026-07-31",
            }
        }
        cursor = Mock()
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = []
        cursor.description = []
        conn = Mock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__.return_value = conn

        with (
            patch(
                "reports.services.ventas_marcas_mensual_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.alcance_objetivos_cod_viajante",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.get_mysql_pool",
                return_value=pool,
            ),
        ):
            result = run_ventas_marcas_mensual(report, payload, Mock())

        self.assertEqual(result.meta["filters_applied"]["fecha_inicio_facturacion"], "2026-07-01")
        self.assertEqual(result.meta["filters_applied"]["fecha_fin_facturacion"], "2026-07-31")

    def test_devuelve_resultado_vacio_si_falla_alcance_comercial(self):
        report = ReportDefinition(
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category="operational",
            version="1.0.0",
        )
        payload = {
            "filters": {
                "base_empresa": "administranet1",
                "fecha_inicio": "2026-07-01",
                "fecha_fin": "2026-07-31",
            }
        }
        with (
            patch(
                "reports.services.ventas_marcas_mensual_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.alcance_objetivos_cod_viajante",
                side_effect=ConnectionError("MySQL no disponible"),
            ),
        ):
            result = run_ventas_marcas_mensual(report, payload, Mock())

        self.assertEqual(result.data, [])
        self.assertEqual(result.totals, {})
        self.assertEqual(
            result.notes,
            ["Error al validar el alcance comercial; no se mostrarán datos."],
        )
        self.assertIn("extra", result.meta)
        self.assertEqual(result.meta["extra"]["meses"], [])
        self.assertEqual(result.meta["extra"]["kpis"]["unidades"], 0)

    def test_filtro_punto_venta_incluye_id_pv_en_sql(self):
        report = ReportDefinition(
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category="operational",
            version="1.0.0",
        )
        payload = {
            "filters": {
                "base_empresa": "administranet1",
                "fecha_inicio_facturacion": "2026-07-01",
                "fecha_fin_facturacion": "2026-07-31",
                "punto_venta": ["200"],
            }
        }
        captured = {}

        def fake_execute(sql, params=None):
            captured["sql"] = sql
            captured["params"] = list(params or [])

        cursor = Mock()
        cursor.execute = fake_execute
        cursor.fetchall.return_value = []
        cursor.description = []
        conn = Mock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__.return_value = conn

        with (
            patch(
                "reports.services.ventas_marcas_mensual_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.alcance_objetivos_cod_viajante",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.get_mysql_pool",
                return_value=pool,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_tc",
                return_value=14.5817,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_marcas_incluidos",
                return_value=[],
            ),
        ):
            result = run_ventas_marcas_mensual(report, payload, Mock())

        self.assertIn("cc.id_pv IN", captured.get("sql", ""))
        self.assertIn(200, captured.get("params", []))
        self.assertEqual(result.meta["filters_applied"]["punto_venta"], [200])
        self.assertIn("DATE_FORMAT(cc.Fecha, '%Y%m')", captured["sql"] % tuple(captured["params"]))

    def test_export_detalle_escapa_formatos_date_format_para_mysql(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        cursor.description = []

        fetch_detalle_renglones(
            cursor,
            where_s="cc.Fecha BETWEEN %s AND %s",
            params=["2026-07-01", "2026-07-31"],
            cat_sql="",
            cat_params=[],
            modo_unidades="packs",
        )

        sql, params = cursor.execute.call_args.args
        self.assertIn("DATE_FORMAT(cc.Fecha, '%Y-%m-%d')", sql % tuple(params))
        self.assertIn("DATE_FORMAT(cc.Fecha, '%Y%m')", sql % tuple(params))
        self.assertIn("m.CodMarca = art.CodigoMarca", sql)
        self.assertNotIn("art.CodMarca", sql)


class VentasMarcasMensualExportHeadersTest(SimpleTestCase):
    def setUp(self):
        self.svc = ExportService(Mock())

    def test_export_headers_orden_y_columnas(self):
        r = ReportDefinition(slug="ventas-marcas-mensual", config={})
        row = {
            "cod_viajante": 1,
            "nombre_vendedor": "A",
            "codigo_cliente": "C1",
            "nombre_cliente": "Cliente",
            "anio_mes": "202607",
            "unidades": 10.0,
            "facturacion": 100.0,
            "extra": "omit",
        }
        h = self.svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "nombre_vendedor",
                "nombre_cliente",
                "anio_mes",
                "unidades",
                "facturacion",
            ],
        )
        self.assertNotIn("cod_viajante", h)
        self.assertNotIn("codigo_cliente", h)

    def test_export_headers_con_proyeccion(self):
        r = ReportDefinition(slug="ventas-marcas-mensual", config={})
        row = {
            "cod_viajante": 1,
            "nombre_vendedor": "A",
            "codigo_cliente": "C1",
            "nombre_cliente": "Cliente",
            "anio_mes": "202607",
            "unidades": 10.0,
            "facturacion": 100.0,
            "unidades_proy": 11.0,
            "facturacion_proy": 107.0,
        }
        h = self.svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "nombre_vendedor",
                "nombre_cliente",
                "anio_mes",
                "unidades",
                "facturacion",
                "unidades_proy",
                "facturacion_proy",
            ],
        )

    def test_export_filename_patron(self):
        name = self.svc._resolve_export_filename(
            "ventas-marcas-mensual",
            {"filters": {"fecha_inicio_facturacion": "2026-07-01", "fecha_fin_facturacion": "2026-07-31"}},
            "20260729120000",
        )
        self.assertTrue(name.startswith("Ventas_marcas_mensual_"))
        self.assertTrue(name.endswith(".xlsx"))


class SortFilasVendedoresTest(SimpleTestCase):
    def _filas_dos_vendedores(self):
        return [
            {
                "cod": 1,
                "nombre": "Bajo",
                "total": {"u": 10.0, "f": 100.0},
            },
            {
                "cod": 2,
                "nombre": "Alto",
                "total": {"u": 50.0, "f": 5000.0},
            },
        ]

    def test_orden_facturacion_desc(self):
        ordenadas = sort_filas_vendedores(self._filas_dos_vendedores(), campo="f", descendente=True)
        self.assertEqual(ordenadas[0]["cod"], 2)
        self.assertEqual(ordenadas[1]["cod"], 1)

    def test_orden_unidades_asc(self):
        ordenadas = sort_filas_vendedores(self._filas_dos_vendedores(), campo="u", descendente=False)
        self.assertEqual(ordenadas[0]["cod"], 1)
        self.assertEqual(ordenadas[1]["cod"], 2)


class PresetConfigShapeTest(SimpleTestCase):
    def test_preset_hombre_en_config_seed(self):
        cfg = _report_defaults()["config"]
        self.assertIn("preset_hombre", cfg)
        preset = cfg["preset_hombre"]
        self.assertIn("id_manuales", preset)
        self.assertIsInstance(preset["id_manuales"], list)
        self.assertEqual(preset.get("label"), "Hombre")


class UmDesconocidasMetaTest(SimpleTestCase):
    def test_um_desconocidas_en_meta_extra(self):
        report = ReportDefinition(
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category="operational",
            version="1.0.0",
        )
        payload = {
            "filters": {
                "base_empresa": "administranet1",
                "fecha_inicio_facturacion": "2026-07-01",
                "fecha_fin_facturacion": "2026-07-31",
            }
        }
        cursor = Mock()
        product_row = (
            10,
            "Vendedor",
            "C1",
            "Cliente",
            "202607",
            12.0,
            1.0,
            1000.0,
            "XX,P1",
        )
        product_desc = [
            ("ven",),
            ("vend_nombre",),
            ("codigo_cliente",),
            ("nombre_cliente",),
            ("anio_mes",),
            ("packs",),
            ("docenas",),
            ("facturacion",),
            ("ums_raw",),
        ]

        def fake_execute(sql, params=None):
            if "NOT EXISTS" in (sql or ""):
                cursor.description = [
                    ("codigo_cliente",),
                    ("nombre_cliente",),
                    ("anio_mes",),
                    ("facturacion",),
                ]
                cursor.fetchall.return_value = []
            else:
                cursor.description = product_desc
                cursor.fetchall.return_value = [product_row]

        cursor.execute = fake_execute
        cursor.fetchall.return_value = [product_row]
        cursor.description = product_desc
        conn = Mock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__.return_value = conn

        with (
            patch(
                "reports.services.ventas_marcas_mensual_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.alcance_objetivos_cod_viajante",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.get_mysql_pool",
                return_value=pool,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_tc",
                return_value=14.5817,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_marcas_incluidos",
                return_value=[],
            ),
        ):
            result = run_ventas_marcas_mensual(report, payload, Mock())

        ums = result.meta.get("extra", {}).get("um_desconocidas", [])
        self.assertIn("XX", ums)
        self.assertNotIn("P1", ums)
        self.assertTrue(result.meta["extra"]["filas"])


class BuildFilasMatrizCompareTest(SimpleTestCase):
    def _row(self, ven, cli, mes, packs, fact):
        return {
            "ven": ven,
            "vend_nombre": "V",
            "codigo_cliente": cli,
            "nombre_cliente": f"C {cli}",
            "anio_mes": mes,
            "packs": packs,
            "docenas": packs / 12.0,
            "facturacion": fact,
        }

    def test_celdas_a_b_por_mes(self):
        rows_a = [self._row(1, "C1", "202601", 12, 100)]
        rows_b = [self._row(1, "C1", "202601", 6, 50)]
        filas, kpis_a, kpis_b = build_filas_matriz_compare(rows_a, rows_b, ["202601"], "packs")
        self.assertAlmostEqual(kpis_a["facturacion"], 100)
        self.assertAlmostEqual(kpis_b["facturacion"], 50)
        celda = filas[0]["totales_mes"]["202601"]
        self.assertAlmostEqual(celda["a"]["u"], 12)
        self.assertAlmostEqual(celda["b"]["u"], 6)


class DeltaPctFacturacionTest(SimpleTestCase):
    def test_delta_positivo(self):
        self.assertAlmostEqual(_delta_pct_facturacion(100, 150), 50.0)

    def test_delta_base_cero(self):
        self.assertIsNone(_delta_pct_facturacion(0, 0))


class BuildFilasPlanasCompareExportTest(SimpleTestCase):
    def test_columnas_a_y_b(self):
        rows_a = [
            {
                "ven": 1,
                "vend_nombre": "V",
                "codigo_cliente": "C1",
                "nombre_cliente": "Cliente",
                "anio_mes": "202601",
                "packs": 10,
                "docenas": 1,
                "facturacion": 100,
            }
        ]
        rows_b = [
            {
                "ven": 1,
                "vend_nombre": "V",
                "codigo_cliente": "C1",
                "nombre_cliente": "Cliente",
                "anio_mes": "202601",
                "packs": 5,
                "docenas": 0.5,
                "facturacion": 40,
            }
        ]
        planas = build_filas_planas_compare_export(rows_a, rows_b, ["202601"], "packs")
        self.assertEqual(len(planas), 1)
        self.assertAlmostEqual(planas[0]["unidades_a"], 10)
        self.assertAlmostEqual(planas[0]["unidades_b"], 5)
        self.assertAlmostEqual(planas[0]["facturacion_a"], 100)
        self.assertAlmostEqual(planas[0]["facturacion_b"], 40)


class VentasMarcasMensualCompareRunnerTest(SimpleTestCase):
    def test_marcas_iguales_rechazadas(self):
        report = ReportDefinition(
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category="operational",
            version="1.0.0",
        )
        payload = {
            "filters": {
                "base_empresa": "administranet1",
                "fecha_inicio_facturacion": "2026-01-01",
                "fecha_fin_facturacion": "2026-01-31",
                "modo_comparacion": "comparar",
                "marca_a": "PUM",
                "marca_b": "PUM",
            }
        }
        with (
            patch(
                "reports.services.ventas_marcas_mensual_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.alcance_objetivos_cod_viajante",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.get_mysql_pool",
            ) as mock_pool,
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_marca_single",
                side_effect=[(10, "PUM"), (10, "PUM")],
            ),
        ):
            cursor = Mock()
            conn = Mock()
            conn.cursor.return_value = cursor
            mock_pool.return_value.get_connection.return_value.__enter__.return_value = conn

            result = run_ventas_marcas_mensual(report, payload, Mock())

        self.assertEqual(result.data, [])
        self.assertIn("Las marcas A y B deben ser distintas.", result.notes)


class VentasMarcasMensualExportDetalleTest(SimpleTestCase):
    def test_headers_detalle(self):
        self.assertIn("fecha", DETALLE_EXPORT_HEADERS)
        self.assertIn("nombre_articulo", DETALLE_EXPORT_HEADERS)
        self.assertNotIn("cod_viajante", DETALLE_EXPORT_HEADERS)
        self.assertNotIn("codigo_cliente", DETALLE_EXPORT_HEADERS)

    def test_headers_detalle_con_proyeccion(self):
        h = resolve_detalle_headers({"unidades_proy": 1, "facturacion_proy": 1})
        self.assertIn("unidades_proy", h)


class VentasMarcasMensualExportCompareHeadersTest(SimpleTestCase):
    def setUp(self):
        self.svc = ExportService(Mock())

    def test_export_headers_modo_comparar(self):
        r = ReportDefinition(slug="ventas-marcas-mensual", config={})
        row = {
            "cod_viajante": 1,
            "nombre_vendedor": "A",
            "codigo_cliente": "C1",
            "nombre_cliente": "Cliente",
            "anio_mes": "202601",
            "unidades_a": 10,
            "facturacion_a": 100,
            "unidades_b": 5,
            "facturacion_b": 40,
        }
        h = self.svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "nombre_vendedor",
                "nombre_cliente",
                "anio_mes",
                "unidades_a",
                "facturacion_a",
                "unidades_b",
                "facturacion_b",
            ],
        )


class ResolveTcRunnerTest(SimpleTestCase):
    def test_tc_manual_prevalece(self):
        tc = _resolve_tc(None, {"tc": "1100"}, base_empresa="emp")
        self.assertEqual(tc, 1100.0)

    @patch("core.services.cotizacion_service.resolver_tc", return_value=1200.0)
    def test_tc_vacio_delega_resolver_tc(self, mock_resolver):
        tc = _resolve_tc(MagicMock(), {"tc": ""}, base_empresa="emp_test", fecha_corte="2026-07-15")
        self.assertEqual(tc, 1200.0)
        mock_resolver.assert_called_once()

    @patch("core.services.cotizacion_service.resolver_tc", return_value=None)
    def test_fallback_145817_si_resolver_none(self, _mock_resolver):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        tc = _resolve_tc(cursor, {}, base_empresa="emp_test", fecha_corte="2026-07-15")
        self.assertAlmostEqual(tc, 14.5817, places=4)


class PresetHombreServiceTests(TestCase):
    def setUp(self):
        from reports.models import ReportCategory

        ReportDefinition.objects.filter(
            slug="ventas-marcas-mensual", empresa__isnull=True
        ).delete()
        ReportDefinition.objects.create(
            empresa=None,
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category=ReportCategory.OPERATIONAL,
            config={"preset_hombre": {"label": "Hombre", "id_manuales": []}},
            is_active=True,
            is_visible=True,
        )

    def test_normalize_dedup_y_trim(self):
        from reports.services.ventas_marcas_mensual_preset import normalize_id_manuales

        self.assertEqual(
            normalize_id_manuales([" A ", "A", "b", "", None]),
            ["A", "b"],
        )

    def test_set_preset_persiste(self):
        from reports.services.ventas_marcas_mensual_preset import (
            read_preset_hombre,
            set_preset_hombre,
        )

        user = MagicMock()
        user.cod_usuario = "supervisor"
        stored = set_preset_hombre(["SA1", "SA2"], user=user)
        self.assertEqual(stored["id_manuales"], ["SA1", "SA2"])
        self.assertEqual(stored["updated_by"], "supervisor")
        self.assertEqual(read_preset_hombre()["id_manuales"], ["SA1", "SA2"])


class PresetHombreApiTests(TestCase):
    def setUp(self):
        from reports.models import ReportCategory

        ReportDefinition.objects.filter(
            slug="ventas-marcas-mensual", empresa__isnull=True
        ).delete()
        ReportDefinition.objects.create(
            empresa=None,
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category=ReportCategory.OPERATIONAL,
            config={"preset_hombre": {"label": "Hombre", "id_manuales": ["OLD"]}},
            is_active=True,
            is_visible=True,
        )

    def _user(self, *, supervisor=False):
        user = MagicMock()
        user.is_authenticated = True
        user.is_superuser = False
        user.is_admin = MagicMock(return_value=False)
        user.cod_usuario = "supervisor" if supervisor else "vendedor"
        user.tiene_permiso = lambda p: p == "reports.view_operational"
        return user

    @patch("reports.ventas_marcas_mensual_api_views.user_has_full_access", return_value=False)
    def test_get_sin_edicion(self, _full):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from reports.ventas_marcas_mensual_api_views import VentasMarcasMensualPresetAPIView

        factory = APIRequestFactory()
        request = factory.get("/api/reports/ventas-marcas-mensual/preset-hombre/")
        force_authenticate(request, user=self._user())
        response = VentasMarcasMensualPresetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_edit"])
        self.assertEqual(response.data["preset_hombre"]["id_manuales"], ["OLD"])

    @patch("reports.ventas_marcas_mensual_api_views.user_has_full_access", return_value=False)
    def test_patch_rechaza_no_supervisor(self, _full):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from reports.ventas_marcas_mensual_api_views import VentasMarcasMensualPresetAPIView

        factory = APIRequestFactory()
        request = factory.patch(
            "/api/reports/ventas-marcas-mensual/preset-hombre/",
            {"id_manuales": ["X"]},
            format="json",
        )
        force_authenticate(request, user=self._user())
        response = VentasMarcasMensualPresetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 403)

    @patch("reports.ventas_marcas_mensual_api_views.user_has_full_access", return_value=True)
    def test_patch_supervisor_ok(self, _full):
        from rest_framework.test import APIRequestFactory, force_authenticate

        from reports.ventas_marcas_mensual_api_views import VentasMarcasMensualPresetAPIView

        factory = APIRequestFactory()
        request = factory.patch(
            "/api/reports/ventas-marcas-mensual/preset-hombre/",
            {"id_manuales": ["H1", "H2"]},
            format="json",
        )
        force_authenticate(request, user=self._user(supervisor=True))
        response = VentasMarcasMensualPresetAPIView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["preset_hombre"]["id_manuales"], ["H1", "H2"])
        self.assertTrue(response.data["can_edit"])


class VentasMarcasMensualPostPieRunnerTest(SimpleTestCase):
    """Runner VMM usa importe post-pie (REQ-VMM-PIE-01, REQ-VMM-PIE-04)."""

    def _run_with_mock_rows(self, rows, *, modo_comparacion="una", extra_filters=None):
        report = ReportDefinition(
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category="operational",
            version="1.0.0",
        )
        filters = {
            "base_empresa": "administranet1",
            "fecha_inicio_facturacion": "2026-07-01",
            "fecha_fin_facturacion": "2026-07-31",
            "tasa_regalia_pct": 13,
        }
        if extra_filters:
            filters.update(extra_filters)
        payload = {"filters": filters}
        captured = {}

        def fake_execute(sql, params=None):
            captured["sql"] = sql
            captured["params"] = list(params or [])

        cursor = Mock()
        cursor.execute = fake_execute
        cursor.fetchall.return_value = rows
        cursor.description = [
            ("ven",),
            ("vend_nombre",),
            ("codigo_cliente",),
            ("nombre_cliente",),
            ("anio_mes",),
            ("packs",),
            ("docenas",),
            ("facturacion",),
            ("ums_raw",),
        ]
        conn = Mock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__.return_value = conn

        patches = [
            patch(
                "reports.services.ventas_marcas_mensual_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.alcance_objetivos_cod_viajante",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.get_mysql_pool",
                return_value=pool,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_tc",
                return_value=14.5817,
            ),
        ]
        if modo_comparacion == "comparar":
            patches.append(
                patch(
                    "reports.services.ventas_marcas_mensual_runner._resolve_marca_single",
                    side_effect=[(10, "PUM"), (20, "PUW")],
                )
            )
        else:
            patches.append(
                patch(
                    "reports.services.ventas_marcas_mensual_runner._resolve_marcas_incluidos",
                    return_value=[10],
                )
            )

        from contextlib import ExitStack

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = run_ventas_marcas_mensual(report, payload, Mock())

        return result, captured

    def test_sql_emitido_usa_expr_post_pie(self):
        row = (1, "V", "C1", "Cliente", "202607", 10.0, 10.0, 800.0, "CU")
        _, captured = self._run_with_mock_rows([row])
        sql = captured.get("sql", "")
        self.assertIn("SubTotal1", sql)
        self.assertIn("SubtotalDesc", sql)
        self.assertIn("0.0001", sql)
        self.assertIn("PrecioNetoxR", sql)

    def test_fa_dto_pie_20_facturacion_y_regalias(self):
        """FA SubTotal1=1000, SubtotalDesc=800 → fact=800; regalías = 800 × 13%."""
        row = (1, "V", "C1", "Cliente", "202607", 10.0, 10.0, 800.0, "CU")
        result, _ = self._run_with_mock_rows([row])
        kpis = result.meta["extra"]["kpis"]
        self.assertAlmostEqual(kpis["facturacion"], 800.0, places=2)
        self.assertAlmostEqual(kpis["unidades"], 10.0, places=2)
        self.assertAlmostEqual(kpis["regalias"], 104.0, places=2)
        self.assertAlmostEqual(kpis["precio_medio"], 80.0, places=2)

    def test_nc_mismo_factor_signo_negativo(self):
        row = (1, "V", "C1", "Cliente", "202607", -5.0, -5.0, -400.0, "CU")
        result, _ = self._run_with_mock_rows([row])
        kpis = result.meta["extra"]["kpis"]
        self.assertAlmostEqual(kpis["facturacion"], -400.0, places=2)
        self.assertAlmostEqual(kpis["unidades"], -5.0, places=2)

    def test_sin_pie_paridad_factor_uno(self):
        row = (1, "V", "C1", "Cliente", "202607", 12.0, 1.0, 1000.0, "P1")
        result, _ = self._run_with_mock_rows([row])
        kpis = result.meta["extra"]["kpis"]
        self.assertAlmostEqual(kpis["facturacion"], 1000.0, places=2)
        self.assertAlmostEqual(kpis["unidades"], 12.0, places=2)


class VentasMarcasMensualComparePostPieTest(SimpleTestCase):
    def test_modo_comparar_kpis_post_pie(self):
        report = ReportDefinition(
            slug="ventas-marcas-mensual",
            name="Ventas marcas mensual",
            category="operational",
            version="1.0.0",
        )
        payload = {
            "filters": {
                "base_empresa": "administranet1",
                "fecha_inicio_facturacion": "2026-01-01",
                "fecha_fin_facturacion": "2026-01-31",
                "modo_comparacion": "comparar",
                "marca_a": "PUM",
                "marca_b": "PUW",
            }
        }
        call_count = {"n": 0}

        def fake_execute(sql, params=None):
            call_count["sql"] = sql

        def fake_fetchall():
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [(1, "V", "C1", "Cliente", "202601", 10.0, 10.0, 800.0, "CU")]
            return [(1, "V", "C1", "Cliente", "202601", 6.0, 6.0, 480.0, "CU")]

        cursor = Mock()
        cursor.execute = fake_execute
        cursor.fetchall = fake_fetchall
        cursor.description = [
            ("ven",),
            ("vend_nombre",),
            ("codigo_cliente",),
            ("nombre_cliente",),
            ("anio_mes",),
            ("packs",),
            ("docenas",),
            ("facturacion",),
            ("ums_raw",),
        ]
        conn = Mock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__.return_value = conn

        with (
            patch(
                "reports.services.ventas_marcas_mensual_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.alcance_objetivos_cod_viajante",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner.get_mysql_pool",
                return_value=pool,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_tc",
                return_value=14.5817,
            ),
            patch(
                "reports.services.ventas_marcas_mensual_runner._resolve_marca_single",
                side_effect=[(10, "PUM"), (20, "PUW")],
            ),
        ):
            result = run_ventas_marcas_mensual(report, payload, Mock())

        cmp_meta = result.meta["extra"]["compare"]
        self.assertAlmostEqual(cmp_meta["marca_a"]["kpis"]["facturacion"], 800.0, places=2)
        self.assertAlmostEqual(cmp_meta["marca_b"]["kpis"]["facturacion"], 480.0, places=2)
        self.assertIn("SubTotal1", call_count.get("sql", ""))
        delta = cmp_meta.get("delta_pct_facturacion")
        if delta is not None:
            self.assertAlmostEqual(delta, -40.0, places=1)


class VentasMarcasMensualUnidadesInvariantesPostPieTest(SimpleTestCase):
    """Unidades no llevan factor pie (REQ-VMM-PIE-05)."""

    def test_unidades_sin_factor_pie_con_dto_20(self):
        rows = [
            {
                "ven": 1,
                "vend_nombre": "V",
                "codigo_cliente": "C1",
                "nombre_cliente": "Cliente",
                "anio_mes": "202607",
                "packs": 10.0,
                "docenas": 10.0,
                "facturacion": 800.0,
            }
        ]
        _, kpis = build_filas_matriz(rows, ["202607"], "packs")
        self.assertAlmostEqual(kpis["unidades"], 10.0)
        self.assertAlmostEqual(kpis["facturacion"], 800.0)


class VentasMarcasMensualExportPostPieTest(SimpleTestCase):
    def test_detalle_sql_usa_post_pie(self):
        cursor = Mock()
        cursor.fetchall.return_value = []
        cursor.description = []

        fetch_detalle_renglones(
            cursor,
            where_s="cc.Fecha BETWEEN %s AND %s",
            params=["2026-07-01", "2026-07-31"],
            cat_sql="",
            cat_params=[],
            modo_unidades="packs",
        )

        sql, _ = cursor.execute.call_args.args
        self.assertIn("SubTotal1", sql)
        self.assertIn("SubtotalDesc", sql)
        self.assertNotIn("_signo_imp_sql", sql)

    def test_suma_detalle_coherente_con_kpi(self):
        cursor = Mock()
        cursor.fetchall.return_value = [
            (
                "2026-07-15",
                "FA",
                "1-100",
                1,
                "Vendedor",
                "C1",
                "Cliente",
                "SA1",
                "Art",
                "PUM",
                "202607",
                5.0,
                5.0,
                400.0,
            ),
            (
                "2026-07-16",
                "FA",
                "1-101",
                1,
                "Vendedor",
                "C1",
                "Cliente",
                "SA2",
                "Art2",
                "PUM",
                "202607",
                5.0,
                5.0,
                400.0,
            ),
        ]
        cursor.description = [
            ("fecha",),
            ("tipo_comprobante",),
            ("nro_comprobante",),
            ("ven",),
            ("vend_nombre",),
            ("codigo_cliente",),
            ("nombre_cliente",),
            ("id_manual",),
            ("nombre_articulo",),
            ("nombre_marca",),
            ("anio_mes",),
            ("packs",),
            ("docenas",),
            ("facturacion",),
        ]
        rows = fetch_detalle_renglones(
            cursor,
            where_s="1=1",
            params=[],
            cat_sql="",
            cat_params=[],
            modo_unidades="packs",
        )
        suma_detalle = sum(r["facturacion"] for r in rows)
        self.assertAlmostEqual(suma_detalle, 800.0, places=2)
        self.assertAlmostEqual(sum(r["unidades"] for r in rows), 10.0, places=2)


class VentasMarcasMensualAjustesCabeceraTest(SimpleTestCase):
    def test_pin_deja_ajustes_al_final_y_suma_kpi(self):
        from reports.services.ventas_marcas_mensual_runner import _pin_ajustes_vmm

        rows = [
            {
                "ven": 1,
                "vend_nombre": "Vendedor",
                "codigo_cliente": "10",
                "nombre_cliente": "Cliente A",
                "anio_mes": "202608",
                "packs": 12.0,
                "docenas": 1.0,
                "facturacion": 800.0,
            },
            {
                "ven": -1,
                "vend_nombre": "Ajustes sin mercadería",
                "codigo_cliente": "99",
                "nombre_cliente": "Cliente NC",
                "anio_mes": "202608",
                "packs": 0.0,
                "docenas": 0.0,
                "facturacion": -100.0,
            },
        ]
        filas, kpis = build_filas_matriz(rows, ["202608"], "packs")
        filas = _pin_ajustes_vmm(filas)
        self.assertAlmostEqual(kpis["facturacion"], 700.0, places=2)
        self.assertAlmostEqual(kpis["unidades"], 12.0, places=2)
        self.assertEqual(filas[-1]["nombre"], "Ajustes sin mercadería")
        self.assertTrue(filas[-1]["es_ajuste_cabecera"])
        self.assertEqual(filas[-1]["clientes"][0]["nombre"], "Cliente NC")
