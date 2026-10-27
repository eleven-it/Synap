from decimal import Decimal
import re
from unittest.mock import patch

from django.test import SimpleTestCase

from core.services.administranet_stock import _aplicar_entregas_pedi
from core.services.pedido_interno_stock import crear_pedido_interno
from core.services.stock_presentaciones import PresentacionInvalida, factor_presentacion


class PresentacionesStockTests(SimpleTestCase):
    def test_display_y_bulto_guardan_unidades_base(self):
        self.assertEqual(factor_presentacion("Unidad", 6, 2, 0), Decimal(1))
        self.assertEqual(factor_presentacion("Display", 6, 2, 0), Decimal(6))
        self.assertEqual(factor_presentacion("Bulto", 6, 2, 0), Decimal(12))
        self.assertEqual(factor_presentacion("Bulto", 6, 0, 3), Decimal(18))

    def test_lote_y_serie_solo_permiten_unidad(self):
        for bandera in ({"usa_lote": True}, {"usa_serie": True}):
            with self.assertRaises(PresentacionInvalida):
                factor_presentacion("Display", 6, 2, 0, **bandera)


class CursorPedi:
    def __init__(self):
        self.sql = []
        self.rowcount = 1
        self._last = ""

    def execute(self, sql, params=None):
        params = params or []
        assert len(re.findall(r"(?<!%)%s", sql)) == len(params), (sql, params)
        self.sql.append((sql, params))
        self._last = sql
        self.rowcount = 1

    def fetchone(self):
        if "SELECT cp.NroComprobante" in self._last:
            return ("0001-00000001", 2, 1)
        if "SELECT EXISTS" in self._last:
            return (0,)
        if "SELECT COUNT(*) FROM stockp" in self._last:
            return (0,)
        return None


class ConsumoPediTests(SimpleTestCase):
    def test_dos_renglones_crean_una_sola_relacion_y_completan(self):
        cursor = CursorPedi()
        renglones = [
            {"codmov_nro_pedi": 20, "id_stock": 101, "IDArt": 5, "_cantidad_unidades": Decimal(6)},
            {"codmov_nro_pedi": 20, "id_stock": 102, "IDArt": 6, "_cantidad_unidades": Decimal(3)},
        ]
        error = _aplicar_entregas_pedi(cursor, 30, {"nro_pedi": 20}, renglones, 1, 2)
        self.assertIsNone(error)
        self.assertEqual(sum("INSERT INTO movstock_pedi" in sql for sql, _ in cursor.sql), 1)
        self.assertEqual(sum("cantidad_entregada=LEAST" in sql for sql, _ in cursor.sql), 2)
        self.assertTrue(any("UPDATE comp_ped SET Estado" in sql and params[0] == "Completo"
                            for sql, params in cursor.sql))

    def test_no_acepta_articulo_ajeno_al_pedi(self):
        cursor = CursorPedi()
        error = _aplicar_entregas_pedi(cursor, 30, {"nro_pedi": 20}, [
            {"codmov_nro_pedi": None, "IDArt": 5, "_cantidad_unidades": Decimal(1)}], 1, 2)
        self.assertIn("Todos los renglones", error)
        self.assertEqual(cursor.sql, [])

    def test_no_acepta_deposito_proveedor_distinto(self):
        cursor = CursorPedi()
        error = _aplicar_entregas_pedi(cursor, 30, {"nro_pedi": 20}, [
            {"codmov_nro_pedi": 20, "id_stock": 101, "IDArt": 5,
             "_cantidad_unidades": Decimal(1)}], 3, 2)
        self.assertIn("depósitos", error)
        self.assertFalse(any("UPDATE stockp" in sql for sql, _ in cursor.sql))


class ConexionSimulada:
    def __init__(self, cursor):
        self.cursor_value = cursor
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def autocommit(self, value):
        self.autocommit_value = value

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class CursorCrear(CursorPedi):
    def fetchone(self):
        if "FROM codmov" in self._last:
            return (10,)
        if "FROM talonarios" in self._last:
            return (1, 7)
        if "FROM articulo" in self._last:
            return (295, "950056-01", "Media blanca", "950056", 100, "Gravado", 1, 1, "No")
        return None


class CreacionPediTests(SimpleTestCase):
    def test_crea_stockp_y_movimiento_en_una_transaccion(self):
        cursor = CursorCrear()
        conexion = ConexionSimulada(cursor)
        class Pool:
            def get_connection(self, base):
                return conexion
        with patch("core.services.pedido_interno_stock.get_depositos", return_value=[
            {"CodDeposito": 1}, {"CodDeposito": 2}]), patch(
                "core.services.pedido_interno_stock.get_mysql_pool", return_value=Pool()), patch(
                "core.services.pedido_interno_stock.datos_presentacion_articulo", return_value={
                    "lote": False, "serie": False, "unidades_display": 6,
                    "multiplicador_comp": 1, "displays_bulto": 1}):
            ok, resultado = crear_pedido_interno("administranet2", 1, 1, 1, {
                "tipo": "A deposito", "deposito_origen": 2, "deposito_destino": 1,
                "fecha": "2026-10-24", "renglones": [
                    {"id_articulo": 295, "cantidad": 2, "tipo_unidad": "Display"}],
            })
        self.assertTrue(ok, resultado)
        self.assertEqual(resultado["nro_comprobante"], "0001-00000008")
        self.assertEqual(conexion.commits, 1)
        self.assertEqual(conexion.rollbacks, 0)
        stockp = next(params for sql, params in cursor.sql if "INSERT INTO stockp" in sql)
        self.assertEqual(stockp[5], Decimal(12))
        self.assertEqual(stockp[6], Decimal(12))
        movimiento = next(params for sql, params in cursor.sql if "INSERT INTO movimiento_stock" in sql)
        self.assertEqual(movimiento[3:5], [2, 1])
