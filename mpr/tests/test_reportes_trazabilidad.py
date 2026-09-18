"""Tests reporte_mpr_trazabilidad_componente y delegación timeline unificada."""
from unittest.mock import MagicMock, patch

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from mpr.export import analisis_trazabilidad_a_csv
from mpr.services import reporte_mpr_trazabilidad_componente
from mpr.services_kardex_articulo import _normalizar_fila_kardex


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


def _payload_analisis_timeline(**overrides):
    payload = {
        "articulo": {
            "id": 1398,
            "codigo": "610",
            "descripcion": "Pack Mix",
            "es_pack": True,
        },
        "demanda_ped": {
            "filas": [
                {
                    "nro_pedido": "0001-00009999",
                    "nombre_cliente": "Cliente CSV",
                    "fecha": "01/07/2026",
                    "cantidad_pendiente_prod": 50,
                }
            ],
            "totales": {"p_ped": 50},
        },
        "stock": {"terminado": 235, "semi_componentes": [], "negativo": False},
        "brechas": {
            "ped_urgente": 0,
            "tot_urgente": 0,
            "reserva": 0,
            "texto_explicativo": "",
        },
        "a_producir": {
            "cantidad": 0,
            "capacidad_semi": 10,
            "alerta_semi_cero": False,
        },
        "saldo_inicial": {"valor": 100, "calculado_ok": True},
        "movimientos": [
            {
                "fecha_display": "03/08/2026",
                "tipo_mov": "OPA",
                "entrada": 42,
                "salida": 0,
                "saldo_corrido": 142,
                "nro_comprobante": "0001-00003306",
                "detalle": "Armado 1ra MPR",
                "operario": "-",
                "clase_ui": "opa",
                "afecta_deposito": True,
            }
        ],
        "eventos_mpr": [
            {
                "tipo": "opa",
                "tipo_label": "Armado (OPA)",
                "fecha_display": "03/08/2026 10:00",
                "cantidad": 42,
                "detalle": "0001-00003306 — Armado 1ra MPR",
                "operario": "-",
            }
        ],
        "kpis": {
            "pedido": 50,
            "terminado": 235,
            "ped_urgente": 0,
            "tot_urgente": 0,
            "saldo_final": 142,
            "eventos": 1,
        },
        "advertencias": [],
    }
    payload.update(overrides)
    return payload


class TestReporteMprTrazabilidad(SimpleTestCase):
    def test_sin_articulo(self):
        r = reporte_mpr_trazabilidad_componente("empresa92", None)
        self.assertEqual(r["eventos"], [])
        self.assertEqual(r.get("codigo"), "")
        self.assertIsNone(r["id_articulo"])

    @patch("mpr.services._fetch_descripciones_articulo", return_value={1398: ("610", "Pack Mix")})
    @patch("mpr.services.mysql_cursor")
    @patch(
        "mpr.services_kardex_articulo._consultar_movimientos_kardex_articulo",
        return_value=[
            {
                "codigo_movimiento": 1,
                "fecha": "2026-08-03",
                "tipo_mov": "OPA",
                "motivo_movimiento": "Armado",
                "nro_comprobante": "0001-00003306",
                "detalle": "Armado 1ra MPR",
                "id_operario_opt": None,
                "total_entrada": 42,
                "total_salida": 0,
            }
        ],
    )
    def test_incluye_opa_mstock_pack(self, _mock_kardex, mock_cursor, _mock_desc):
        """Packs sin envío/parte MPR igual muestran OPA de armado (REQ-TRAZ-04/05)."""
        cur = mock_cursor.return_value.__enter__.return_value
        cur.fetchall.return_value = []

        r = reporte_mpr_trazabilidad_componente(
            "empresa92", 1398, "2026-07-01", "2026-09-01"
        )
        self.assertEqual(r["id_articulo"], 1398)
        self.assertEqual(len(r["eventos"]), 1)
        ev = r["eventos"][0]
        self.assertEqual(ev["tipo"], "opa")
        self.assertEqual(ev["tipo_label"], "Armado (OPA)")
        self.assertEqual(ev["cantidad"], 42)
        self.assertIn("0001-00003306", ev["detalle"])


class TestNormalizarFilaKardexPack(SimpleTestCase):
    def test_opa_pack_con_entrada_no_queda_en_cero(self):
        fila = _normalizar_fila_kardex(
            {
                "tipo_mov": "OPA",
                "motivo_movimiento": "Armado",
                "total_entrada": 42,
                "total_salida": 0,
                "fecha": "2026-08-03",
                "codigo_movimiento": 10,
                "nro_comprobante": "0001-1",
                "detalle": "Armado",
                "id_operario_opt": None,
            }
        )
        self.assertIsNotNone(fila)
        self.assertEqual(fila["entrada"], 42)
        self.assertEqual(fila["salida"], 0)

    def test_opa_componente_con_salida(self):
        fila = _normalizar_fila_kardex(
            {
                "tipo_mov": "OPA",
                "motivo_movimiento": "Armado",
                "total_entrada": 0,
                "total_salida": 126,
                "fecha": "2026-08-03",
                "codigo_movimiento": 11,
                "nro_comprobante": "0001-2",
                "detalle": "Armado",
                "id_operario_opt": None,
            }
        )
        self.assertEqual(fila["entrada"], 0)
        self.assertEqual(fila["salida"], 126)


class TestTimelineDelegacionAnalisis(SimpleTestCase):
    """URLs legacy timeline → Análisis trazabilidad (informe canónico)."""

    def setUp(self):
        self.factory = RequestFactory()

    def _get_context(self, params, analisis_payload=None):
        from mpr.views import ReportesMPRView

        view = ReportesMPRView()
        request = self.factory.get("/mpr/reportes/", params)
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.reportes")
        view.request = request
        analisis_payload = analisis_payload or _payload_analisis_timeline()
        with patch("mpr.views._get_base_empresa", return_value="empresa92"):
            with patch(
                "mpr.services_kardex_articulo.construir_analisis_trazabilidad_articulo",
                return_value=analisis_payload,
            ) as mock_analisis:
                with patch("mpr.views._build_renglones_modal_map", return_value={"100": {"articulos": []}}):
                    ctx = view.get_context_data()
        return ctx, mock_analisis

    def test_legacy_timeline_carga_kardex_articulo(self):
        ctx, mock_analisis = self._get_context(
            {
                "grupo": "trazabilidad",
                "reporte": "timeline",
                "id_articulo": "1398",
                "desde": "2026-07-01",
                "hasta": "2026-09-01",
            }
        )
        self.assertEqual(ctx["reporte"], "kardex_articulo")
        mock_analisis.assert_called_once()
        self.assertEqual(ctx["meta"]["id_articulo"], 1398)

    def test_grupo_trazabilidad_sin_reporte_usa_kardex(self):
        ctx, mock_analisis = self._get_context(
            {
                "grupo": "trazabilidad",
                "id_articulo": "1398",
                "desde": "2026-07-01",
                "hasta": "2026-09-01",
            }
        )
        self.assertEqual(ctx["reporte"], "kardex_articulo")
        mock_analisis.assert_called_once()

    def test_pipeline_prepara_saldos_semi_sin_desplazarlos_a_produccion(self):
        analisis = _payload_analisis_timeline()
        analisis["deposito"] = {
            "tipo_eje": "pipeline_fabricados",
            "etapas": [
                {"tipo_mpr": "Produccion", "label": "Producción"},
                {"tipo_mpr": "SemiElaborado", "label": "Semi elaborado"},
                {"tipo_mpr": "2daSeleccion", "label": "2da Selección"},
            ],
        }
        analisis["saldo_inicial"] = {
            "valor": 0,
            "calculado_ok": True,
            "por_etapa": {
                "Produccion": 0,
                "SemiElaborado": 0,
                "2daSeleccion": 0,
            },
        }
        analisis["stock"] = {
            "terminado": 28,
            "por_etapa": {
                "Produccion": 0,
                "SemiElaborado": 28,
                "2daSeleccion": 0,
            },
        }
        analisis["movimientos"] = [
            {
                "fecha_display": "17/09/2026",
                "tipo_mov": "INV",
                "clase_ui": "inventario",
                "etapa_label": "Semi elaborado",
                "entrada": 28,
                "salida": 0,
                "saldo_corrido": 28,
                "saldos_por_etapa": {
                    "Produccion": 0,
                    "SemiElaborado": 28,
                    "2daSeleccion": 0,
                },
            }
        ]

        ctx, _ = self._get_context(
            {
                "grupo": "trazabilidad",
                "reporte": "kardex_articulo",
                "id_articulo": "1398",
                "desde": "2026-09-01",
                "hasta": "2026-09-17",
                "presentacion": "docenas",
            },
            analisis,
        )

        fila = ctx["filas"][0]
        self.assertEqual(fila["etapa_label"], "Semi elaborado")
        self.assertEqual(
            [celda["saldo"] for celda in fila["saldos_etapa_ui"]],
            [0, 28, 0],
        )
        self.assertEqual(fila["saldo_consolidado_celda"]["saldo"], 28)


class TestTimelinePartialDeepLink(SimpleTestCase):
    """PR3 — deep-link kardex #timeline preserva filtros (REQ-TRAZ-06)."""

    def test_enlace_kardex_preserva_params(self):
        html = render_to_string(
            "mpr/reportes/partials/trazabilidad_timeline.html",
            {
                "meta": {
                    "id_articulo": 1398,
                    "id_deposito": 6,
                    "codigo_articulo": "610",
                    "descripcion_articulo": "Pack Mix",
                },
                "fecha_desde_iso": "2026-07-01",
                "fecha_hasta_iso": "2026-09-01",
                "modo_presentacion": "docenas",
            },
        )
        self.assertIn("reporte=kardex_articulo", html)
        self.assertIn("id_articulo=1398", html)
        self.assertIn("desde=2026-07-01", html)
        self.assertIn("hasta=2026-09-01", html)
        self.assertIn("presentacion=docenas", html)
        self.assertIn("id_deposito=6", html)
        self.assertIn("#timeline", html)
        self.assertIn("Análisis completo", html)
        self.assertIn("@keydown.arrow-down.prevent", html)
        self.assertIn("focoSugerencia", html)
        self.assertIn("aplicarSugerenciaActiva", html)
        self.assertNotIn("alert(", html)
        self.assertNotIn("window.confirm", html)


class TestExportAnalisisTrazabilidadCsv(SimpleTestCase):
    def test_csv_multi_seccion_utf8_bom(self):
        payload = analisis_trazabilidad_a_csv(
            _payload_analisis_timeline(),
            modo="docenas",
            fecha_desde_display="01/07/2026",
            fecha_hasta_display="30/09/2026",
        )
        self.assertTrue(payload.startswith("\ufeff".encode("utf-8")))
        body = payload.decode("utf-8-sig")
        self.assertIn("DEMANDA PED", body)
        self.assertIn("MOVIMIENTOS", body)
        self.assertIn("EVENTOS MPR", body)
        self.assertIn("Cliente CSV", body)
        self.assertIn("Armado (OPA)", body)

    def test_csv_pipeline_incluye_etapas_y_seccion_saldos(self):
        analisis = _payload_analisis_timeline()
        analisis["deposito"] = {
            "tipo_eje": "pipeline_fabricados",
            "etapas": [
                {"tipo_mpr": "Produccion", "label": "Producción"},
                {"tipo_mpr": "SemiElaborado", "label": "Semi elaborado"},
            ],
        }
        analisis["movimientos"] = [
            {
                "fecha_display": "01/08/2026",
                "tipo_mov": "OPP",
                "etapa_label": "Producción",
                "cod_deposito": 3,
                "saldos_por_etapa": {"Produccion": 79, "SemiElaborado": 28},
                "saldo_corrido": 107,
                "entrada": 0,
                "salida": 0,
                "nro_comprobante": "-",
                "detalle": "",
                "afecta_deposito": True,
                "operario": "-",
            }
        ]
        analisis["saldo_inicial"] = {"por_etapa": {"Produccion": 70, "SemiElaborado": 20}}
        analisis["kpis"]["saldo_final_por_etapa"] = {"Produccion": 79, "SemiElaborado": 28}
        analisis["stock"]["por_etapa"] = {"Produccion": 79, "SemiElaborado": 28}
        body = analisis_trazabilidad_a_csv(analisis, modo="docenas").decode("utf-8-sig")
        self.assertIn("Etapa", body)
        self.assertIn("SALDOS POR ETAPA", body)
        self.assertIn("Saldo Producción", body)
