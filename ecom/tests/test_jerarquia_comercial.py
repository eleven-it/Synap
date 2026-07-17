# Tests jerarquía comercial (REQ-JER-02): 1-padre, subárbol, rol.

import unittest
from unittest.mock import MagicMock, patch

from ecom.services.jerarquia_comercial import (
    desactivar_vinculo_supervisor_vendedor,
    rol_de,
    subarbol_de,
    vincular_gerente_supervisor,
    vincular_supervisor_vendedor,
)


def _mock_conn_fetchone(rows_sequence):
    """Context manager mock para pool.get_connection con fetchone encadenado."""
    cursor = MagicMock()
    cursor.fetchone.side_effect = rows_sequence

    conn = MagicMock()
    conn.cursor.return_value = cursor

    pool = MagicMock()
    pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
    pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    return pool, cursor, conn


class TestRolDe(unittest.TestCase):
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_gerente(self, mock_pool_fn):
        pool, cursor, _ = _mock_conn_fetchone([(1,), None, None])
        mock_pool_fn.return_value = pool
        self.assertEqual(rol_de("emp1", 100), "gerente")

    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_supervisor(self, mock_pool_fn):
        pool, cursor, _ = _mock_conn_fetchone([None, (1,), None])
        mock_pool_fn.return_value = pool
        self.assertEqual(rol_de("emp1", 50), "supervisor")

    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_vendedor(self, mock_pool_fn):
        pool, cursor, _ = _mock_conn_fetchone([None, None, (1,)])
        mock_pool_fn.return_value = pool
        self.assertEqual(rol_de("emp1", 42), "vendedor")


class TestSubarbolDe(unittest.TestCase):
    @patch("ecom.services.jerarquia_comercial.rol_de", return_value="vendedor")
    def test_vendedor_solo_propio(self, _rol):
        with patch("ecom.services.jerarquia_comercial.get_mysql_pool"):
            self.assertEqual(subarbol_de("emp1", 42, "vendedor"), [42])

    @patch("ecom.services.jerarquia_comercial.rol_de", return_value="supervisor")
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_supervisor_incluye_vendedores(self, mock_pool_fn, _rol):
        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [{"cod_vendedor": 20}, {"cod_vendedor": 21}]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        self.assertEqual(subarbol_de("emp1", 10, "supervisor"), [10, 20, 21])


class TestUnPadre(unittest.TestCase):
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_rechaza_segundo_supervisor_activo(self, mock_pool_fn):
        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1, 5, "Si")
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        ok, msg = vincular_supervisor_vendedor("emp1", 10, 30)
        self.assertFalse(ok)
        self.assertIn("supervisor activo", msg.lower())

    @patch("ecom.services.jerarquia_comercial._validar_sin_ciclo_gerente_supervisor", return_value=(True, ""))
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_vincular_gs_ok_nuevo(self, mock_pool_fn, _ciclo):
        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        ok, msg = vincular_gerente_supervisor("emp1", 1, 2)
        self.assertTrue(ok)
        conn.commit.assert_called_once()


class TestDesactivar(unittest.TestCase):
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_desactivar_sv(self, mock_pool_fn):
        pool = MagicMock()
        cursor = MagicMock()
        cursor.rowcount = 1
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        ok, _ = desactivar_vinculo_supervisor_vendedor("emp1", 42)
        self.assertTrue(ok)


class TestBuscarUsuariosJerarquia(unittest.TestCase):
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_busca_y_deduplica_por_viajante(self, mock_pool_fn):
        from ecom.services.jerarquia_comercial import buscar_usuarios_jerarquia

        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "id_usuario": 1,
                "cod_usuario": "juan",
                "nombre_usuario": "Juan",
                "apellido_usuario": "Perez",
                "cod_viajante": 10,
                "nombre_viajante": "Juan V",
                "permiso_supervisor_venta": "Si",
            },
            {
                "id_usuario": 2,
                "cod_usuario": "juan2",
                "nombre_usuario": "Juan",
                "apellido_usuario": "Bis",
                "cod_viajante": 10,
                "nombre_viajante": "Juan V",
                "permiso_supervisor_venta": "No",
            },
        ]
        cursor.description = [
            ("id_usuario",), ("cod_usuario",), ("nombre_usuario",), ("apellido_usuario",),
            ("cod_viajante",), ("nombre_viajante",), ("permiso_supervisor_venta",),
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        rows = buscar_usuarios_jerarquia("emp1", "juan")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cod_viajante"], 10)
        self.assertIn("Juan", rows[0]["etiqueta"])
        self.assertIn("vía. 10", rows[0]["etiqueta"])
