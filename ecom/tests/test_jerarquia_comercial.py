# Tests jerarquía comercial (REQ-JER-02): 1-padre, subárbol, rol.

import unittest
from unittest.mock import MagicMock, patch

from ecom.services.jerarquia_comercial import (
    desactivar_vinculo_supervisor_vendedor,
    listar_arbol_jerarquia,
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

    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_mover_vendedor_con_flag(self, mock_pool_fn):
        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1, 5, "Si")  # id, cod_supervisor actual, activo
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        ok, msg = vincular_supervisor_vendedor("emp1", 10, 30, mover=True)
        self.assertTrue(ok)
        self.assertIn("movido", msg.lower())
        conn.commit.assert_called_once()

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

    @patch("ecom.services.jerarquia_comercial._validar_sin_ciclo_gerente_supervisor", return_value=(True, ""))
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_vincular_gs_guarda_ids_usuarios(self, mock_pool_fn, _ciclo):
        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        ok, _ = vincular_gerente_supervisor(
            "emp1", 1, 2, id_usuario_gerente=41, id_usuario_supervisor=72
        )

        self.assertTrue(ok)
        sql, params = cursor.execute.call_args_list[-1][0]
        self.assertIn("id_usuario_gerente", sql)
        self.assertIn("id_usuario_supervisor", sql)
        self.assertEqual(params[:4], (1, 2, 41, 72))

    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_vincular_sv_guarda_id_usuario_supervisor(self, mock_pool_fn):
        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        ok, _ = vincular_supervisor_vendedor(
            "emp1", 2, 30, id_usuario_supervisor=72
        )

        self.assertTrue(ok)
        sql, params = cursor.execute.call_args_list[-1][0]
        self.assertIn("id_usuario_supervisor", sql)
        self.assertEqual(params[:3], (2, 30, 72))


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
    def test_busca_dos_usuarios_con_mismo_viajante(self, mock_pool_fn):
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
                "nombre_puesto": "Supervisor",
                "nombre_viajante": "Juan V",
            },
            {
                "id_usuario": 2,
                "cod_usuario": "juan2",
                "nombre_usuario": "Juan",
                "apellido_usuario": "Bis",
                "cod_viajante": 10,
                "nombre_puesto": "Supervisor",
                "nombre_viajante": "Juan V",
            },
        ]
        cursor.description = [
            ("id_usuario",), ("cod_usuario",), ("nombre_usuario",), ("apellido_usuario",),
            ("cod_viajante",), ("nombre_puesto",), ("nombre_viajante",),
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        rows = buscar_usuarios_jerarquia("emp1", "juan", rol="gerente")
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["id_usuario"] for row in rows], [1, 2])
        self.assertEqual([row["cod_viajante"] for row in rows], [10, 10])
        self.assertEqual([row["etiqueta"] for row in rows], ["Juan Perez", "Juan Bis"])
        self.assertNotIn("@", rows[0]["etiqueta"])
        self.assertNotIn("vía", rows[0]["etiqueta"])


class TestEtiquetasArbol(unittest.TestCase):
    @patch("ecom.services.jerarquia_comercial.etiquetas_usuarios_por_id")
    @patch("ecom.services.jerarquia_comercial.etiquetas_viajantes_usuarios")
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_prioriza_id_usuario_para_etiqueta(self, mock_pool_fn, mock_viajantes, mock_usuarios):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [
                {
                    "id": 1,
                    "cod_gerente": 1,
                    "cod_supervisor": 2,
                    "id_usuario_gerente": 41,
                    "id_usuario_supervisor": 72,
                    "activo": "Si",
                }
            ],
            [
                {
                    "id": 2,
                    "cod_supervisor": 2,
                    "cod_vendedor": 30,
                    "id_usuario_supervisor": 72,
                    "activo": "Si",
                }
            ],
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool
        mock_viajantes.return_value = {1: "Victoria Martinez", 2: "Supervisor .", 30: "Vendedor"}
        mock_usuarios.return_value = {41: "Gerente Correcto", 72: "Priscila Borgo"}

        arbol = listar_arbol_jerarquia("emp1")

        self.assertEqual(arbol["vinculos_gs"][0]["etiqueta_gerente"], "Gerente Correcto")
        self.assertEqual(arbol["vinculos_gs"][0]["etiqueta_supervisor"], "Priscila Borgo")
        self.assertEqual(arbol["vinculos_sv"][0]["etiqueta_supervisor"], "Priscila Borgo")

    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_gerente_excluye_puestos_no_habilitados(self, mock_pool_fn):
        from ecom.services.jerarquia_comercial import buscar_usuarios_jerarquia

        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {
                "id_usuario": 1,
                "cod_usuario": "dep",
                "nombre_usuario": "Ana",
                "apellido_usuario": "Depo",
                "cod_viajante": 5,
                "nombre_puesto": "Depósito",
                "nombre_viajante": "",
            },
            {
                "id_usuario": 2,
                "cod_usuario": "ven",
                "nombre_usuario": "Beto",
                "apellido_usuario": "Venta",
                "cod_viajante": 6,
                "nombre_puesto": "Ventas",
                "nombre_viajante": "",
            },
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        rows = buscar_usuarios_jerarquia("emp1", "", rol="supervisor")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["etiqueta"], "Beto Venta")

    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_vendedor_busca_viajantes(self, mock_pool_fn):
        from ecom.services.jerarquia_comercial import buscar_usuarios_jerarquia

        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"cod_viajante": 21, "nombre_viajante": "Pedro Viajante"},
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        rows = buscar_usuarios_jerarquia("emp1", "Pedro", rol="vendedor")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["etiqueta"], "Pedro Viajante")
        self.assertIsNone(rows[0]["id_usuario"])

    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_vendedor_excluye_placeholders(self, mock_pool_fn):
        from ecom.services.jerarquia_comercial import buscar_usuarios_jerarquia

        pool = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"cod_viajante": 1, "nombre_viajante": "-Ninguno-"},
            {"cod_viajante": 2, "nombre_viajante": ""},
            {"cod_viajante": 3, "nombre_viajante": "   ---   "},
            {"cod_viajante": 4, "nombre_viajante": "Ana Real"},
        ]
        conn = MagicMock()
        conn.cursor.return_value = cursor
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool_fn.return_value = pool

        rows = buscar_usuarios_jerarquia("emp1", "", rol="vendedor")
        etiquetas = [r["etiqueta"] for r in rows]
        self.assertEqual(rows and len(rows), 1)
        self.assertEqual(rows[0]["etiqueta"], "Ana Real")
        self.assertNotIn("-Ninguno-", etiquetas)
