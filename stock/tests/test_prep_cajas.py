"""Reglas de destino y cantidad heredadas del control de salida VB6."""

from decimal import Decimal
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from core.middleware.mobile_level_a_middleware import mobile_path_allowed_for_level_a
from stock.services.prep_cajas import (
    PreparacionError, _cantidad_codigo, _coincide_codigo, _compatible,
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
        self.assertEqual(_cantidad_codigo("D42", self.linea), (Decimal(6), "Display"))
        self.assertEqual(_cantidad_codigo("B42", self.linea), (Decimal(24), "Bulto"))
        self.assertIsNone(_cantidad_codigo("NOEXISTE", self.linea))

    def test_etiqueta_333_conserva_su_cantidad(self):
        self.assertEqual(_cantidad_codigo("333000420007", self.linea), (Decimal(7), "Etiqueta 333"))
        self.assertTrue(_coincide_codigo("333000420007", self.linea))
        self.assertFalse(_coincide_codigo("333000430007", self.linea))
        with self.assertRaises(PreparacionError):
            _cantidad_codigo("333000420000", self.linea)

    def test_lote_impide_conversion_a_display(self):
        with self.assertRaises(PreparacionError):
            _cantidad_codigo("D42", {**self.linea, "lote": "Si"})

    def test_pantalla_y_api_disponibles_en_movil(self):
        self.assertTrue(mobile_path_allowed_for_level_a("/stock/preparacion-cajas/"))
        self.assertTrue(mobile_path_allowed_for_level_a("/stock/api/preparacion-cajas/42/lectura/"))


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

    def _registrar(self, consumido=None, lineas=None):
        with patch("stock.services.prep_cajas._tx", self._fake_tx), \
             patch("stock.services.prep_cajas._bloquear_preparacion", return_value=1), \
             patch("stock.services.prep_cajas._lineas", return_value=lineas or [self.linea]), \
             patch("stock.services.prep_cajas._consumos", return_value=consumido or {}):
            return registrar_lectura("prueba", 44, 1, "7790012345678", self.KEY, 7)

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

    def test_rechaza_otro_domicilio(self):
        with self.assertRaisesMessage(PreparacionError, "otra sucursal"):
            self._registrar(lineas=[{**self.linea, "pedido": 101,
                                     "id_cliente_domicilio": 202, "destino": "Sucursal 2"}])
