"""Reglas de destino y cantidad heredadas del control de salida VB6."""

from decimal import Decimal
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from core.middleware.mobile_level_a_middleware import mobile_path_allowed_for_level_a
from stock.services.prep_cajas import (
    PreparacionError, _cantidad_codigo, _coincide_codigo, _compatible,
    _cajas_listas, _estado_finalizacion, abrir_caja,
    registrar_lectura,
)


class CajasPreparacionReglasTests(SimpleTestCase):
    def setUp(self):
        self.caja = {
            "id_cliente": 12, "id_cliente_domicilio": 201,
            "destino_entrega": "Casa Matriz", "estado": "Abierta",
            "codigo_movimiento_ped_origen": 100,
        }
        self.linea = {
            "id_cliente": 12, "id_cliente_domicilio": 201,
            "destino": "Casa Matriz", "id_articulo": 42, "pedido": 101,
            "codigo_manual": "M42", "barra_interna": "7790012345678",
            "barra_fabrica": "", "barra_display": "D42",
            "barra_bulto": "B42", "unidades_display": 6,
            "displays_bulto": 4, "lote": "No", "serie": "No",
        }

    def test_mismo_cliente_y_domicilio_admite_pedidos_distintos(self):
        self.assertTrue(_compatible(self.caja, self.linea))
        self.assertFalse(_compatible(self.caja, {**self.linea, "id_cliente": 13}))
        self.assertFalse(_compatible(self.caja, {**self.linea, "id_cliente_domicilio": 202}))

    def test_sin_id_domicilio_compara_texto(self):
        linea = {**self.linea, "id_cliente_domicilio": None, "destino": "  casa  matriz "}
        self.assertTrue(_compatible(self.caja, linea))
        self.assertFalse(_compatible(self.caja, {**linea, "destino": "Otra sucursal"}))

    def test_pedido_origen_siempre_es_compatible(self):
        self.assertTrue(_compatible(self.caja, {**self.linea, "pedido": 100, "destino": ""}))

    def test_barras_unidad_display_y_bulto(self):
        self.assertEqual(_cantidad_codigo("7790012345678", self.linea), (Decimal(1), "Unidad"))
        self.assertEqual(_cantidad_codigo("7790012345678", self.linea, "display"),
                         (Decimal(6), "Display por modo"))
        self.assertEqual(_cantidad_codigo("D42", self.linea), (Decimal(6), "Display"))
        self.assertEqual(_cantidad_codigo("B42", self.linea), (Decimal(24), "Bulto"))
        self.assertIsNone(_cantidad_codigo("NOEXISTE", self.linea))

    def test_etiqueta_333_conserva_su_cantidad(self):
        self.assertEqual(_cantidad_codigo("333000420007", self.linea), (Decimal(7), "Etiqueta 333"))
        self.assertEqual(_cantidad_codigo("333000420007", self.linea, "display"),
                         (Decimal(7), "Etiqueta 333"))
        self.assertTrue(_coincide_codigo("333000420007", self.linea))
        self.assertFalse(_coincide_codigo("333000430007", self.linea))
        with self.assertRaises(PreparacionError):
            _cantidad_codigo("333000420000", self.linea)

    def test_lote_impide_conversion_a_display(self):
        with self.assertRaises(PreparacionError):
            _cantidad_codigo("D42", {**self.linea, "lote": "Si"})
        self.assertEqual(_cantidad_codigo("7790012345678", {**self.linea, "lote": "Si"}, "display"),
                         (Decimal(1), "Unidad"))

    def test_pantalla_y_api_disponibles_en_movil(self):
        self.assertTrue(mobile_path_allowed_for_level_a("/stock/preparacion-cajas/"))
        self.assertTrue(mobile_path_allowed_for_level_a("/stock/api/preparacion-cajas/42/lectura/"))

    def test_finalizacion_exige_todos_los_articulos_y_cajas_cerradas_con_contenido(self):
        articulos = [{"faltante": Decimal(0)}, {"faltante": Decimal(0)}]
        caja = {"estado": "Cerrada", "lecturas_activas": 2}
        self.assertEqual(_estado_finalizacion(articulos, [caja]), (True, True))
        self.assertEqual(_estado_finalizacion([{**articulos[0], "faltante": Decimal(1)}], [caja]), (False, False))
        self.assertEqual(_estado_finalizacion(articulos, [{**caja, "estado": "Abierta"}]), (True, False))
        self.assertEqual(_estado_finalizacion(articulos, [caja, {**caja, "lecturas_activas": 0}]), (True, False))
        self.assertEqual(_estado_finalizacion([], [caja]), (False, False))

    def test_cajas_cerradas_con_faltantes_quedan_listas_para_control_parcial(self):
        caja = {"estado": "Cerrada", "lecturas_activas": 1}
        self.assertTrue(_cajas_listas([caja]))
        self.assertEqual(_estado_finalizacion([{"faltante": Decimal(6)}], [caja]),
                         (False, False))
        self.assertFalse(_cajas_listas([{**caja, "estado": "Abierta"}]))
        self.assertFalse(_cajas_listas([{**caja, "lecturas_activas": 0}]))


class CajasPreparacionRegistroTests(SimpleTestCase):
    KEY = "e89687fa-005e-4012-a774-47c0615d0ad3"

    def setUp(self):
        self.cursor = MagicMock()
        self.cursor.fetchone.side_effect = [None, {
            "id_caja": 1, "estado": "Abierta", "id_cliente": 12,
            "id_cliente_domicilio": 201, "destino_entrega": "Casa Matriz",
            "codigo_movimiento_ped_origen": 100,
        }]
        self.cursor.lastrowid = 77
        self.linea = {
            "pedido": 100, "id_articulo": 42, "id_stock": 900,
            "id_cliente": 12, "id_cliente_domicilio": 201,
            "destino": "Casa Matriz", "pendiente": Decimal(3),
            "articulo": "Artículo 42", "nro_pedido": "PED-100",
            "codigo_manual": "M42", "barra_interna": "7790012345678",
            "barra_fabrica": "", "barra_display": "D42",
            "barra_bulto": "B42", "unidades_display": 6,
            "displays_bulto": 4, "lote": "No", "serie": "No",
        }

    @contextmanager
    def _fake_tx(self, _base):
        yield self.cursor

    def _registrar(self, consumido=None, lineas=None, modo="unidad", otros=None):
        with patch("stock.services.prep_cajas._tx", self._fake_tx), \
             patch("stock.services.prep_cajas._bloquear_preparacion", return_value=1), \
             patch("stock.services.prep_cajas._asegurar_reserva"), \
             patch("stock.services.prep_cajas._lineas", return_value=lineas or [self.linea]), \
             patch("stock.services.prep_cajas._consumos", return_value=consumido or {}), \
             patch("stock.services.prep_cajas._consumo_otros_bloqueado",
                   return_value=(otros or {}).get((100, 42), Decimal(0))):
            return registrar_lectura("prueba", 44, 1, "7790012345678", self.KEY, 7, modo)

    def test_lectura_registra_pedido_y_linea_exactos(self):
        resultado = self._registrar()
        self.assertEqual(resultado["id_lectura"], 77)
        self.assertEqual(resultado["cantidad"], Decimal(1))
        self.assertIn(900, self.cursor.execute.call_args.args[1])

    def test_rechaza_exceso_de_cantidad_ya_leida(self):
        with self.assertRaisesMessage(PreparacionError, "supera la cantidad"):
            self._registrar(consumido={(100, 42): Decimal(3)})
        self.assertFalse(any("INSERT INTO synap_prep_caja_lectura" in c.args[0]
                             for c in self.cursor.execute.call_args_list))

    def test_parcial_rechaza_unidades_armadas_en_otra_preparacion(self):
        with self.assertRaisesMessage(PreparacionError, "Quedan 0 unidades"):
            self._registrar(otros={(100, 42): Decimal(3)})
        self.assertFalse(any("INSERT INTO synap_prep_caja_lectura" in c.args[0]
                             for c in self.cursor.execute.call_args_list))

    def test_parcial_rechaza_display_que_supera_saldo_entre_preparaciones(self):
        with self.assertRaisesMessage(PreparacionError, "Quedan 4 unidades"):
            self._registrar(lineas=[{**self.linea, "pendiente": Decimal(8)}],
                            otros={(100, 42): Decimal(4)}, modo="display")
        self.assertFalse(any("INSERT INTO synap_prep_caja_lectura" in c.args[0]
                             for c in self.cursor.execute.call_args_list))

    def test_no_abre_caja_para_pedido_ya_armado_en_otra_preparacion(self):
        with patch("stock.services.prep_cajas._tx", self._fake_tx), \
             patch("stock.services.prep_cajas._bloquear_preparacion", return_value=1), \
             patch("stock.services.prep_cajas._asegurar_reserva"), \
             patch("stock.services.prep_cajas._lineas", return_value=[self.linea]), \
             patch("stock.services.prep_cajas._consumos_otras_preparaciones",
                   return_value={(100, 42): Decimal(3)}):
            with self.assertRaisesMessage(PreparacionError, "no tiene artículos pendientes"):
                abrir_caja("prueba", 44, 100, 7, "sesion")
        self.assertFalse(any("INSERT INTO synap_prep_caja" in c.args[0]
                             for c in self.cursor.execute.call_args_list))

    def test_modo_display_registra_pack_y_respeta_faltante(self):
        resultado = self._registrar(lineas=[{**self.linea, "pendiente": Decimal(12)}], modo="display")
        self.assertEqual(resultado["cantidad"], Decimal(6))
        self.assertTrue(any("INSERT INTO synap_prep_caja_lectura" in c.args[0]
                            and "Display por modo" in c.args[1] and Decimal(6) in c.args[1]
                            for c in self.cursor.execute.call_args_list))
        self.cursor.reset_mock()
        self.cursor.fetchone.side_effect = [None, {
            "id_caja": 1, "estado": "Abierta", "id_cliente": 12,
            "id_cliente_domicilio": 201, "destino_entrega": "Casa Matriz",
            "codigo_movimiento_ped_origen": 100,
        }]
        with self.assertRaisesMessage(PreparacionError, "supera la cantidad"):
            self._registrar(lineas=[{**self.linea, "pendiente": Decimal(5)}], modo="display")

    def test_rechaza_otro_domicilio(self):
        with self.assertRaisesMessage(PreparacionError, "otra sucursal"):
            self._registrar(lineas=[{**self.linea, "pedido": 101,
                                     "id_cliente_domicilio": 202, "destino": "Sucursal 2"}])
