# Tests servicio asignación vendedor-cliente/marca.

import unittest
from unittest.mock import MagicMock, patch

from ventas.services.vendedor_asignacion_mysql import (
    asignar_items_bulk,
    listar_items_asignacion,
    listar_resumen_vendedores,
)


class TestVendedorAsignacionMysql(unittest.TestCase):
    @patch("ventas.services.vendedor_asignacion_mysql.get_mysql_pool")
    def test_listar_resumen_cliente(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [(12, "Juan", 5), (3, "María", 2)],
        ]
        cursor.fetchone.return_value = (7,)
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        ok, err, rows, sin = listar_resumen_vendedores("emp1", "cliente")
        self.assertTrue(ok)
        self.assertEqual(err, "")
        self.assertEqual(len(rows), 2)
        self.assertEqual(sin, 7)

    def test_modo_invalido_items(self):
        ok, err, items, total = listar_items_asignacion("emp1", "otro")
        self.assertFalse(ok)
        self.assertEqual(items, [])
        self.assertEqual(total, 0)

    @patch("ventas.services.vendedor_asignacion_mysql.get_mysql_pool")
    def test_asignar_desasignar(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [(101,)]
        cursor.rowcount = 1
        conn.cursor.return_value = cursor
        mock_pool.return_value.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        mock_pool.return_value.get_connection.return_value.__exit__ = MagicMock(return_value=False)

        ok, err, n = asignar_items_bulk("emp1", "cliente", [101], None, {"cod_usuario": "admin"})
        self.assertTrue(ok)
        self.assertEqual(n, 1)
        self.assertTrue(any("DELETE" in str(c[0][0]) for c in cursor.execute.call_args_list))
