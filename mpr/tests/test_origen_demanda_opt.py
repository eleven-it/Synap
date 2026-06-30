"""Tests origen de demanda en OPT."""
from django.test import SimpleTestCase

from mpr.services import (
    _etiqueta_origen_demanda_desde_split,
    aplicar_origen_demanda_a_filas,
    resumen_origen_demanda_opt,
)


class OrigenDemandaEtiquetaTest(SimpleTestCase):
    def test_pedido_solo(self):
        self.assertEqual(_etiqueta_origen_demanda_desde_split(10, 0), "Pedido")

    def test_reserva_solo(self):
        self.assertEqual(_etiqueta_origen_demanda_desde_split(0, 5), "Reserva")

    def test_pedido_mas_reserva(self):
        self.assertEqual(_etiqueta_origen_demanda_desde_split(3, 2), "Pedido + reserva")

    def test_sin_demanda(self):
        self.assertEqual(_etiqueta_origen_demanda_desde_split(0, 0), "—")

    def test_aplicar_a_filas(self):
        filas = [{"id_articulo": 1}, {"id_articulo": 2}]
        mapa = {
            1: {"origen_demanda_etiqueta": "Pedido", "cantidad_pedida_pedido": 10, "cantidad_demanda_reserva": 0},
            2: {"origen_demanda_etiqueta": "Reserva", "cantidad_pedida_pedido": 0, "cantidad_demanda_reserva": 4},
        }
        aplicar_origen_demanda_a_filas(filas, mapa)
        self.assertEqual(filas[0]["origen_demanda_etiqueta"], "Pedido")
        self.assertEqual(filas[1]["origen_demanda_etiqueta"], "Reserva")

    def test_resumen_varios(self):
        lineas = [
            {"origen_demanda_etiqueta": "Pedido"},
            {"origen_demanda_etiqueta": "Reserva"},
        ]
        self.assertEqual(resumen_origen_demanda_opt(lineas), "Varios")

    def test_resumen_unico(self):
        lineas = [{"origen_demanda_etiqueta": "Pedido + reserva"}]
        self.assertEqual(resumen_origen_demanda_opt(lineas), "Pedido + reserva")


class ProgresoOptTest(SimpleTestCase):
    def test_cerrada_100(self):
        from mpr.services import calcular_porcentaje_progreso_opt

        self.assertEqual(calcular_porcentaje_progreso_opt(False, 0), 100)

    def test_en_proceso_con_opp_pendiente(self):
        from mpr.services import calcular_porcentaje_progreso_opt

        self.assertEqual(calcular_porcentaje_progreso_opt(True, 50), 40)

    def test_en_proceso_opp_cero(self):
        from mpr.services import calcular_porcentaje_progreso_opt

        self.assertEqual(calcular_porcentaje_progreso_opt(True, 0), 80)


class AgruparOptListadoTest(SimpleTestCase):
    def test_agrupa_mismo_codigo_movimiento(self):
        from mpr.services import agrupar_filas_opt_listado_por_lote

        filas = [
            {"codigo_movimiento_opt": 100, "id_lista_produccion": 5, "cantidad_pedida": 10, "cantidad_pendiente_prod": 0, "porcentaje_progreso": 80, "fase_clave": "lista_cerrar", "etiqueta_fase": "Lista para cerrar", "en_proceso_produccion": "Si"},
            {"codigo_movimiento_opt": 100, "id_lista_produccion": 8, "cantidad_pedida": 20, "cantidad_pendiente_prod": 5, "porcentaje_progreso": 40, "fase_clave": "en_produccion_opp", "etiqueta_fase": "OPP", "en_proceso_produccion": "Si"},
        ]
        grupos = agrupar_filas_opt_listado_por_lote(filas)
        self.assertEqual(len(grupos), 1)
        self.assertTrue(grupos[0]["es_grupo"])
        self.assertEqual(grupos[0]["cantidad_pedida"], 30)
        self.assertEqual(len(grupos[0]["lineas"]), 2)

    def test_fila_sola_no_es_grupo(self):
        from mpr.services import agrupar_filas_opt_listado_por_lote

        filas = [{"codigo_movimiento_opt": 50, "id_lista_produccion": 3, "codigo_articulo": "X", "cantidad_pedida": 1, "cantidad_pendiente_prod": 0, "porcentaje_progreso": 100, "fase_clave": "cerrada", "etiqueta_fase": "Cerrada", "en_proceso_produccion": "No"}]
        grupos = agrupar_filas_opt_listado_por_lote(filas)
        self.assertEqual(len(grupos), 1)
        self.assertFalse(grupos[0]["es_grupo"])
        self.assertEqual(grupos[0]["codigo_articulo"], "X")
