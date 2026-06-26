"""Tests: descomposición docenas · unidades (pack con bulto y OPP con divisor 12)."""
from django.test import SimpleTestCase

from mpr.services import (
    agrupar_filas_movimiento_por_articulo,
    build_resumen_metrica_opt,
    cantidad_opp_presentacion_du,
    descomponer_docenas_unidades,
    divisor_docena_pack,
    docenas_enteras_desde_packs,
    enriquecer_movimientos_opp_presentacion_du,
    lineas_texto_cantidad_opp,
    lineas_texto_cantidad_pack,
    texto_docenas_unidades,
)


class DescomponerDocenasUnidadesTest(SimpleTestCase):
    def test_opp_ciento_veinticuatro_es_diez_y_cuatro(self):
        self.assertEqual(
            descomponer_docenas_unidades(124, unidades_por_docena_fijo=12),
            {"docenas": 10, "unidades": 4, "divisor": 12, "total": 124},
        )

    def test_pack_bulto_doce(self):
        self.assertEqual(
            descomponer_docenas_unidades(124, 12),
            {"docenas": 10, "unidades": 4, "divisor": 12, "total": 124},
        )

    def test_pack_bulto_veinticuatro(self):
        self.assertEqual(
            descomponer_docenas_unidades(124, 24),
            {"docenas": 5, "unidades": 4, "divisor": 24, "total": 124},
        )

    def test_bulto_cero_usa_doce(self):
        self.assertEqual(divisor_docena_pack(0), 12)
        self.assertEqual(texto_docenas_unidades(124, 0), "10 docenas · 4 unidades")

    def test_docenas_enteras_armado_sin_unidades_sueltas(self):
        self.assertEqual(docenas_enteras_desde_packs(41, 12), 3)
        self.assertEqual(docenas_enteras_desde_packs(24, 12), 2)
        self.assertEqual(docenas_enteras_desde_packs(23, 12), 1)


class BuildResumenMetricaOptTest(SimpleTestCase):
    def test_varias_lineas_mismo_bulto_agrega_total(self):
        lineas = [
            {"etiqueta": "A", "packs": 500, "bulto": 12},
            {"etiqueta": "B", "packs": 1000, "bulto": 12},
        ]
        r = build_resumen_metrica_opt(1500, lineas)
        self.assertFalse(r["mostrar_desglose"])
        self.assertEqual(r["texto_principal"], "125 docenas · 0 unidades")

    def test_bultos_distintos_muestra_desglose_c4(self):
        lineas = [
            {"etiqueta": "A", "packs": 500, "bulto": 12},
            {"etiqueta": "B", "packs": 1000, "bulto": 24},
        ]
        r = build_resumen_metrica_opt(1500, lineas)
        self.assertTrue(r["mostrar_desglose"])
        self.assertEqual(r["texto_principal"], "1500 packs")
        self.assertEqual(r["lineas"][0]["texto_docenas_unidades"], "41 docenas · 8 unidades")
        self.assertEqual(r["lineas"][1]["texto_docenas_unidades"], "41 docenas · 16 unidades")


class CantidadOppPresentacionDuTest(SimpleTestCase):
    def test_trescientos_sesenta_es_treinta_docenas(self):
        self.assertEqual(
            cantidad_opp_presentacion_du(360),
            {"docenas": 30, "unidades": 0, "divisor": 12, "total": 360},
        )

    def test_ciento_veinte_es_diez_docenas(self):
        self.assertEqual(
            cantidad_opp_presentacion_du(120),
            {"docenas": 10, "unidades": 0, "divisor": 12, "total": 120},
        )

    def test_enriquecer_movimientos_opp(self):
        movs = [{"cantidad_total": 124}]
        enriquecer_movimientos_opp_presentacion_du(movs)
        self.assertEqual(movs[0]["cantidad_du"]["docenas"], 10)
        self.assertEqual(movs[0]["cantidad_du"]["unidades"], 4)

    def test_lineas_texto_opp(self):
        self.assertEqual(
            lineas_texto_cantidad_opp(360),
            ["30 docenas", "0 unidades"],
        )

    def test_lineas_texto_pack(self):
        self.assertEqual(
            lineas_texto_cantidad_pack(1100, 4),
            ["1100 packs", "275 docenas", "0 unidades"],
        )


class AgruparFilasMovimientoPorArticuloTest(SimpleTestCase):
    def test_agrupa_mismo_id_articulo(self):
        filas = [
            {"id_articulo": 10, "codigo_articulo": "A", "descripcion": "Desc", "nombre_deposito": "Prod"},
            {"id_articulo": 10, "codigo_articulo": "A", "descripcion": "Desc", "nombre_deposito": "Semi"},
            {"id_articulo": 11, "codigo_articulo": "B", "descripcion": "Otro", "nombre_deposito": "Prod"},
        ]
        grupos = agrupar_filas_movimiento_por_articulo(filas)
        self.assertEqual(len(grupos), 2)
        self.assertEqual(len(grupos[0]["filas"]), 2)
        self.assertEqual(grupos[0]["filas"][0]["nombre_deposito"], "Prod")
        self.assertEqual(grupos[0]["filas"][1]["nombre_deposito"], "Semi")
        self.assertEqual(len(grupos[1]["filas"]), 1)
