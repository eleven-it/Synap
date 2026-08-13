"""Tests TDD servicio kardex artículo MPR (OPP/OPA movimiento_stock)."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.reportes_hub import CSV_COLUMNAS, GRUPOS_REPORTES, PARTIALS
from mpr.services_kardex_articulo import (
    _calcular_saldo_corrido_movimientos,
    _clasificar_movimiento_kardex,
    construir_kardex_articulo,
)


class TestClasificarMovimientoKardex(SimpleTestCase):
    """Task 1.1 — clasificación OPP/OPA/legacy/ignorar."""

    def test_opp_es_entrada(self):
        self.assertEqual(_clasificar_movimiento_kardex("OPP", ""), "entrada")

    def test_opa_es_salida(self):
        self.assertEqual(_clasificar_movimiento_kardex("OPA", ""), "salida")

    def test_armado_es_salida(self):
        self.assertEqual(_clasificar_movimiento_kardex("ARMADO", ""), "salida")

    def test_legacy_parte_produccion_es_entrada(self):
        self.assertEqual(
            _clasificar_movimiento_kardex("X", "Parte producción"),
            "entrada",
        )

    def test_opt_se_ignora(self):
        self.assertEqual(_clasificar_movimiento_kardex("OPT", "Pedido producción"), "ignorar")

    def test_tipo_desconocido_se_ignora(self):
        self.assertEqual(_clasificar_movimiento_kardex("RECLASIFICACION", ""), "ignorar")


def _fake_mysql_cursor_factory(fetchall_rows=None, fetchone_row=None):
    """Context manager mock para mysql_cursor."""
    rows = fetchall_rows if fetchall_rows is not None else []
    one = fetchone_row if fetchone_row is not None else (rows[0] if rows else None)

    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = one

    @contextmanager
    def _ctx(*_args, **_kwargs):
        yield cursor

    return _ctx, cursor


class TestConstruirKardexArticuloSaldoCorrido(SimpleTestCase):
    """Task 1.3 — saldo corrido OPP/OPA y período vacío."""

    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Semi")
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={615: ("907944-02", "Pack prueba")},
    )
    @patch("mpr.services_kardex_articulo.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_saldo_corrido_opp_opa_orden_asc(
        self,
        mock_nombre_tabla,
        mock_mysql,
        *_mocks,
    ):
        mock_nombre_tabla.side_effect = lambda _c, n: n

        mov_rows = [
            {
                "codigo_movimiento": 100,
                "fecha": date(2026, 8, 1),
                "tipo_mov": "OPP",
                "motivo_movimiento": "Parte producción",
                "nro_comprobante": "0001-00000100",
                "detalle": "Entrada semi",
                "id_operario_opt": 5,
                "total_entrada": 100,
                "total_salida": 0,
            },
            {
                "codigo_movimiento": 101,
                "fecha": date(2026, 8, 2),
                "tipo_mov": "OPA",
                "motivo_movimiento": "Armado",
                "nro_comprobante": "0001-00000101",
                "detalle": "Salida armado",
                "id_operario_opt": 6,
                "total_entrada": 0,
                "total_salida": 30,
            },
        ]
        ctx, _cursor = _fake_mysql_cursor_factory(mov_rows)
        mock_mysql.side_effect = ctx

        resultado = construir_kardex_articulo(
            "empresa92",
            615,
            id_deposito=3,
            fecha_desde="2026-08-01",
            fecha_hasta="2026-08-31",
        )

        movs = resultado["movimientos"]
        self.assertEqual(len(movs), 2)
        self.assertEqual(movs[0]["entrada"], 100)
        self.assertEqual(movs[0]["salida"], 0)
        self.assertEqual(movs[0]["saldo_corrido"], 100)
        self.assertEqual(movs[1]["entrada"], 0)
        self.assertEqual(movs[1]["salida"], 30)
        self.assertEqual(movs[1]["saldo_corrido"], 70)
        self.assertEqual(resultado["kpis"]["saldo_final"], 70)
        self.assertEqual(resultado["kpis"]["total_entradas"], 100)
        self.assertEqual(resultado["kpis"]["total_salidas"], 30)
        self.assertEqual(movs[0]["fecha_display"], "01/08/2026")
        self.assertEqual(movs[1]["fecha_display"], "02/08/2026")

    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={615: ("907944-02", "Pack prueba")},
    )
    @patch(
        "mpr.services_kardex_articulo._consultar_movimientos_kardex_articulo",
        return_value=[],
    )
    def test_sin_movimientos_saldo_final_cero(self, *_mocks):
        resultado = construir_kardex_articulo(
            "empresa92",
            615,
            id_deposito=3,
            fecha_desde="2026-08-01",
            fecha_hasta="2026-08-31",
        )
        self.assertEqual(resultado["movimientos"], [])
        self.assertEqual(resultado["kpis"]["saldo_final"], 0)
        self.assertEqual(resultado["kpis"]["total_entradas"], 0)
        self.assertEqual(resultado["kpis"]["total_salidas"], 0)


class TestCalcularSaldoCorridoMovimientos(SimpleTestCase):
    def test_acumula_desde_cero(self):
        base = [
            {"entrada": 50, "salida": 0},
            {"entrada": 0, "salida": 20},
        ]
        out = _calcular_saldo_corrido_movimientos(base)
        self.assertEqual(out[0]["saldo_corrido"], 50)
        self.assertEqual(out[1]["saldo_corrido"], 30)


class TestKardexPack90794402Semi(SimpleTestCase):
    """Task 1.5 — aceptación pack 907944-02 Semi BOM qty 2."""

    BOM_24 = {
        "cabecera": {"id_en_abm": 24, "nombre_en_abm": "Pack 907944-02"},
        "componentes": [
            {
                "id_articulo": 963,
                "codigo_articulo": "COMP-963",
                "descripcion_articulo": "Componente 963",
                "cantidad_articulo": 2.0,
            },
        ],
    }

    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=45)
    @patch("mpr.services.get_bom_detalle")
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=24)
    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Semi")
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={615: ("907944-02", "Pack 907944-02")},
    )
    @patch("mpr.services_kardex_articulo.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_pack_907944_02_semi_bom_qty_2_max_packs(
        self,
        mock_nombre_tabla,
        mock_mysql,
        _mock_fetch_desc,
        _mock_fetch_dep,
        _mock_id_abm,
        mock_bom,
        mock_max_packs,
    ):
        mock_nombre_tabla.side_effect = lambda _c, n: n
        mock_bom.return_value = self.BOM_24

        mov_rows = [
            {
                "codigo_movimiento": 200,
                "fecha": date(2026, 8, 5),
                "tipo_mov": "OPP",
                "motivo_movimiento": "Parte producción",
                "nro_comprobante": "0001-00000200",
                "detalle": "OPP pack",
                "id_operario_opt": None,
                "total_entrada": 100,
                "total_salida": 0,
            },
            {
                "codigo_movimiento": 201,
                "fecha": date(2026, 8, 6),
                "tipo_mov": "OPA",
                "motivo_movimiento": "Armado",
                "nro_comprobante": "0001-00000201",
                "detalle": "OPA pack",
                "id_operario_opt": None,
                "total_entrada": 0,
                "total_salida": 10,
            },
        ]
        ctx, _cursor = _fake_mysql_cursor_factory(mov_rows)
        mock_mysql.side_effect = ctx

        resultado = construir_kardex_articulo(
            "empresa92",
            615,
            id_deposito=3,
            fecha_desde="2026-08-01",
            fecha_hasta="2026-08-31",
        )

        saldo_final = resultado["kpis"]["saldo_final"]
        self.assertEqual(saldo_final, 90)
        self.assertEqual(resultado["kpis"]["total_entradas"], 100)
        self.assertEqual(resultado["kpis"]["total_salidas"], 10)
        self.assertTrue(resultado["articulo"]["es_pack"])
        self.assertEqual(resultado["articulo"]["id_en_abm"], 24)
        self.assertIsNotNone(resultado["bom"])
        self.assertEqual(resultado["bom"]["cabecera"]["id_en_abm"], 24)

        expected_max = saldo_final // 2
        mock_max_packs.assert_called_once_with("empresa92", 615, deposito_semi=3)
        self.assertEqual(resultado["kpis"]["max_packs"], 45)
        self.assertEqual(expected_max, 45)

        with patch("mpr.services.calcular_max_packs_armado_1ra", return_value=expected_max):
            r2 = construir_kardex_articulo(
                "empresa92",
                615,
                id_deposito=3,
                fecha_desde="2026-08-01",
                fecha_hasta="2026-08-31",
            )
        self.assertEqual(r2["kpis"]["max_packs"], expected_max)
        self.assertEqual(expected_max, 90 // 2)


class TestKardexHubRegistro(SimpleTestCase):
    """Task 1.7 — registro en hub trazabilidad."""

    def test_kardex_articulo_en_grupo_trazabilidad(self):
        reportes = GRUPOS_REPORTES["trazabilidad"]["reportes"]
        self.assertIn("kardex_articulo", reportes)
        self.assertEqual(reportes["kardex_articulo"], "Kardex artículo")

    def test_partial_y_csv_kardex(self):
        self.assertEqual(
            PARTIALS[("trazabilidad", "kardex_articulo")],
            "mpr/reportes/partials/kardex_articulo.html",
        )
        cols = CSV_COLUMNAS[("trazabilidad", "kardex_articulo")]
        claves = [c[0] for c in cols]
        self.assertIn("fecha_display", claves)
        self.assertIn("saldo_corrido", claves)


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


class TestReportesKardexArticuloView(SimpleTestCase):
    """Task 1.8 — vista ReportesMPRView kardex: permisos, contexto, CSV."""

    def setUp(self):
        from django.test import RequestFactory

        self.factory = RequestFactory()

    def _get_context(self, params, kardex_payload=None, depositos=None):
        from mpr.views import ReportesMPRView

        view = ReportesMPRView()
        request = self.factory.get("/mpr/reportes/", params)
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.reportes")
        view.request = request
        depositos = depositos if depositos is not None else [
            {"CodDeposito": 3, "NombreDeposito": "Semi", "tipo_mpr": "semi"},
        ]
        kardex_payload = kardex_payload or {
            "articulo": {"id": 615, "codigo": "907944-02", "descripcion": "Pack", "es_pack": True},
            "bom": None,
            "deposito": {"id": 3, "nombre": "Semi"},
            "movimientos": [
                {
                    "fecha_display": "01/08/2026",
                    "tipo_mov": "OPP",
                    "entrada": 10,
                    "salida": 0,
                    "saldo_corrido": 10,
                    "codigo_movimiento": 100,
                    "nro_comprobante": "0001-00000100",
                    "detalle": "Entrada",
                    "operario": "-",
                },
            ],
            "kpis": {"saldo_final": 10, "total_entradas": 10, "total_salidas": 0, "max_packs": 5},
            "advertencias": [],
        }
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.listar_depositos_config", return_value=depositos):
                with patch("mpr.services.construir_kardex_articulo", return_value=kardex_payload):
                    with patch("mpr.views._build_renglones_modal_map", return_value={"100": {"articulos": []}}):
                        return view.get_context_data()

    def test_contexto_incluye_depositos_y_kardex(self):
        ctx = self._get_context(
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "id_articulo": "615",
                "id_deposito": "3",
                "desde": "2026-08-01",
                "hasta": "2026-08-31",
            }
        )
        self.assertEqual(ctx["grupo"], "trazabilidad")
        self.assertEqual(ctx["reporte"], "kardex_articulo")
        self.assertEqual(len(ctx["depositos"]), 1)
        self.assertEqual(ctx["meta"]["id_articulo"], 615)
        self.assertEqual(ctx["meta"]["id_deposito"], 3)
        self.assertEqual(ctx["kpis"]["saldo_final"], 10)
        self.assertEqual(len(ctx["filas"]), 1)

    def test_sin_articulo_no_invoca_servicio(self):
        from mpr.views import ReportesMPRView

        view = ReportesMPRView()
        request = self.factory.get(
            "/mpr/reportes/",
            {"grupo": "trazabilidad", "reporte": "kardex_articulo"},
        )
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.ver")
        view.request = request
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.listar_depositos_config", return_value=[]):
                with patch("mpr.services.construir_kardex_articulo") as mock_svc:
                    ctx = view.get_context_data()
        mock_svc.assert_not_called()
        self.assertIsNone(ctx["meta"]["id_articulo"])

    def test_articulo_inexistente_sin_datos_parciales(self):
        ctx = self._get_context(
            {"grupo": "trazabilidad", "reporte": "kardex_articulo", "id_articulo": "99999"},
            kardex_payload={
                "articulo": None,
                "bom": None,
                "deposito": None,
                "movimientos": [],
                "kpis": {"saldo_final": 0, "total_entradas": 0, "total_salidas": 0, "max_packs": 0},
                "advertencias": ["Artículo inexistente o sin datos en la base."],
            },
        )
        self.assertIsNone(ctx["meta"]["articulo"])
        self.assertIn("inexistente", ctx["meta"]["advertencias"][0].lower())
        self.assertEqual(ctx["filas"], [])

    def test_permiso_reportes_200(self):
        from django.http import HttpResponse
        from django.urls import reverse

        from mpr.views import ReportesMPRView

        request = self.factory.get(
            reverse("mpr:reportes"),
            {"grupo": "trazabilidad", "reporte": "kardex_articulo"},
        )
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.reportes")
        with patch.object(ReportesMPRView, "get", return_value=HttpResponse("ok")):
            response = ReportesMPRView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_export_csv_kardex_columnas(self):
        from mpr.views import ReportesMPRView

        request = self.factory.get(
            "/mpr/reportes/",
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "id_articulo": "615",
                "desde": "2026-08-01",
                "hasta": "2026-08-31",
                "format": "csv",
            },
        )
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.ver")
        kardex_payload = {
            "articulo": {"id": 615, "codigo": "907944-02", "descripcion": "Pack", "es_pack": True},
            "bom": None,
            "deposito": None,
            "movimientos": [
                {
                    "fecha_display": "01/08/2026",
                    "tipo_mov": "OPP",
                    "nro_comprobante": "0001-00000100",
                    "detalle": "Entrada",
                    "entrada": 10,
                    "salida": 0,
                    "saldo_corrido": 10,
                    "operario": "-",
                },
            ],
            "kpis": {"saldo_final": 10, "total_entradas": 10, "total_salidas": 0, "max_packs": 0},
            "advertencias": [],
        }
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.listar_depositos_config", return_value=[]):
                with patch("mpr.services.construir_kardex_articulo", return_value=kardex_payload):
                    with patch("mpr.views._build_renglones_modal_map", return_value={}):
                        response = ReportesMPRView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        body = response.content.decode("utf-8-sig")
        self.assertIn("Saldo corrido", body)
        self.assertIn("01/08/2026", body)
        self.assertIn("10", body)


class TestKardexArticuloUIRender(SimpleTestCase):
    """Cierra gaps verify: empty states, modal markup, KPI strip y canon UI."""

    def _base_ctx(self, **overrides):
        ctx = {
            "meta": {
                "id_articulo": None,
                "id_deposito": None,
                "articulo": None,
                "deposito": None,
                "bom": None,
                "advertencias": [],
            },
            "filas": [],
            "depositos": [
                {"CodDeposito": 3, "NombreDeposito": "Semi", "tipo_mpr": "semi"},
            ],
            "fecha_desde_iso": "2026-08-01",
            "fecha_hasta_iso": "2026-08-31",
            "fecha_desde_display": "01/08/2026",
            "fecha_hasta_display": "31/08/2026",
            "modo_presentacion": "docenas",
            "renglones_por_movimiento": {},
            "grupo": "trazabilidad",
            "reporte": "kardex_articulo",
            "kpis": {},
        }
        ctx.update(overrides)
        return ctx

    def _render_partial(self, context):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        request = RequestFactory().get("/mpr/reportes/")
        return render_to_string(
            "mpr/reportes/partials/kardex_articulo.html",
            context,
            request=request,
        )

    def test_empty_state_sin_articulo_render(self):
        html = self._render_partial(self._base_ctx())
        self.assertIn("Seleccioná un artículo para ver el kardex OPP/OPA del período", html)
        self.assertNotIn("js-comprobante-modal-trigger", html)
        self.assertNotIn("Saldo corrido", html)

    def test_empty_state_sin_movimientos_render(self):
        html = self._render_partial(
            self._base_ctx(
                meta={
                    "id_articulo": 615,
                    "id_deposito": 3,
                    "articulo": {
                        "id": 615,
                        "codigo": "907944-02",
                        "descripcion": "Pack test",
                        "es_pack": True,
                    },
                    "deposito": {"id": 3, "nombre": "Semi"},
                    "bom": None,
                    "advertencias": [],
                },
                filas=[],
            )
        )
        self.assertIn("Sin movimientos OPP/OPA en el período para este artículo", html)
        self.assertIn("Ver tablero de producción", html)
        self.assertNotIn("js-comprobante-modal-trigger", html)

    def test_tabla_incluye_trigger_modal_y_partial(self):
        html = self._render_partial(
            self._base_ctx(
                meta={
                    "id_articulo": 615,
                    "id_deposito": 3,
                    "articulo": {
                        "id": 615,
                        "codigo": "907944-02",
                        "descripcion": "Pack test",
                        "es_pack": True,
                    },
                    "deposito": {"id": 3, "nombre": "Semi"},
                    "bom": {
                        "componentes": [
                            {
                                "id_articulo": 963,
                                "codigo_articulo": "COMP-963",
                                "descripcion_articulo": "Componente Semi",
                                "cantidad_articulo": 2,
                            }
                        ]
                    },
                    "advertencias": [],
                },
                filas=[
                    {
                        "fecha_display": "01/08/2026",
                        "tipo_mov": "OPP",
                        "entrada": 10,
                        "salida": 0,
                        "saldo_corrido": 10,
                        "codigo_movimiento": 100,
                        "nro_comprobante": "0001-00000100",
                        "detalle": "Entrada",
                        "operario": "-",
                    }
                ],
                renglones_por_movimiento={
                    "100": {
                        "articulos": [
                            {
                                "codigo_articulo": "907944-02",
                                "descripcion": "Pack test",
                                "filas": [
                                    {
                                        "nombre_deposito": "Semi",
                                        "entrada": 10,
                                        "salida": 0,
                                        "saldo": 10,
                                    }
                                ],
                            }
                        ]
                    }
                },
            )
        )
        self.assertIn("js-comprobante-modal-trigger", html)
        self.assertIn('data-codigo-movimiento="100"', html)
        self.assertIn('id="renglones-por-movimiento-data"', html)
        self.assertIn('id="modal-comprobante-movimiento"', html)
        self.assertIn("modal_comprobante_movimiento.js", html)
        self.assertIn("sticky top-0", html)
        self.assertIn("Saldo corrido", html)
        self.assertIn("Lista de materiales (BOM)", html)
        self.assertIn("reporte=timeline", html)
        self.assertIn("id_articulo=963", html)
        self.assertNotIn("alert(", html)
        self.assertNotIn("window.confirm", html)

    def test_kpi_strip_kardex_saldo_y_max_packs(self):
        from django.template.loader import render_to_string

        html = render_to_string(
            "mpr/reportes/_kpi_strip.html",
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "kpis": {"saldo_final": 90, "max_packs": 45},
                "filas": [{"x": 1}, {"x": 2}],
            },
        )
        self.assertIn("Saldo final", html)
        self.assertIn("90", html)
        self.assertIn("Max packs", html)
        self.assertIn("45", html)
        self.assertIn("Movimientos", html)

    def test_contexto_vista_expone_renglones_modal_para_ui(self):
        """La vista debe pasar renglones_por_movimiento cuando hay movimientos."""
        from mpr.views import ReportesMPRView
        from django.test import RequestFactory

        view = ReportesMPRView()
        request = RequestFactory().get(
            "/mpr/reportes/",
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "id_articulo": "615",
                "id_deposito": "3",
                "desde": "2026-08-01",
                "hasta": "2026-08-31",
            },
        )
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.reportes")
        view.request = request
        kardex_payload = {
            "articulo": {"id": 615, "codigo": "907944-02", "descripcion": "Pack", "es_pack": True},
            "bom": None,
            "deposito": {"id": 3, "nombre": "Semi"},
            "movimientos": [
                {
                    "fecha_display": "01/08/2026",
                    "tipo_mov": "OPP",
                    "entrada": 10,
                    "salida": 0,
                    "saldo_corrido": 10,
                    "codigo_movimiento": 100,
                    "nro_comprobante": "0001-00000100",
                    "detalle": "Entrada",
                    "operario": "-",
                },
            ],
            "kpis": {"saldo_final": 10, "total_entradas": 10, "total_salidas": 0, "max_packs": 5},
            "advertencias": [],
        }
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch("mpr.views.listar_depositos_config", return_value=[]):
                with patch("mpr.services.construir_kardex_articulo", return_value=kardex_payload):
                    with patch(
                        "mpr.views._build_renglones_modal_map",
                        return_value={"100": {"articulos": [{"codigo_articulo": "907944-02", "filas": []}]}},
                    ):
                        ctx = view.get_context_data()
        self.assertIn("100", ctx["renglones_por_movimiento"])
        self.assertEqual(ctx["kpis"]["saldo_final"], 10)
        self.assertEqual(ctx["kpis"]["max_packs"], 5)

    def test_modal_js_abre_pinta_renglones_y_cierra(self):
        import subprocess
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        script = root / "mpr" / "tests" / "js" / "test_modal_comprobante_movimiento.mjs"
        result = subprocess.run(
            ["node", str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stderr={result.stderr}\nstdout={result.stdout}",
        )
        self.assertIn("OK modal_comprobante_movimiento", result.stdout)
