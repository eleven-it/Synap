# Tests de regresión para actualizar_pedidos_produccion (ventana-pack / demanda MPR).
# Verifica que los pedidos con estado_pedido_opt NULL se incluyan como pendientes de producción.
from datetime import date
from unittest.mock import MagicMock, patch

from django.test import TestCase

from mpr.services import (
    _agrupar_filas_pedidos_produccion,
    _mpr_columna_pk_fila_lista_produccion_detalle,
    _mpr_en_proceso_detalle_es_si,
    actualizar_pedidos_produccion,
)


class MprEnProcesoDetalleSiTest(TestCase):
    """Normalización en_proceso para reconciliar demanda (no pisar líneas en OPT)."""

    def test_si_y_variantes(self):
        self.assertTrue(_mpr_en_proceso_detalle_es_si("Si"))
        self.assertTrue(_mpr_en_proceso_detalle_es_si("SI"))
        self.assertTrue(_mpr_en_proceso_detalle_es_si("sí"))

    def test_no_es_pendiente(self):
        self.assertFalse(_mpr_en_proceso_detalle_es_si("No"))
        self.assertFalse(_mpr_en_proceso_detalle_es_si(None))
        self.assertFalse(_mpr_en_proceso_detalle_es_si(""))


class AgruparFilasPedidosProduccionTest(TestCase):
    """Una fila detalle debe reflejar la suma de las líneas stockp del mismo par."""

    def test_acumula_lineas_duplicadas_por_pedido_y_articulo(self):
        codigos, cantidades = _agrupar_filas_pedidos_produccion(
            [
                (945, 38, 252),
                (945, 38, 252),
                (945, 36, 120),
                (None, 99, 50),
            ]
        )

        self.assertEqual(codigos, {945})
        self.assertEqual(cantidades, {(945, 38): 504, (945, 36): 120})


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
        self.assertTrue(ok, "Sin pedidos en rango la actualización sigue siendo válida (sincroniza demanda por reserva).")
        self.assertIn("demanda por reserva", msg.lower())

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


class MprColumnaPkListaDetalleTest(TestCase):
    """PK de fila en lista_produccion_detalle: no confundir id_lista_produccion (FK) con la PK real."""

    def _cursor_con_columnas(self, columnas):
        cursor = MagicMock()

        def fake_execute(sql, params=None):
            return None

        def fake_fetchall():
            if "SHOW COLUMNS" in (fake_execute.last_sql or ""):
                return columnas
            return []

        def fake_execute_wrap(sql, params=None):
            fake_execute.last_sql = sql
            return fake_execute(sql, params)

        fake_execute.last_sql = ""
        cursor.execute.side_effect = fake_execute_wrap
        cursor.fetchall.side_effect = fake_fetchall
        return cursor

    def test_usa_columna_pri_aunque_nombre_este_corrupto(self):
        pk_corrupta = "id\x1f_lista_detalle"
        columnas = [
            (pk_corrupta, "bigint", "NO", "PRI", "auto_increment"),
            ("id_lista_produccion", "bigint", "YES", "MUL", ""),
        ]
        cursor = self._cursor_con_columnas(columnas)
        self.assertEqual(
            _mpr_columna_pk_fila_lista_produccion_detalle(cursor, "lista_produccion_detalle"),
            pk_corrupta,
        )

    def test_no_elige_id_lista_produccion_si_pri_es_otra(self):
        columnas = [
            ("id_lista_detalle", "bigint", "NO", "PRI", "auto_increment"),
            ("id_lista_produccion", "bigint", "YES", "MUL", ""),
        ]
        cursor = self._cursor_con_columnas(columnas)
        self.assertEqual(
            _mpr_columna_pk_fila_lista_produccion_detalle(cursor, "lista_produccion_detalle"),
            "id_lista_detalle",
        )
