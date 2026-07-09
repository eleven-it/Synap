"""Tests docenas operativas y clasificación por operario fabricante."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.presentacion_operativa import (
    DEFAULT_MODO,
    enriquecer_fila_tablero_armado,
    enriquecer_fila_tablero_presentacion,
    parse_modo_presentacion_operativa,
    resolver_modo_presentacion_operativa,
)
from mpr.repositories.transicion_lote import crear_transicion_lote
from mpr.views import _envio_cantidad_unidades_desde_post


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
            {
                "dem_ped": 120,
                "dem_res": 24,
                "resta_urgente": 120,
                "resta_total": 144,
                "pendiente": 144,
                "enviado": 0,
                "produccion": 0,
            },
            "docenas",
        )
        self.assertEqual(fila["pedido_pares"], 120)
        self.assertEqual(fila["reserva_pares"], 24)
        self.assertEqual(fila["resta_urgente_pares"], 120)
        self.assertEqual(fila["resta_urgente_docenas_pcp"], 10)
        self.assertEqual(fila["resta_total_pares"], 144)
        self.assertEqual(fila["resta_total_docenas_pcp"], 12)
        self.assertEqual(fila["enviado_display"], "0")
        self.assertNotIn("pares", fila["produccion_display"].lower())

    def test_a_enviar_descuenta_fabricando(self):
        fila = enriquecer_fila_tablero_presentacion(
            {
                "dem_ped": 12,
                "resta_urgente": 12,
                "resta_total": 12,
                "enviado": 12,
                "produccion": 0,
            },
            "unidades",
        )
        self.assertEqual(fila["a_enviar"], 0)
        self.assertEqual(fila["a_enviar_docenas"], 0)

    def test_a_enviar_docenas_pcp_enteras(self):
        fila = enriquecer_fila_tablero_presentacion(
            {
                "resta_urgente": 2405,
                "enviado": 0,
                "produccion": 0,
            },
            "docenas",
        )
        self.assertEqual(fila["a_enviar"], 2405)
        self.assertEqual(fila["a_enviar_docenas"], 200)
        self.assertEqual(fila["a_enviar_pares_sueltos"], 5)
        self.assertEqual(fila["a_enviar_docenas_pcp"], 200)

    def test_envio_cantidad_modo_docenas_solo_docenas(self):
        post = {
            "presentacion": "docenas",
            "envio_42_docenas": "200",
            "envio_42_unidades": "5",
        }
        self.assertEqual(_envio_cantidad_unidades_desde_post(post, 42), 2400)

    def test_envio_cantidad_modo_pares_enteros(self):
        post = {"presentacion": "unidades", "envio_42": "2405"}
        self.assertEqual(_envio_cantidad_unidades_desde_post(post, 42), 2405)

    def test_enriquecer_fila_tablero_armado(self):
        fila = enriquecer_fila_tablero_armado(
            {
                "pedido": 120,
                "stock_terminado": 24,
                "stock_reserva": 0,
                "resta_urgente": 96,
                "resta_armar": 96,
                "max_armable": 8,
                "a_armar": 8,
                "codigo_marca": 1,
            },
            "docenas",
            marcas_etiqueta={1: "Atomik"},
        )
        self.assertEqual(fila["marca_nombre"], "Atomik")
        self.assertEqual(fila["resta_armar_docenas_pcp"], 8)
        self.assertEqual(fila["a_armar_docenas_pcp"], 1)

    def test_enriquecer_fila_tablero_pares(self):
        fila = enriquecer_fila_tablero_presentacion(
            {"resta_urgente": 24, "produccion": 12, "enviado": 0},
            "unidades",
        )
        self.assertEqual(fila["resta_urgente_display"], "24")
        self.assertEqual(fila["produccion_display"], "12")


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

    @patch("mpr.repositories.parte.listar_pares_fecha_turno_con_pendiente_clasificacion", return_value=[])
    @patch(
        "mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno",
        return_value={(10, 5): Decimal("48")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_grilla_con_nombre")
    @patch("mpr.services._fetch_descripciones_articulo", return_value={10: ("12A", "Pack")})
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({10: {"Produccion": 100.0}}, {}))
    def test_grilla_sin_bloqueo_si_clasificacion_completa(
        self, _pivot, _fetch, mock_celdas, _cls, _arr,
    ):
        from mpr.services import construir_grilla_clasificacion_produccion

        mock_celdas.return_value = {
            (10, 5): {"cantidad": Decimal("48"), "operario_nombre": "López"},
        }
        grilla = construir_grilla_clasificacion_produccion(
            "empresa92", date(2026, 7, 8), 1,
        )
        self.assertEqual(grilla["filas"], [])
        self.assertEqual(grilla["bloqueos"], [])

    @patch("mpr.repositories.parte.listar_pares_fecha_turno_con_pendiente_clasificacion", return_value=[])
    @patch("mpr.repositories.transicion_lote.sumar_clasificado_por_operario_fecha_turno", return_value={})
    @patch("mpr.repositories.parte.acumular_celdas_grilla_con_nombre")
    @patch("mpr.services._fetch_descripciones_articulo", return_value={99: ("X", "Sin operario")})
    @patch("mpr.services._pivot_stock_por_tipo_mpr", return_value=({99: {"Produccion": 12.0}}, {}))
    def test_grilla_bloqueo_cantidad_sin_operario(
        self, _pivot, _fetch, mock_celdas, _cls, _arr,
    ):
        from mpr.services import construir_grilla_clasificacion_produccion

        mock_celdas.return_value = {
            (99, 0): {"cantidad": Decimal("12"), "operario_nombre": "-"},
        }
        grilla = construir_grilla_clasificacion_produccion(
            "empresa92", date(2026, 7, 8), 1,
        )
        self.assertEqual(len(grilla["bloqueos"]), 1)
        self.assertEqual(grilla["bloqueos"][0]["id_articulo"], 99)
