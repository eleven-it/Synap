"""Filtro por depósito/etapa del pipeline en Análisis trazabilidad (kardex_articulo)."""
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from mpr.services_kardex_articulo import (
    _calcular_saldo_corrido_por_etapa,
    filtrar_analisis_por_etapa,
    resolver_etapa_filtro_kardex,
)
from mpr.tests.test_reportes_trazabilidad import _mock_user_reportes

ETAPAS = [
    {"tipo_mpr": "Produccion", "label": "Producción", "id_deposito": 10},
    {"tipo_mpr": "Semi", "label": "Semi elaborado", "id_deposito": 20},
    {"tipo_mpr": "2da", "label": "2da Selección", "id_deposito": 30},
]
TIPOS = [e["tipo_mpr"] for e in ETAPAS]
MAPA = {e["id_deposito"]: e for e in ETAPAS}


def _mov(cod, dep, entrada=0, salida=0, fecha="2026-07-02"):
    et = MAPA[dep]
    return {
        "codigo_movimiento": cod,
        "cod_deposito": dep,
        "entrada": entrada,
        "salida": salida,
        "fecha": fecha,
        "fecha_display": fecha,
        "afecta_deposito": True,
        "etapa": {"tipo_mpr": et["tipo_mpr"], "label": et["label"]},
        "etapa_label": et["label"],
    }


def _analisis():
    ini = {"Produccion": 5, "Semi": 40, "2da": 70}
    movs = _calcular_saldo_corrido_por_etapa(
        [
            _mov(1, 10, entrada=12),
            _mov(2, 10, salida=12, fecha="2026-07-03"),
            _mov(2, 20, entrada=12, fecha="2026-07-03"),
            _mov(3, 20, salida=5, fecha="2026-07-04"),
            _mov(4, 30, entrada=5, fecha="2026-07-05"),
        ],
        saldo_inicial_por_etapa=ini,
        tipos_etapa=TIPOS,
        mapa_dep=MAPA,
    )
    ult = movs[-1]["saldos_por_etapa"]
    return {
        "articulo": {"id": 871, "codigo": "871", "descripcion": "Media"},
        "deposito": {"tipo_eje": "pipeline_fabricados", "nombre": "Pipeline", "etapas": ETAPAS},
        "movimientos": movs,
        "saldo_inicial": {"valor": sum(ini.values()), "calculado_ok": True, "por_etapa": ini},
        "stock": {"terminado": sum(ult.values()), "por_etapa": dict(ult)},
        "kpis": {
            "saldo_final": movs[-1]["saldo_corrido"],
            "saldo_final_por_etapa": dict(ult),
            "stock_por_etapa": dict(ult),
            "total_entradas": 29,
            "total_salidas": 17,
            "etapas": [{"tipo_mpr": t, "label": MAPA[e["id_deposito"]]["label"]} for t, e in zip(TIPOS, ETAPAS)],
        },
        "advertencias": [],
        "eventos_mpr": [],
    }


class TestResolverEtapaFiltro(SimpleTestCase):
    def test_vacio_y_todos(self):
        self.assertIsNone(resolver_etapa_filtro_kardex("", ETAPAS))
        self.assertIsNone(resolver_etapa_filtro_kardex("Todos", ETAPAS))
        self.assertIsNone(resolver_etapa_filtro_kardex(None, ETAPAS))

    def test_por_tipo_case_insensitive_y_por_id(self):
        self.assertEqual(resolver_etapa_filtro_kardex("semi", ETAPAS), "Semi")
        self.assertEqual(resolver_etapa_filtro_kardex("30", ETAPAS), "2da")

    def test_invalido(self):
        self.assertIsNone(resolver_etapa_filtro_kardex("Terminado", ETAPAS))


class TestFiltrarAnalisisPorEtapa(SimpleTestCase):
    def test_sin_filtro_intacto(self):
        a = _analisis()
        self.assertIs(filtrar_analisis_por_etapa(a, None), a)

    def test_sin_pipeline_intacto(self):
        a = _analisis()
        a["deposito"] = {"tipo_eje": "terminado"}
        self.assertIs(filtrar_analisis_por_etapa(a, "Semi"), a)

    def test_semi_saldos_consistentes(self):
        r = filtrar_analisis_por_etapa(_analisis(), "Semi")
        movs = r["movimientos"]
        self.assertEqual([m["codigo_movimiento"] for m in movs], [2, 3])
        self.assertEqual(r["saldo_inicial"]["valor"], 40)
        self.assertEqual([m["saldo_corrido"] for m in movs], [52, 47])
        self.assertEqual(r["kpis"]["saldo_final"], 47)
        self.assertEqual(r["kpis"]["saldo_final_por_etapa"], {"Semi": 47})
        self.assertEqual(r["kpis"]["total_entradas"], 12)
        self.assertEqual(r["kpis"]["total_salidas"], 5)
        # saldo inicial + neto == cierre
        neto = sum(m["entrada"] - m["salida"] for m in movs)
        self.assertEqual(r["saldo_inicial"]["valor"] + neto, r["kpis"]["saldo_final"])
        self.assertEqual([e["tipo_mpr"] for e in r["deposito"]["etapas"]], ["Semi"])
        self.assertEqual(len(r["deposito"]["etapas_todas"]), 3)
        for m in movs:
            self.assertEqual(list(m["saldos_por_etapa"]), ["Semi"])

    def test_cierres_por_etapa_coinciden_con_desglose_todos(self):
        a = _analisis()
        for t in TIPOS:
            r = filtrar_analisis_por_etapa(a, t)
            self.assertEqual(r["kpis"]["saldo_final"], a["kpis"]["saldo_final_por_etapa"][t])

    def test_etapa_sin_movimientos_cierre_igual_inicial(self):
        a = _analisis()
        a["movimientos"] = [m for m in a["movimientos"] if m["etapa"]["tipo_mpr"] != "2da"]
        a["kpis"]["saldo_final_por_etapa"] = {}
        r = filtrar_analisis_por_etapa(a, "2da")
        self.assertEqual(r["movimientos"], [])
        self.assertEqual(r["kpis"]["saldo_final"], 70)


class TestVistaParametroDeposito(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _ctx(self, extra):
        from mpr.views import ReportesMPRView

        params = {
            "grupo": "trazabilidad",
            "reporte": "kardex_articulo",
            "id_articulo": "871",
            "desde": "2026-07-01",
            "hasta": "2026-10-31",
            "presentacion": "unidades",
        }
        params.update(extra)
        view = ReportesMPRView()
        request = self.factory.get("/mpr/reportes/", params)
        request.session = {"user": {"base_empresa": "empresa92"}}
        request.user = _mock_user_reportes("mpr.reportes")
        view.request = request
        with patch("mpr.views._get_base_empresa", return_value="empresa92"), patch(
            "mpr.services_kardex_articulo.construir_analisis_trazabilidad_articulo",
            return_value=_analisis(),
        ), patch("mpr.views._build_renglones_modal_map", return_value={}):
            return view.get_context_data()

    def test_default_todos(self):
        ctx = self._ctx({})
        self.assertEqual(ctx["meta"]["deposito_filtro"], "")
        self.assertEqual(len(ctx["meta"]["etapas_filtro_opciones"]), 3)
        self.assertEqual(len(ctx["filas"]), 5)

    def test_filtro_semi(self):
        ctx = self._ctx({"deposito": "Semi"})
        self.assertEqual(ctx["meta"]["deposito_filtro"], "Semi")
        self.assertEqual(len(ctx["filas"]), 2)
        self.assertEqual(ctx["meta"]["saldo_cierre_etapas_ui"], [{"label": "Semi elaborado", "valor": 47}])
        self.assertEqual(ctx["_analisis_trazabilidad"]["kpis"]["saldo_final"], 47)

    def test_filtro_invalido_cae_a_todos(self):
        ctx = self._ctx({"deposito": "xyz"})
        self.assertEqual(ctx["meta"]["deposito_filtro"], "")
        self.assertEqual(len(ctx["filas"]), 5)

    def test_csv_respeta_filtro(self):
        from mpr.views import ReportesMPRView

        ctx = self._ctx({"deposito": "Semi"})
        resp = ReportesMPRView()._respuesta_csv(ctx)
        body = resp.content.decode("utf-8-sig")
        self.assertIn("Saldo final,47", body)
