# Tests ecom_config_mysql y filtro tabla vendedor-cliente.

import unittest
from unittest.mock import MagicMock, patch

from ecom.services.ecom_config_mysql import fuente_vendedor_asignacion, leer_valor_configuracion_ecom
from ecom.services.vendedor_asignacion_sql import where_vendedor_cliente


class TestEcomConfigMysql(unittest.TestCase):
    @patch("ecom.services.ecom_config_mysql.get_mysql_pool")
    def test_leer_valor_default_si_no_hay_fila(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        self.assertEqual(leer_valor_configuracion_ecom("emp1", "clave_x", "legacy"), "legacy")

    def test_fuente_desde_sesion(self):
        self.assertEqual(
            fuente_vendedor_asignacion("emp1", "cliente", sesion_valor="tabla"),
            "tabla",
        )
        self.assertEqual(
            fuente_vendedor_asignacion("emp1", "cliente", sesion_valor="legacy"),
            "legacy",
        )


class TestWhereVendedorClienteTabla(unittest.TestCase):
    def test_modo_tabla_supervisor_con_cargo(self):
        sess = {
            "todos_clientes": "No",
            "supervisor_venta": "Si",
            "id_vendedor_usr": 5,
            "vendedor_a_cargo": [7, 9],
        }
        sql, params = where_vendedor_cliente("emp1", sess, fuente="tabla")
        self.assertIn("vendedores_clientes_asignacion", sql)
        self.assertNotIn("cliente.CodViajante", sql)
        self.assertEqual(params, [5, 7, 9])

    def test_modo_legacy_vendedor_simple(self):
        sess = {
            "todos_clientes": "No",
            "supervisor_venta": "No",
            "id_vendedor_usr": 3,
        }
        sql, params = where_vendedor_cliente("emp1", sess, fuente="legacy")
        self.assertIn("cliente.CodViajante", sql)
        self.assertEqual(params, [3])
