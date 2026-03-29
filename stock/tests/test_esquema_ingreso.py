# Tests para verificación de esquema antes del alta de movimiento de stock.
from unittest.mock import patch, MagicMock

from django.test import TestCase

from core.services.administranet_stock import (
    verificar_esquema_ingreso_movimiento,
    ESQUEMA_INGRESO_MOVIMIENTO,
)


class TestVerificarEsquemaIngresoMovimiento(TestCase):
    """Verificar que verificar_esquema_ingreso_movimiento detecte tablas/campos faltantes."""

    def _mock_cursor_tablas_y_columnas(self, tablas_existentes, columnas_por_tabla):
        """Simula SHOW TABLES y SHOW COLUMNS; tablas_existentes = set de nombres en minúscula."""
        def fake_execute(sql, params=None):
            pass
        def fake_fetchall():
            # SHOW TABLES devuelve una columna por fila (nombre de la tabla)
            return [{list(k)[0]: k[list(k)[0]]} for k in [{"Tables_in_x": t} for t in tablas_existentes]]
        cursor = MagicMock()
        cursor.execute = fake_execute
        call_count = [0]
        all_tables = list(ESQUEMA_INGRESO_MOVIMIENTO.keys())
        def fetchall():
            call_count[0] += 1
            if call_count[0] == 1:
                return [{"Tables_in_db": t} for t in tablas_existentes]
            # Llamadas siguientes: SHOW COLUMNS para cada tabla (mismo orden que ESQUEMA_INGRESO_MOVIMIENTO)
            idx = (call_count[0] - 2) % len(all_tables)
            tabla = all_tables[idx]
            cols = columnas_por_tabla.get(tabla, [])
            return [{"Field": c} for c in cols]
        cursor.fetchall = fetchall
        return cursor

    @patch("core.services.administranet_stock.mysql_cursor")
    def test_esquema_ok_devuelve_true_y_lista_vacia(self, mock_mysql_cursor):
        tablas = {t.lower() for t in ESQUEMA_INGRESO_MOVIMIENTO.keys()}
        columnas_por_tabla = {t: list(cols) for t, cols in ESQUEMA_INGRESO_MOVIMIENTO.items()}
        cursor = MagicMock()
        call_idx = [0]
        def fetchall():
            call_idx[0] += 1
            if call_idx[0] == 1:
                return [{"Tables_in_x": t} for t in tablas]
            idx = (call_idx[0] - 2) % len(ESQUEMA_INGRESO_MOVIMIENTO)
            tabla = list(ESQUEMA_INGRESO_MOVIMIENTO.keys())[idx]
            return [{"Field": c} for c in ESQUEMA_INGRESO_MOVIMIENTO[tabla]]
        cursor.fetchall = fetchall
        cursor.execute = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=cursor)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_mysql_cursor.return_value = mock_ctx

        ok, errores = verificar_esquema_ingreso_movimiento("base_test")
        self.assertTrue(ok, "Con todas las tablas y columnas debe devolver ok=True")
        self.assertEqual(errores, [], "No debe haber errores")

    @patch("core.services.administranet_stock.mysql_cursor")
    def test_tabla_faltante_devuelve_error_con_tabla_sin_campo(self, mock_mysql_cursor):
        # Solo existe codmov; faltan el resto de tablas
        tablas = {"codmov"}
        cursor = MagicMock()
        call_idx = [0]
        def fetchall():
            call_idx[0] += 1
            if call_idx[0] == 1:
                return [{"Tables_in_x": t} for t in tablas]
            # Segunda llamada: SHOW COLUMNS de codmov (única tabla que existe)
            return [{"Field": c} for c in ESQUEMA_INGRESO_MOVIMIENTO["codmov"]]
        cursor.fetchall = fetchall
        cursor.execute = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=cursor)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_mysql_cursor.return_value = mock_ctx

        ok, errores = verificar_esquema_ingreso_movimiento("base_test")
        self.assertFalse(ok)
        self.assertGreater(len(errores), 0)
        # Debe haber al menos un error de "Falta la tabla"
        mensajes_tabla = [e for e in errores if e.get("campo") is None and e.get("tabla") and "Falta la tabla" in (e.get("mensaje") or "")]
        self.assertGreater(len(mensajes_tabla), 0, "Debe haber errores por tabla faltante")
