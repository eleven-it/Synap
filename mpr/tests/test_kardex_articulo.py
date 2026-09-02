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


def _movimientos_kardex_normalizados(mov_rows):
    """Filas normalizadas para mock de _recolectar_movimientos_analisis."""
    from mpr.services_kardex_articulo import _normalizar_fila_analisis_mstock

    out = []
    for row in mov_rows:
        fila = _normalizar_fila_analisis_mstock(row)
        if fila:
            out.append(fila)
    return out


def _side_effect_recolectar(mov_rows):
    """Evita doble conteo cuando mysql_cursor mock no filtra por fecha."""

    def _recolectar(_base, _art, **kwargs):
        if kwargs.get("solo_pre_periodo"):
            return []
        return _movimientos_kardex_normalizados(mov_rows)

    return _recolectar


class TestConstruirKardexArticuloSaldoCorrido(SimpleTestCase):
    """Task 1.3 — saldo corrido OPP/OPA y período vacío."""

    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=0)
    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Semi")
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={615: ("907944-02", "Pack prueba")},
    )
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis")
    @patch("mpr.services_kardex_articulo.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_saldo_corrido_opp_opa_orden_asc(
        self,
        mock_nombre_tabla,
        mock_mysql,
        mock_recolectar,
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
        mock_recolectar.side_effect = _side_effect_recolectar(mov_rows)
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

    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=0)
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=None)
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={615: ("907944-02", "Pack prueba")},
    )
    @patch(
        "mpr.services_kardex_articulo._recolectar_movimientos_analisis",
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

    @patch("mpr.services_kardex_articulo._consultar_eventos_mpr_articulo", return_value=[])
    @patch("mpr.services.listar_demanda_ped_por_articulo", return_value=[])
    @patch("mpr.services_kardex_articulo._fetch_stock_reserva_articulo", return_value=0)
    @patch("mpr.services_kardex_articulo._fetch_stock_terminado_analisis", return_value=0)
    @patch("mpr.services.calcular_max_packs_armado_1ra", return_value=45)
    @patch("mpr.services.get_bom_detalle")
    @patch("mpr.services.get_id_en_abm_por_articulo", return_value=24)
    @patch("mpr.services_kardex_articulo._fetch_nombre_deposito", return_value="Semi")
    @patch(
        "mpr.services._fetch_descripciones_articulo",
        return_value={615: ("907944-02", "Pack 907944-02")},
    )
    @patch("mpr.services_kardex_articulo._recolectar_movimientos_analisis")
    @patch("mpr.services_kardex_articulo.mysql_cursor")
    @patch("mpr.services._nombre_tabla")
    def test_pack_907944_02_semi_bom_qty_2_max_packs(
        self,
        mock_nombre_tabla,
        mock_mysql,
        mock_recolectar,
        _mock_fetch_desc,
        _mock_fetch_dep,
        _mock_id_abm,
        mock_bom,
        mock_max_packs,
        *_mocks,
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
        mock_recolectar.side_effect = _side_effect_recolectar(mov_rows)
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

        mock_recolectar.side_effect = _side_effect_recolectar(mov_rows)
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


class TestConstruirKardexWrapperCompat(SimpleTestCase):
    """Task 1.13 — wrapper delgado mantiene contrato legacy."""

    @patch("mpr.services_kardex_articulo.construir_analisis_trazabilidad_articulo")
    def test_wrapper_proyecta_payload_sin_bloques_extra(self, mock_analisis):
        mock_analisis.return_value = {
            "articulo": {"id": 615, "codigo": "610", "descripcion": "Pack", "es_pack": True},
            "bom": {"cabecera": {"id_en_abm": 1}, "componentes": []},
            "deposito": {"id": 3, "nombre": "Semi"},
            "movimientos": [
                {
                    "fecha_display": "01/08/2026",
                    "tipo_mov": "OPP",
                    "entrada": 10,
                    "salida": 0,
                    "saldo_corrido": 10,
                    "codigo_movimiento": 1,
                    "nro_comprobante": "X",
                    "detalle": "",
                    "operario": "-",
                    "clase_ui": "opp",
                    "afecta_deposito": True,
                }
            ],
            "kpis": {
                "saldo_final": 10,
                "total_entradas": 10,
                "total_salidas": 0,
                "max_packs": 5,
                "pedido": 0,
            },
            "demanda_ped": {"filas": [], "totales": {"p_ped": 0}},
            "advertencias": [],
        }
        resultado = construir_kardex_articulo("empresa92", 615, id_deposito=3)
        self.assertNotIn("demanda_ped", resultado)
        self.assertEqual(resultado["kpis"]["saldo_final"], 10)
        self.assertEqual(len(resultado["movimientos"]), 1)
        self.assertNotIn("clase_ui", resultado["movimientos"][0])
        mock_analisis.assert_called_once()


class TestKardexHubRegistro(SimpleTestCase):
    """Task 1.7 — registro en hub trazabilidad."""

    def test_kardex_articulo_en_grupo_trazabilidad(self):
        reportes = GRUPOS_REPORTES["trazabilidad"]["reportes"]
        self.assertEqual(list(reportes.keys()), ["kardex_articulo"])
        self.assertEqual(reportes["kardex_articulo"], "Análisis trazabilidad")
        self.assertNotIn("timeline", reportes)
        self.assertNotIn("movimientos", reportes)
        self.assertNotIn("conciliacion", reportes)

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


def _payload_analisis_completo(**overrides):
    """Payload mínimo construir_analisis_trazabilidad_articulo para tests vista/UI."""
    payload = {
        "articulo": {
            "id": 615,
            "codigo": "907944-02",
            "descripcion": "Pack prueba",
            "es_pack": True,
            "id_en_abm": 24,
        },
        "demanda_ped": {
            "filas": [
                {
                    "nro_pedido": "0001-00012345",
                    "nombre_cliente": "Cliente Test",
                    "fecha": "01/07/2026",
                    "cantidad_pendiente_prod": 100,
                }
            ],
            "totales": {"p_ped": 100},
        },
        "stock": {"terminado": -20, "semi_componentes": [], "negativo": True},
        "brechas": {
            "ped_urgente": 120,
            "tot_urgente": 150,
            "reserva": 30,
            "texto_explicativo": "PED Urgente incluye |Terminado| negativo.",
        },
        "a_producir": {
            "cantidad": 150,
            "capacidad_semi": 0,
            "alerta_semi_cero": True,
        },
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
                "clase_ui": "opp",
                "afecta_deposito": True,
            },
        ],
        "eventos_mpr": [],
        "kpis": {
            "pedido": 100,
            "terminado": -20,
            "ped_urgente": 120,
            "tot_urgente": 150,
            "saldo_final": 10,
            "total_entradas": 10,
            "total_salidas": 0,
            "max_packs": 5,
        },
        "saldo_inicial": {"valor": 0, "calculado_ok": True},
        "advertencias": [],
    }
    payload.update(overrides)
    return payload


class TestReportesKardexArticuloView(SimpleTestCase):
    """Task 1.8 / 2.1 — vista ReportesMPRView kardex: permisos, contexto, CSV."""

    def setUp(self):
        from django.test import RequestFactory

        self.factory = RequestFactory()

    def _get_context(self, params, analisis_payload=None):
        from mpr.views import ReportesMPRView

        view = ReportesMPRView()
        request = self.factory.get("/mpr/reportes/", params)
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.reportes")
        view.request = request
        analisis_payload = analisis_payload or _payload_analisis_completo()
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch(
                "mpr.services_kardex_articulo.construir_analisis_trazabilidad_articulo",
                return_value=analisis_payload,
            ) as mock_svc:
                with patch("mpr.views._build_renglones_modal_map", return_value={"100": {"articulos": []}}):
                    ctx = view.get_context_data()
        ctx["_mock_svc"] = mock_svc
        return ctx

    def test_contexto_kardex_deposito_automatico(self):
        ctx = self._get_context(
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "id_articulo": "615",
                "desde": "2026-08-01",
                "hasta": "2026-08-31",
            }
        )
        self.assertEqual(ctx["grupo"], "trazabilidad")
        self.assertEqual(ctx["reporte"], "kardex_articulo")
        self.assertNotIn("depositos", ctx)
        self.assertEqual(ctx["meta"]["id_articulo"], 615)
        self.assertEqual(ctx["meta"]["id_deposito"], 3)
        self.assertEqual(ctx["kpis"]["saldo_final"], 10)
        self.assertEqual(len(ctx["filas"]), 1)
        mock_svc = ctx.pop("_mock_svc")
        mock_svc.assert_called_once()
        self.assertNotIn("id_deposito", mock_svc.call_args.kwargs)

    def test_contexto_incluye_bloques_analisis_completo(self):
        """Task 2.1 — payload análisis expuesto en meta y kpis (REQ-ANAL-01/13)."""
        ctx = self._get_context(
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "id_articulo": "615",
                "desde": "2026-07-01",
                "hasta": "2026-09-01",
            }
        )
        meta = ctx["meta"]
        self.assertIn("demanda_ped", meta)
        self.assertIn("stock", meta)
        self.assertIn("brechas", meta)
        self.assertIn("a_producir", meta)
        self.assertIn("saldo_inicial", meta)
        self.assertEqual(meta["demanda_ped"]["totales"]["p_ped"], 100)
        self.assertEqual(meta["stock"]["terminado"], -20)
        self.assertTrue(meta["stock"]["negativo"])
        self.assertEqual(meta["brechas"]["ped_urgente"], 120)
        self.assertEqual(len(ctx["filas"]), 1)
        self.assertEqual(ctx["filas"][0]["clase_ui"], "opp")
        kpis = ctx["kpis"]
        self.assertEqual(kpis["pedido"], 100)
        self.assertEqual(kpis["terminado"], -20)
        self.assertEqual(kpis["ped_urgente"], 120)
        self.assertEqual(kpis["tot_urgente"], 150)

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
            with patch(
                "mpr.services_kardex_articulo.construir_analisis_trazabilidad_articulo"
            ) as mock_svc:
                ctx = view.get_context_data()
        mock_svc.assert_not_called()
        self.assertIsNone(ctx["meta"]["id_articulo"])

    def test_articulo_inexistente_sin_datos_parciales(self):
        ctx = self._get_context(
            {"grupo": "trazabilidad", "reporte": "kardex_articulo", "id_articulo": "99999"},
            analisis_payload=_payload_analisis_completo(
                articulo=None,
                bom=None,
                deposito=None,
                movimientos=[],
                kpis={
                    "pedido": 0,
                    "terminado": 0,
                    "ped_urgente": 0,
                    "tot_urgente": 0,
                    "saldo_final": 0,
                    "total_entradas": 0,
                    "total_salidas": 0,
                    "max_packs": 0,
                },
                advertencias=["Artículo inexistente o sin datos en la base."],
            ),
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
        analisis_payload = _payload_analisis_completo(
            bom=None,
            deposito=None,
            demanda_ped={"filas": [], "totales": {"p_ped": 0}},
            stock={"terminado": 0, "semi_componentes": [], "negativo": False},
            brechas={
                "ped_urgente": 0,
                "tot_urgente": 0,
                "reserva": 0,
                "texto_explicativo": "",
            },
            a_producir={"cantidad": 0, "capacidad_semi": 0, "alerta_semi_cero": False},
            kpis={
                "pedido": 0,
                "terminado": 0,
                "ped_urgente": 0,
                "tot_urgente": 0,
                "saldo_final": 10,
                "total_entradas": 10,
                "total_salidas": 0,
                "max_packs": 0,
            },
        )
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch(
                "mpr.services_kardex_articulo.construir_analisis_trazabilidad_articulo",
                return_value=analisis_payload,
            ):
                with patch("mpr.views._build_renglones_modal_map", return_value={}):
                    response = ReportesMPRView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("analisis_trazabilidad.csv", response["Content-Disposition"])
        body = response.content.decode("utf-8-sig")
        self.assertIn("Análisis trazabilidad artículo", body)
        self.assertIn("DEMANDA PED", body)
        self.assertIn("MOVIMIENTOS", body)
        self.assertIn("Saldo corrido", body)
        self.assertIn("01/08/2026", body)
        self.assertIn("10", body)
        self.assertIn("OPP", body)


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
                "demanda_ped": {"filas": [], "totales": {"p_ped": 0}},
                "stock": {"terminado": 0, "semi_componentes": [], "negativo": False},
                "brechas": {
                    "ped_urgente": 0,
                    "tot_urgente": 0,
                    "reserva": 0,
                    "texto_explicativo": "",
                },
                "a_producir": {
                    "cantidad": 0,
                    "capacidad_semi": 0,
                    "alerta_semi_cero": False,
                },
                "saldo_inicial": {"valor": 0, "calculado_ok": True},
                "eventos_mpr": [],
                "advertencias": [],
            },
            "filas": [],
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
        self.assertIn(
            "Elegí un artículo para reconstruir BOM, demanda viva y movimientos del período",
            html,
        )
        self.assertNotIn("js-comprobante-modal-trigger", html)
        self.assertNotIn(">Saldo<", html)

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
                    "demanda_ped": {"filas": [], "totales": {"p_ped": 0}},
                    "stock": {"terminado": 0, "semi_componentes": [], "negativo": False},
                    "brechas": {
                        "ped_urgente": 0,
                        "tot_urgente": 0,
                        "reserva": 0,
                        "texto_explicativo": "",
                    },
                    "a_producir": {
                        "cantidad": 0,
                        "capacidad_semi": 0,
                        "alerta_semi_cero": False,
                    },
                    "saldo_inicial": {"valor": 0, "calculado_ok": True},
                    "eventos_mpr": [],
                    "advertencias": [],
                },
                filas=[],
            )
        )
        self.assertIn("Sin movimientos que muevan stock en el rango para este artículo", html)
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
                    "demanda_ped": {"filas": [], "totales": {"p_ped": 0}},
                    "stock": {"terminado": 10, "semi_componentes": [], "negativo": False},
                    "brechas": {
                        "ped_urgente": 0,
                        "tot_urgente": 0,
                        "reserva": 0,
                        "texto_explicativo": "",
                    },
                    "a_producir": {
                        "cantidad": 0,
                        "capacidad_semi": 5,
                        "alerta_semi_cero": False,
                    },
                    "saldo_inicial": {"valor": 0, "calculado_ok": True},
                    "eventos_mpr": [],
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
                        "clase_ui": "opp",
                        "afecta_deposito": True,
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
        self.assertIn("mpr-kardex-thead-sticky", html)
        self.assertIn("z-30", html)
        self.assertIn("0_-16px_0_0_", html)
        self.assertIn("border-separate", html)
        self.assertIn("encabezado fijo", html)
        self.assertNotIn("max-h-[min(70vh,42rem)]", html)
        self.assertIn(">Saldo<", html)
        self.assertIn("Lista de materiales (BOM)", html)
        self.assertIn("Demanda de pedidos", html)
        self.assertIn("Movimientos", html)
        self.assertIn("Saldo inicial histórico", html)
        self.assertIn("mpr-post-loading", html)
        self.assertIn("@keydown.arrow-down.prevent", html)
        self.assertIn("focoSugerencia", html)
        self.assertNotIn(">A producir<", html)
        self.assertNotIn('id="traz-sec-producir"', html)
        self.assertNotIn("Afecta depósito", html)
        self.assertIn("reporte=kardex_articulo", html)
        self.assertIn("id_articulo=963", html)
        self.assertNotIn("reporte=timeline", html)
        self.assertNotIn("alert(", html)
        self.assertNotIn("window.confirm", html)
        self.assertNotIn('name="id_deposito"', html)
        self.assertIn("sincronizarPeriodoShell", html)
        self.assertIn('@submit="sincronizarPeriodoShell()"', html)

    def test_kpi_strip_kardex_brecha_pack(self):
        from django.template.loader import render_to_string

        html = render_to_string(
            "mpr/reportes/_kpi_strip.html",
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "kpis": {
                    "pedido": 100,
                    "terminado": -20,
                    "ped_urgente": 120,
                    "tot_urgente": 150,
                    "saldo_final": 90,
                    "max_packs": 45,
                },
                "filas": [{"x": 1}, {"x": 2}],
            },
        )
        self.assertIn("Pedido", html)
        self.assertIn("100", html)
        self.assertIn("Stock", html)
        self.assertIn("-20", html)
        self.assertIn("Movimientos", html)
        self.assertIn(">2<", html)
        self.assertNotIn("PED Urgente", html)
        self.assertNotIn("TOT Urgente", html)
        self.assertNotIn(">Terminado<", html)

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
                "desde": "2026-08-01",
                "hasta": "2026-08-31",
            },
        )
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.reportes")
        view.request = request
        analisis_payload = _payload_analisis_completo(
            bom=None,
            kpis={
                "pedido": 100,
                "terminado": -20,
                "ped_urgente": 120,
                "tot_urgente": 150,
                "saldo_final": 10,
                "total_entradas": 10,
                "total_salidas": 0,
                "max_packs": 5,
            },
        )
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch(
                "mpr.services_kardex_articulo.construir_analisis_trazabilidad_articulo",
                return_value=analisis_payload,
            ):
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
