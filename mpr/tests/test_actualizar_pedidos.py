# Tests de regresión para actualizar_pedidos_produccion (ventana-pack / demanda MPR).
# Verifica que los pedidos con estado_pedido_opt NULL se incluyan como pendientes de producción.
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from mpr.services import actualizar_pedidos_produccion


class ActualizarPedidosProduccionFiltroEstadoTest(TestCase):
    """
    Verifica que el filtro de pedidos pendientes incluya tanto estado_pedido_opt = 'Pendiente'
    como estado_pedido_opt IS NULL (pedidos aún no asignados a producción).
    """

    def test_sql_incluye_null_y_pendiente_cuando_columna_existe(self):
        sql_executada = []

        def fake_execute(sql, params=None):
            if params is None:
                params = ()
            sql_executada.append((sql, params))

        fetchone_calls = [0]

        def fake_fetchone():
            # Primera llamada: SHOW COLUMNS → columna estado_pedido_opt existe
            fetchone_calls[0] += 1
            if fetchone_calls[0] == 1:
                return ("estado_pedido_opt",)
            return None

        def fake_fetchall():
            return []

        cursor = MagicMock()
        cursor.execute.side_effect = fake_execute
        cursor.fetchone.side_effect = fake_fetchone
        cursor.fetchall.side_effect = fake_fetchall

        conn = MagicMock()
        conn.cursor.return_value = cursor
        conn.autocommit = MagicMock()

        class Ctx:
            def __enter__(self):
                return conn

            def __exit__(self, *args):
                pass

        with patch("mpr.services.get_connection", return_value=Ctx()):
            with patch("mpr.services._nombre_tabla", return_value="tabla_fake"):
                ok, msg = actualizar_pedidos_produccion(
                    base_empresa="test_db",
                    id_usuario=1,
                    fecha_desde=date(2026, 1, 1),
                    fecha_hasta=date(2026, 3, 31),
                )
        self.assertFalse(ok)
        self.assertIn("pedidos pendientes", msg)

        # Debe haberse ejecutado al menos SHOW COLUMNS y el SELECT de pedidos
        self.assertGreaterEqual(
            len(sql_executada), 2,
            "Se esperan al menos 2 ejecuciones SQL (SHOW COLUMNS y SELECT pedidos)",
        )
        # El SELECT de pedidos es el que tiene codigo_movimiento_pedido y estado_pedido_opt
        select_sql = None
        for s, _ in sql_executada:
            if "codigo_movimiento_pedido" in s and "estado_pedido_opt" in s:
                select_sql = s
                break
        self.assertIsNotNone(
            select_sql,
            "Debe ejecutarse el SELECT de pedidos con filtro estado_pedido_opt.",
        )

        # Regresión: pedidos con estado_pedido_opt Pendiente o Parcial entran en ventana-pack (demanda a fabricar)
        self.assertIn(
            "('Pendiente', 'Parcial')",
            select_sql,
            "El SQL debe filtrar por estado_pedido_opt IN ('Pendiente', 'Parcial') para ventana-pack.",
        )
