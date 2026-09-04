# -*- coding: utf-8 -*-
"""Tests informe ventas-marca-superart (árbol y export)."""
from contextlib import ExitStack
from unittest.mock import MagicMock, Mock, patch

from django.test import SimpleTestCase

from reports.models import ReportDefinition
from reports.services.export_service import ExportService
from reports.services.ventas_marca_superart_runner import (
    CODIGO_MARCA_AJUSTES,
    ID_MANUAL_AJUSTES,
    NOMBRE_MARCA_AJUSTES,
    NOMBRE_SUPERART_AJUSTES,
    _display_marca,
    _display_superart,
    _filtros_catalogo_restringen,
    _flatten_filas_marca_superart,
    _nest_marca_superart_articulo,
    _pin_ajustes_al_final,
    _sort_arbol_marca_superart,
    run_ventas_marca_superart,
)


class VentasMarcaSuperartNestTests(SimpleTestCase):
    def test_sin_marca_display(self):
        cod, nom = _display_marca(0, "")
        self.assertEqual(cod, 0)
        self.assertEqual(nom, "Sin marca")

    def test_sin_superart_display(self):
        manual, nom = _display_superart("")
        self.assertEqual(manual, "")
        self.assertEqual(nom, "Sin SuperArt")

    def test_nest_marca_superart_articulo_rollups(self):
        filas = [
            {
                "codigo_marca": 1,
                "nombre_marca": "Marca A",
                "id_manual": "SA1",
                "id_art": 10,
                "nombre_articulo": "Art A",
                "packs": 12.0,
                "docenas": 1.0,
                "facturacion": 100.0,
            },
            {
                "codigo_marca": 1,
                "nombre_marca": "Marca A",
                "id_manual": "SA1",
                "id_art": 20,
                "nombre_articulo": "Art B",
                "packs": 6.0,
                "docenas": 1.0,
                "facturacion": 50.0,
            },
            {
                "codigo_marca": 1,
                "nombre_marca": "Marca A",
                "id_manual": "SA2",
                "id_art": 30,
                "nombre_articulo": "Art C",
                "packs": 2.0,
                "docenas": 2.0,
                "facturacion": 25.0,
            },
        ]
        arbol = _nest_marca_superart_articulo(filas)
        self.assertEqual(len(arbol), 1)
        marca = arbol[0]
        self.assertEqual(marca["tipo"], "marca")
        self.assertEqual(marca["packs"], 20.0)
        self.assertEqual(marca["docenas"], 4.0)
        self.assertEqual(marca["facturacion"], 175.0)
        self.assertEqual(len(marca["children"]), 2)
        sa1 = next(c for c in marca["children"] if c["id_manual"] == "SA1")
        self.assertEqual(sa1["packs"], 18.0)
        self.assertEqual(len(sa1["children"]), 2)

    def test_nest_fallbacks_sin_marca_sin_superart(self):
        filas = [
            {
                "codigo_marca": 0,
                "nombre_marca": "",
                "id_manual": "",
                "id_art": 1,
                "nombre_articulo": "X",
                "packs": 1.0,
                "docenas": 1.0,
                "facturacion": 10.0,
            }
        ]
        arbol = _nest_marca_superart_articulo(filas)
        self.assertEqual(arbol[0]["nombre_marca"], "Sin marca")
        self.assertEqual(arbol[0]["children"][0]["nombre_superart"], "Sin SuperArt")

    def test_flatten_filas(self):
        arbol = [
            {
                "tipo": "marca",
                "codigo_marca": 1,
                "nombre_marca": "M",
                "children": [
                    {
                        "tipo": "superart",
                        "id_manual": "SA",
                        "nombre_superart": "SA",
                        "children": [
                            {
                                "tipo": "articulo",
                                "id_art": 9,
                                "nombre_articulo": "Art",
                                "packs": 2.0,
                                "docenas": 0.5,
                                "facturacion": 10.0,
                            }
                        ],
                    }
                ],
            }
        ]
        flat = _flatten_filas_marca_superart(arbol)
        self.assertEqual(len(flat), 1)
        self.assertEqual(flat[0]["nombre_marca"], "M")
        self.assertEqual(flat[0]["nombre_superart"], "SA")
        self.assertEqual(flat[0]["nombre_articulo"], "Art")
        self.assertEqual(flat[0]["packs"], 2.0)

    def test_sort_arbol_por_facturacion_desc(self):
        arbol = [
            {
                "tipo": "marca",
                "codigo_marca": 1,
                "nombre_marca": "A",
                "facturacion": 10.0,
                "packs": 1.0,
                "docenas": 1.0,
                "children": [
                    {
                        "tipo": "superart",
                        "id_manual": "S",
                        "nombre_superart": "S",
                        "facturacion": 10.0,
                        "packs": 1.0,
                        "docenas": 1.0,
                        "children": [
                            {
                                "tipo": "articulo",
                                "id_art": 1,
                                "nombre_articulo": "Bajo",
                                "facturacion": 1.0,
                                "packs": 1.0,
                                "docenas": 1.0,
                            },
                            {
                                "tipo": "articulo",
                                "id_art": 2,
                                "nombre_articulo": "Alto",
                                "facturacion": 9.0,
                                "packs": 1.0,
                                "docenas": 1.0,
                            },
                        ],
                    }
                ],
            }
        ]
        sorted_arbol = _sort_arbol_marca_superart(arbol, "facturacion", "desc")
        arts = sorted_arbol[0]["children"][0]["children"]
        self.assertEqual(arts[0]["nombre_articulo"], "Alto")
        self.assertEqual(arts[1]["nombre_articulo"], "Bajo")

    def test_display_superart_ajustes_cabecera(self):
        manual, nom = _display_superart(ID_MANUAL_AJUSTES)
        self.assertEqual(manual, ID_MANUAL_AJUSTES)
        self.assertEqual(nom, NOMBRE_SUPERART_AJUSTES)

    def test_filtros_catalogo_restringen(self):
        self.assertFalse(_filtros_catalogo_restringen([], [], [], [], [], [], []))
        self.assertTrue(_filtros_catalogo_restringen([1], [], [], [], [], [], []))
        self.assertTrue(_filtros_catalogo_restringen([], [], [], [], [], [], ["SA1"]))

    def test_pin_ajustes_al_final_y_flag(self):
        arbol = [
            {
                "tipo": "marca",
                "codigo_marca": CODIGO_MARCA_AJUSTES,
                "nombre_marca": NOMBRE_MARCA_AJUSTES,
                "facturacion": 50.0,
                "children": [
                    {
                        "tipo": "superart",
                        "id_manual": ID_MANUAL_AJUSTES,
                        "nombre_superart": NOMBRE_SUPERART_AJUSTES,
                        "children": [
                            {
                                "tipo": "articulo",
                                "id_art": 0,
                                "nombre_articulo": "Cliente X",
                                "facturacion": 50.0,
                            }
                        ],
                    }
                ],
            },
            {
                "tipo": "marca",
                "codigo_marca": 1,
                "nombre_marca": "Marca A",
                "facturacion": 10.0,
                "children": [],
            },
        ]
        pinned = _pin_ajustes_al_final(arbol)
        self.assertEqual(pinned[0]["nombre_marca"], "Marca A")
        self.assertEqual(pinned[-1]["nombre_marca"], NOMBRE_MARCA_AJUSTES)
        self.assertTrue(pinned[-1]["es_ajuste_cabecera"])
        self.assertTrue(pinned[-1]["children"][0]["es_ajuste_cabecera"])
        self.assertTrue(pinned[-1]["children"][0]["children"][0]["es_ajuste_cabecera"])

    def test_nest_ajustes_por_cliente(self):
        filas = [
            {
                "codigo_marca": CODIGO_MARCA_AJUSTES,
                "nombre_marca": NOMBRE_MARCA_AJUSTES,
                "id_manual": ID_MANUAL_AJUSTES,
                "id_art": 0,
                "nombre_articulo": "Cliente A",
                "packs": 0.0,
                "docenas": 0.0,
                "facturacion": -100.0,
            },
            {
                "codigo_marca": CODIGO_MARCA_AJUSTES,
                "nombre_marca": NOMBRE_MARCA_AJUSTES,
                "id_manual": ID_MANUAL_AJUSTES,
                "id_art": 0,
                "nombre_articulo": "Cliente B",
                "packs": 0.0,
                "docenas": 0.0,
                "facturacion": -50.0,
            },
        ]
        arbol = _nest_marca_superart_articulo(filas)
        self.assertEqual(len(arbol), 1)
        self.assertEqual(arbol[0]["nombre_marca"], NOMBRE_MARCA_AJUSTES)
        self.assertEqual(arbol[0]["facturacion"], -150.0)
        self.assertEqual(arbol[0]["packs"], 0.0)
        sa = arbol[0]["children"][0]
        self.assertEqual(sa["nombre_superart"], NOMBRE_SUPERART_AJUSTES)
        self.assertEqual(len(sa["children"]), 2)


class VentasMarcaSuperartExportTests(SimpleTestCase):
    def test_export_headers(self):
        r = ReportDefinition(slug="ventas-marca-superart", config={})
        row = {
            "codigo_marca": 1,
            "nombre_marca": "Marca",
            "id_manual": "SA",
            "nombre_superart": "SA",
            "id_art": 10,
            "nombre_articulo": "Art",
            "packs": 3.0,
            "docenas": 0.25,
            "facturacion": 99.0,
        }
        svc = ExportService(Mock())
        h = svc._resolve_export_headers(r, row)
        self.assertEqual(
            h,
            [
                "nombre_marca",
                "nombre_superart",
                "nombre_articulo",
                "packs",
                "docenas",
                "facturacion",
            ],
        )

    def test_export_filename(self):
        svc = ExportService(Mock())
        name = svc._resolve_export_filename(
            "ventas-marca-superart",
            {"filters": {"fecha_inicio_facturacion": "2026-01-01", "fecha_fin_facturacion": "2026-01-31"}},
            "20260101",
        )
        self.assertEqual(name, "Ventas_marca_superart_2026-01-01_2026-01-31.xlsx")


class VentasMarcaSuperartPostPieRunnerTest(SimpleTestCase):
    """Runner SuperArt usa importe post-pie (paridad VMM)."""

    def _run_with_mock_rows(self, rows, ajuste_rows=None, marcas_incluidos=None):
        report = ReportDefinition(
            slug="ventas-marca-superart",
            name="Ventas por marca y SuperArt",
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
        captured = {"sqls": []}
        ajuste_rows = list(ajuste_rows or [])
        marcas_resueltas = list(marcas_incluidos or [])

        cursor = Mock()

        def fake_execute(sql, params=None):
            captured["sql"] = sql
            captured["sqls"].append(sql)
            captured["params"] = list(params or [])
            if "NOT EXISTS" in (sql or ""):
                cursor.description = [
                    ("codigo_cliente",),
                    ("nombre_cliente",),
                    ("facturacion",),
                ]
                cursor.fetchall.return_value = ajuste_rows
            else:
                cursor.description = [
                    ("codigo_marca",),
                    ("nombre_marca",),
                    ("id_manual",),
                    ("id_art",),
                    ("nombre_articulo",),
                    ("packs",),
                    ("docenas",),
                    ("facturacion",),
                ]
                cursor.fetchall.return_value = rows

        cursor.execute = fake_execute
        cursor.fetchall.return_value = rows
        cursor.description = [
            ("codigo_marca",),
            ("nombre_marca",),
            ("id_manual",),
            ("id_art",),
            ("nombre_articulo",),
            ("packs",),
            ("docenas",),
            ("facturacion",),
        ]
        conn = Mock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__.return_value = conn

        patches = [
            patch(
                "reports.services.ventas_marca_superart_runner.ctx_desde_runner",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marca_superart_runner.alcance_objetivos_cod_viajante",
                return_value=None,
            ),
            patch(
                "reports.services.ventas_marca_superart_runner.get_mysql_pool",
                return_value=pool,
            ),
            patch(
                "reports.services.ventas_marca_superart_runner._resolve_marcas_incluidos",
                return_value=marcas_resueltas,
            ),
        ]

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = run_ventas_marca_superart(report, payload, Mock())

        return result, captured

    def test_sql_emitido_usa_expr_post_pie(self):
        row = (1, "Marca A", "SA1", 10, "Art A", 10.0, 10.0, 800.0)
        _, captured = self._run_with_mock_rows([row])
        sql_renglon = next((s for s in captured.get("sqls") or [] if "PrecioNetoxR" in s), "")
        self.assertIn("SubTotal1", sql_renglon)
        self.assertIn("SubtotalDesc", sql_renglon)
        self.assertIn("0.0001", sql_renglon)
        self.assertIn("PrecioNetoxR", sql_renglon)

    def test_totales_facturacion_post_pie(self):
        row = (1, "Marca A", "SA1", 10, "Art A", 12.0, 1.0, 800.0)
        result, _ = self._run_with_mock_rows([row])
        self.assertAlmostEqual(result.totals.get("facturacion"), 800.0, places=2)
        self.assertAlmostEqual(result.totals.get("packs"), 12.0, places=2)

    def test_totales_incluyen_ajustes_sin_mercaderia(self):
        row = (1, "Marca A", "SA1", 10, "Art A", 12.0, 1.0, 800.0)
        ajuste = (99, "Cliente X", -100.0)
        result, captured = self._run_with_mock_rows([row], ajuste_rows=[ajuste])
        self.assertTrue(any("NOT EXISTS" in (s or "") for s in captured.get("sqls") or []))
        self.assertAlmostEqual(result.totals.get("facturacion"), 700.0, places=2)
        self.assertAlmostEqual(result.totals.get("packs"), 12.0, places=2)
        marcas = result.meta["extra"]["tabs"]["marca_superart_jerarquia"]
        self.assertEqual(marcas[-1]["nombre_marca"], NOMBRE_MARCA_AJUSTES)
        self.assertTrue(marcas[-1]["es_ajuste_cabecera"])
        self.assertEqual(marcas[-1]["children"][0]["nombre_superart"], NOMBRE_SUPERART_AJUSTES)
        self.assertEqual(marcas[-1]["children"][0]["children"][0]["nombre_articulo"], "Cliente X")
        self.assertTrue(any("Ventas Netas" in n for n in result.notes))

    def test_no_incluye_ajustes_si_filtro_marca(self):
        row = (1, "Marca A", "SA1", 10, "Art A", 12.0, 1.0, 800.0)
        ajuste = (99, "Cliente X", -100.0)
        result, captured = self._run_with_mock_rows(
            [row],
            ajuste_rows=[ajuste],
            marcas_incluidos=[1],
        )
        self.assertFalse(any("NOT EXISTS" in (s or "") for s in captured.get("sqls") or []))
        self.assertAlmostEqual(result.totals.get("facturacion"), 800.0, places=2)
        self.assertTrue(any("filtros de catálogo" in n.lower() for n in result.notes))
