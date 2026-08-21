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
                "resta_urgente_ped": 96,
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
        self.assertEqual(fila["resta_urgente_ped_pares"], 96)
        self.assertEqual(fila["resta_urgente_ped_docenas_pcp"], 8)
        self.assertEqual(fila["resta_total_pares"], 144)
        self.assertEqual(fila["resta_total_docenas_pcp"], 12)
        self.assertEqual(fila["enviado_display"], "0")
        self.assertNotIn("pares", fila["produccion_display"].lower())

    def test_a_enviar_descuenta_fabricando(self):
        """Tope = Urgente − Fabricando."""
        fila = enriquecer_fila_tablero_presentacion(
            {
                "dem_ped": 12,
                "resta_urgente": 12,
                "resta_total": 12,
                "envios": 12,
                "enviado": 12,
                "produccion": 0,
            },
            "unidades",
        )
        self.assertEqual(fila["a_enviar"], 0)
        self.assertEqual(fila["a_enviar_docenas"], 0)

    def test_a_enviar_con_fabricando_parcial(self):
        """Urgente 12, Fabricando 0 → A enviar 12 aunque ledger tenga envíos."""
        fila = enriquecer_fila_tablero_presentacion(
            {
                "dem_ped": 12,
                "resta_urgente": 12,
                "resta_total": 12,
                "envios": 12,
                "enviado": 0,
                "produccion": 0,
            },
            "unidades",
        )
        self.assertEqual(fila["a_enviar"], 12)

    def test_a_enviar_pedido_nuevo_vs_fabricando(self):
        """Pedido incremental: Urgente 180, Fabricando 130 → A enviar 50."""
        fila = enriquecer_fila_tablero_presentacion(
            {
                "resta_urgente": 180,
                "envios": 200,
                "enviado": 130,
                "produccion": 49,
            },
            "unidades",
        )
        self.assertEqual(fila["a_enviar"], 50)

    def test_a_enviar_docenas_pcp_cero_deshabilita_concepto(self):
        """Pares sueltos < media docena: tope docenas = 0 (input no editable en UI)."""
        fila = enriquecer_fila_tablero_presentacion(
            {
                "resta_urgente": 5,
                "resta_total": 5,
                "envios": 0,
                "enviado": 0,
            },
            "docenas",
        )
        self.assertEqual(fila["a_enviar"], 5)
        self.assertEqual(fila["a_enviar_docenas_pcp"], 0)

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
        self.assertEqual(fila["stock_terminado_display"], "2")
        self.assertFalse(fila.get("stock_terminado_es_negativo"))

    def test_armado_stock_terminado_muestra_negativo(self):
        """Terminado muestra saldo real (no clamp a 0), modo pares."""
        fila = enriquecer_fila_tablero_armado(
            {
                "pedido": 0,
                "stock_terminado": -52,
                "stock_reserva": 0,
                "resta_urgente": 52,
                "resta_armar": 52,
                "max_armable": 10,
                "a_armar": 0,
            },
            "unidades",
        )
        self.assertEqual(fila["stock_terminado_display"], "-52")
        self.assertTrue(fila["stock_terminado_es_negativo"])
        # Otras columnas de demanda siguen sin negativos en display.
        self.assertEqual(fila["resta_armar_display"], "52")

    def test_enriquecer_fila_tablero_pares(self):
        fila = enriquecer_fila_tablero_presentacion(
            {"resta_urgente": 24, "produccion": 12, "enviado": 0},
            "unidades",
        )
        self.assertEqual(fila["resta_urgente_display"], "24")
        self.assertEqual(fila["produccion_display"], "12")

    def test_enriquecer_fila_tablero_envios_display(self):
        fila = enriquecer_fila_tablero_presentacion(
            {"resta_urgente": 24, "envios": 12, "enviado": 5},
            "unidades",
        )
        self.assertEqual(fila["envios_display"], "12")
        self.assertEqual(fila["enviado_display"], "5")


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
        self.assertEqual(params[7], 3)
        self.assertEqual(params[8], "García")
        self.assertIn("cantidad_extra", sql)


class ClasificacionOperarioServicioTests(SimpleTestCase):
    """Grilla consolidada: saldo Producción, colapso máquinas, roster/pendiente."""

    def setUp(self):
        self._patches = [
            patch("mpr.repositories.clasificacion_borrador.listar_lineas_borrador", return_value={}),
            patch("mpr.repositories.clasificacion_borrador.tiene_borrador", return_value=False),
            patch("mpr.repositories.clasificacion_borrador.tiene_borrador_cc_consolidado", return_value=False),
            patch("mpr.repositories.clasificacion_borrador.listar_lineas_borrador_cc_consolidado", return_value=[]),
            patch("mpr.repositories.transicion_lote.semi_agregado_por_articulo_fecha", return_value={}),
            patch("mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha", return_value={}),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()

    @patch("mpr.services._fetch_descripciones_articulo", return_value={10: ("12A", "Pack")})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={10: {"Produccion": 100.0}})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_grilla_filas_por_operario(self, mock_celdas, *_rest):
        from mpr.services import construir_grilla_clasificacion_produccion

        mock_celdas.return_value = {
            (0, 10, 5, 1): {
                "cantidad": Decimal("48"),
                "operario_nombre": "López",
                "maquina_nombre": "—",
                "turno_nombre": "Mañana",
            },
            (0, 10, 6, 1): {
                "cantidad": Decimal("36"),
                "operario_nombre": "García",
                "maquina_nombre": "—",
                "turno_nombre": "Mañana",
            },
        }
        grilla = construir_grilla_clasificacion_produccion("empresa92", date(2026, 7, 8), 1)
        self.assertEqual(len(grilla["bloques"]), 1)
        self.assertEqual(len(grilla["bloques"][0]["filas"]), 2)
        saldos = {f["id_operario"]: float(grilla["bloques"][0]["saldo_produccion"]) for f in grilla["bloques"][0]["filas"]}
        self.assertEqual(saldos[5], 100.0)
        self.assertEqual(saldos[6], 100.0)

    @patch("mpr.services._fetch_descripciones_articulo", return_value={10: ("12A", "Pack")})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={10: {"Produccion": 0.0}})
    @patch(
        "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
        return_value={(10, 5, 1): Decimal("48")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_grilla_ver_roster_muestra_completadas(self, mock_celdas, *_rest):
        from mpr.services import construir_grilla_clasificacion_produccion

        mock_celdas.return_value = {
            (0, 10, 5, 1): {
                "cantidad": Decimal("48"),
                "operario_nombre": "López",
                "maquina_nombre": "—",
                "turno_nombre": "Mañana",
            },
        }
        grilla = construir_grilla_clasificacion_produccion(
            "empresa92", date(2026, 7, 8), 1, ver_roster_completo=True,
        )
        self.assertEqual(len(grilla["bloques"]), 1)
        self.assertTrue(grilla["bloques"][0]["solo_lectura"])
        self.assertFalse(grilla["hay_filas_editables"])

        solo_pendiente = construir_grilla_clasificacion_produccion(
            "empresa92", date(2026, 7, 8), 1, ver_roster_completo=False,
        )
        self.assertTrue(solo_pendiente["filas_vacio"])
        self.assertFalse(solo_pendiente["hay_filas_editables"])

    @patch("mpr.services._fetch_descripciones_articulo", return_value={10: ("12A", "Pack")})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={10: {"Produccion": 100.0}})
    @patch(
        "mpr.repositories.transicion_lote.clasificado_segunda_scrap_por_celda_fecha",
        return_value={(10, 5, 1): Decimal("48")},
    )
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno")
    def test_grilla_sin_bloqueo_si_clasificacion_completa(self, mock_celdas, *_rest):
        from mpr.services import construir_grilla_clasificacion_produccion

        mock_celdas.return_value = {
            (0, 10, 5, 1): {
                "cantidad": Decimal("48"),
                "operario_nombre": "López",
                "maquina_nombre": "—",
                "turno_nombre": "Mañana",
            },
        }
        pendiente = construir_grilla_clasificacion_produccion("empresa92", date(2026, 7, 8), 1)
        # Solo pendiente oculta operario ya clasificado en 2da/scrap; bloque puede quedar vacío de filas.
        self.assertEqual(pendiente["bloqueos"], [])
        roster = construir_grilla_clasificacion_produccion(
            "empresa92", date(2026, 7, 8), 1, ver_roster_completo=True,
        )
        self.assertEqual(len(roster["bloques"]), 1)
        self.assertEqual(roster["bloqueos"], [])

    @patch("mpr.services._fetch_descripciones_articulo", return_value={99: ("X", "Sin parte")})
    @patch("mpr.services_cc_consolidado._pivot_saldo_produccion", return_value={99: {"Produccion": 12.0}})
    @patch("mpr.repositories.parte.acumular_celdas_clasificacion_maquina_turno", return_value={})
    def test_grilla_huerfano_sin_operario(self, *_rest):
        from mpr.services import construir_grilla_clasificacion_produccion

        grilla = construir_grilla_clasificacion_produccion("empresa92", date(2026, 7, 8), 1)
        self.assertEqual(len(grilla["bloques"]), 1)
        self.assertTrue(grilla["bloques"][0]["huerfano"])
        self.assertEqual(grilla["bloqueos"], [])


