"""Tests: presentación unidades vs docenas en hub de reportes MPR."""
from django.test import RequestFactory, SimpleTestCase

from mpr.reportes_hub import columnas_csv_para_modo
from mpr.reportes_presentacion import (
    aplicar_presentacion_reporte,
    enriquecer_fila_cantidades,
    formatear_cantidad_reporte,
    parse_modo_presentacion,
    preparar_stock_por_deposito,
)
from mpr.views import ReportesMPRView


class ParseModoPresentacionTest(SimpleTestCase):
    def test_default_unidades(self):
        self.assertEqual(parse_modo_presentacion(None), "unidades")
        self.assertEqual(parse_modo_presentacion(""), "unidades")

    def test_docenas_valido(self):
        self.assertEqual(parse_modo_presentacion("docenas"), "docenas")

    def test_valor_invalido_cae_a_unidades(self):
        self.assertEqual(parse_modo_presentacion("invalido"), "unidades")


class FormatearCantidadReporteTest(SimpleTestCase):
    def test_modo_unidades_entero(self):
        self.assertEqual(formatear_cantidad_reporte(124, "unidades"), "124")

    def test_modo_docenas_componente_divisor_12(self):
        self.assertEqual(
            formatear_cantidad_reporte(124, "docenas"),
            "10 docenas · 4 unidades",
        )

    def test_modo_docenas_pack_con_bulto(self):
        self.assertEqual(
            formatear_cantidad_reporte(124, "docenas", cantidad_promedio_bulto=24),
            "5 docenas · 4 unidades",
        )


class AplicarPresentacionReporteTest(SimpleTestCase):
    def test_enriquece_filas_y_kpis(self):
        ctx = aplicar_presentacion_reporte(
            {
                "filas": [{"enviado": 24, "parte": 12}],
                "kpis": {"enviado": 24},
            },
            "docenas",
        )
        self.assertEqual(ctx["modo_presentacion"], "docenas")
        self.assertEqual(ctx["filas"][0]["enviado_display"], "2 docenas · 0 unidades")
        self.assertEqual(ctx["kpis"]["enviado_display"], "2 docenas · 0 unidades")

    def test_eventos_timeline_reciben_id_articulo_meta(self):
        ctx = aplicar_presentacion_reporte(
            {
                "eventos": [{"cantidad": 24, "tipo": "envio"}],
                "meta": {"id_articulo": 99},
            },
            "docenas",
        )
        self.assertEqual(ctx["eventos"][0]["cantidad_display"], "2 docenas · 0 unidades")

    def test_pedidos_cantidad_no_es_campo_cantidad_fisica(self):
        fila = enriquecer_fila_cantidades({"cantidad": 5, "estado": "Pendiente"}, "docenas")
        self.assertNotIn("cantidad_display", fila)


class PrepararStockPorDepositoTest(SimpleTestCase):
    def test_pivotea_una_fila_por_articulo(self):
        raw = [
            {
                "id_articulo": 1138,
                "id_deposito": 3,
                "codigo_articulo": "1.1.1133",
                "descripcion_articulo": "Pack prueba",
                "nombre_deposito": "Semi elaborado",
                "tipo_mpr": "SemiElaborado",
                "saldo": 762.0,
            },
            {
                "id_articulo": 1138,
                "id_deposito": 4,
                "codigo_articulo": "1.1.1133",
                "descripcion_articulo": "Pack prueba",
                "nombre_deposito": "Segunda selección",
                "tipo_mpr": "2daSeleccion",
                "saldo": 16.0,
            },
        ]
        ctx = preparar_stock_por_deposito(raw, "docenas")
        self.assertEqual(len(ctx["filas"]), 1)
        self.assertEqual(len(ctx["columnas_deposito"]), 2)
        fila = ctx["filas"][0]
        self.assertEqual(fila["codigo_articulo"], "1.1.1133")
        self.assertEqual(len(fila["depositos"]), 2)
        self.assertEqual(fila["depositos"][0]["docenas"], 1)
        self.assertEqual(fila["depositos"][0]["unidades"], 4)
        self.assertEqual(fila["depositos"][1]["docenas"], 63)
        self.assertEqual(fila["depositos"][1]["unidades"], 6)

    def test_celda_vacia_en_deposito_sin_saldo(self):
        raw = [
            {
                "id_articulo": 10,
                "id_deposito": 1,
                "codigo_articulo": "A",
                "descripcion_articulo": "Art A",
                "nombre_deposito": "Terminado",
                "tipo_mpr": "Terminado",
                "saldo": 5.0,
            },
            {
                "id_articulo": 20,
                "id_deposito": 2,
                "codigo_articulo": "B",
                "descripcion_articulo": "Art B",
                "nombre_deposito": "Semi elaborado",
                "tipo_mpr": "SemiElaborado",
                "saldo": 12.0,
            },
        ]
        ctx = preparar_stock_por_deposito(raw, "unidades")
        self.assertEqual(len(ctx["filas"]), 2)
        self.assertEqual(len(ctx["columnas_deposito"]), 2)
        fila_a = next(f for f in ctx["filas"] if f["id_articulo"] == 10)
        self.assertEqual(fila_a["depositos"][0]["unidades"], 0)
        self.assertEqual(fila_a["depositos"][1]["unidades"], 5)


class ColumnasCsvModoTest(SimpleTestCase):
    def test_docenas_usa_display(self):
        cols = columnas_csv_para_modo("produccion", "resumen_diario", "docenas")
        claves = [c for c, _ in cols]
        self.assertIn("enviado_display", claves)
        self.assertNotIn("enviado", claves)

    def test_unidades_mantiene_claves_originales(self):
        cols = columnas_csv_para_modo("produccion", "resumen_diario", "unidades")
        claves = [c for c, _ in cols]
        self.assertIn("enviado", claves)


class ReportesMPRViewPresentacionTest(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_contexto_incluye_modo_presentacion(self):
        request = self.factory.get(
            "/mpr/reportes/",
            {"grupo": "produccion", "reporte": "resumen_diario", "presentacion": "docenas"},
        )
        request.session = {"base_empresa": "administranet96"}
        view = ReportesMPRView()
        view.setup(request)
        ctx = view.get_context_data()
        self.assertEqual(ctx["modo_presentacion"], "docenas")
        self.assertEqual(ctx["etiqueta_cantidad"], "docenas · unidades")
