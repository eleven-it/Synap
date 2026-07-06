"""Tests docenas operativas y clasificación por operario fabricante."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.presentacion_operativa import (
    DEFAULT_MODO,
    enriquecer_fila_tablero_presentacion,
    parse_modo_presentacion_operativa,
    resolver_modo_presentacion_operativa,
)
from mpr.repositories.transicion_lote import crear_transicion_lote


class PresentacionOperativaTests(SimpleTestCase):
    def test_default_modo_docenas(self):
        self.assertEqual(parse_modo_presentacion_operativa(None), DEFAULT_MODO)
        self.assertEqual(parse_modo_presentacion_operativa(""), "docenas")

    def test_resolver_sesion_desde_get(self):
        request = MagicMock()
        request.GET = {"presentacion": "unidades"}
        request.session = {}
        self.assertEqual(resolver_modo_presentacion_operativa(request), "unidades")
        self.assertEqual(request.session["mpr_presentacion_cantidad"], "unidades")

    def test_enriquecer_fila_tablero_docenas(self):
        fila = enriquecer_fila_tablero_presentacion(
            {"pendiente": 6500, "enviado": 120},
            "docenas",
        )
        self.assertIn("docenas", fila["pendiente_display"])
        self.assertEqual(fila["pendiente_docenas"], 541)
        self.assertEqual(fila["pendiente_unidades_sueltas"], 8)


class TransicionLoteOperarioTests(SimpleTestCase):
    @patch("mpr.repositories.transicion_lote.mysql_cursor")
    def test_crear_transicion_con_operario(self, mock_cursor_ctx):
        cursor = MagicMock()
        cursor.lastrowid = 99
        mock_cursor_ctx.return_value.__enter__.return_value = cursor

        tid = crear_transicion_lote(
            "empresa92",
            100,
            "Produccion",
            "SemiElaborado",
            Decimal("12"),
            5001,
            7,
            id_operario=3,
            operario_nombre="García",
            fecha_produccion=date(2026, 7, 8),
            id_mpr_turno=1,
        )
        self.assertEqual(tid, 99)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("id_operario", sql)
        params = cursor.execute.call_args[0][1]
        self.assertEqual(params[6], 3)
        self.assertEqual(params[7], "García")


class ClasificacionOperarioServicioTests(SimpleTestCase):
    @patch("mpr.services._fetch_descripciones_articulo", return_value={10: ("12A", "Pack")})
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({10: {"Produccion": 100.0}}, {}))
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno")
    @patch("mpr.repositories.parte.acumular_celdas_grilla_con_nombre")
    @patch("mpr.repositories.parte.listar_pares_fecha_turno_con_pendiente_clasificacion", return_value=[])
    def test_grilla_filas_por_operario(
        self,
        _arrastre,
        mock_celdas,
        mock_clasif,
        *_rest,
    ):
        from mpr.services import construir_grilla_clasificacion_produccion

        mock_celdas.return_value = {
            (10, 5): {"cantidad": Decimal("48"), "operario_nombre": "López"},
            (10, 6): {"cantidad": Decimal("36"), "operario_nombre": "García"},
        }
        mock_clasif.return_value = {(10, 5): Decimal("12")}
        grilla = construir_grilla_clasificacion_produccion(
            "empresa92", date(2026, 7, 8), 1,
        )
        self.assertEqual(len(grilla["filas"]), 2)
        pendientes = {f["id_operario"]: f["disponible"] for f in grilla["filas"]}
        self.assertEqual(pendientes[5], 36.0)
        self.assertEqual(pendientes[6], 36.0)

    @patch("mpr.repositories.parte.listar_pares_fecha_turno_con_pendiente_clasificacion", return_value=[])
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno",
        return_value={(10, 5): Decimal("48")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_grilla_con_nombre")
    @patch("mpr.services._fetch_descripciones_articulo", return_value={10: ("12A", "Pack")})
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({10: {"Produccion": 100.0}}, {}))
    def test_grilla_ver_roster_muestra_completadas(
        self, _pivot, _fetch, mock_celdas, _cls, _arr,
    ):
        from mpr.services import construir_grilla_clasificacion_produccion

        mock_celdas.return_value = {
            (10, 5): {"cantidad": Decimal("48"), "operario_nombre": "López"},
        }
        grilla = construir_grilla_clasificacion_produccion(
            "empresa92", date(2026, 7, 8), 1, ver_roster_completo=True,
        )
        self.assertEqual(len(grilla["filas"]), 1)
        self.assertTrue(grilla["filas"][0]["solo_lectura"])
        self.assertIn("Completo", grilla["filas"][0]["disponible_texto"])
