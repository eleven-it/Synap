# -*- coding: utf-8 -*-
"""Tests informe ventas-marcas-mensual (factor U.M., matriz, export)."""

from unittest.mock import Mock

from django.test import SimpleTestCase

from reports.models import ReportDefinition
from reports.services.export_service import ExportService
from reports.services.ventas_marcas_mensual_runner import (
    _compute_kpis_licencia,
    _parse_tasa_regalia,
    aplicar_proyeccion_filas,
    build_filas_matriz,
    build_filas_planas_export,
    ceil_proy_unidades,
    factor_docenas_unimed,
    round_proy_facturacion,
)


class FactorDocenasUnimedTest(SimpleTestCase):
    def test_mapa_p1_a_p6_y_cu(self):
        self.assertEqual(factor_docenas_unimed("P1"), 12.0)
        self.assertEqual(factor_docenas_unimed("p2"), 6.0)
        self.assertEqual(factor_docenas_unimed("P3"), 4.0)
        self.assertEqual(factor_docenas_unimed("P6"), 2.0)
        self.assertEqual(factor_docenas_unimed("CU"), 1.0)

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
                "cod_viajante",
                "nombre_vendedor",
                "codigo_cliente",
                "nombre_cliente",
                "anio_mes",
                "unidades",
                "facturacion",
            ],
        )

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
                "cod_viajante",
                "nombre_vendedor",
                "codigo_cliente",
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
