"""Tests del idle timeout y cierre del pool MySQL."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from core.mysql_pool import MySQLConnectionPool


class MySQLPoolIdleTestCase(SimpleTestCase):
    def setUp(self):
        MySQLConnectionPool._pools.clear()

    def tearDown(self):
        MySQLConnectionPool.close_all_pools()
        MySQLConnectionPool._pools.clear()

    def _pool(self, idle_seconds=30, max_connections=5):
        return MySQLConnectionPool(
            host="127.0.0.1",
            port=3306,
            user="u",
            password="p",
            max_connections=max_connections,
            idle_seconds=idle_seconds,
        )

    @patch.object(MySQLConnectionPool, "_create_connection")
    @patch.object(MySQLConnectionPool, "_is_connection_alive", return_value=True)
    @patch.object(MySQLConnectionPool, "_init_connection_session")
    def test_idle_cero_cierra_al_devolver(self, _init, _alive, create):
        conn = MagicMock()
        create.return_value = conn
        pool = self._pool(idle_seconds=0)
        with pool.get_connection("administranet89"):
            pass
        self.assertEqual(len(pool._available_connections), 0)
        conn.close.assert_called()
        self.assertEqual(pool._connection_count, 0)

    @patch.object(MySQLConnectionPool, "_create_connection")
    @patch.object(MySQLConnectionPool, "_is_connection_alive", return_value=True)
    @patch.object(MySQLConnectionPool, "_init_connection_session")
    def test_idle_expira_conexiones_disponibles(self, _init, _alive, create):
        conn = MagicMock()
        create.return_value = conn
        pool = self._pool(idle_seconds=1)
        with pool.get_connection("administranet89"):
            pass
        self.assertEqual(len(pool._available_connections), 1)
        # Forzar timestamp antiguo
        c, db, _ = pool._available_connections[0]
        pool._available_connections[0] = (c, db, time.monotonic() - 5)
        closed = pool._purge_idle_unlocked()
        self.assertEqual(closed, 1)
        self.assertEqual(len(pool._available_connections), 0)

    def test_close_all_pools(self):
        p = self._pool()
        MySQLConnectionPool._pools["x"] = p
        n = MySQLConnectionPool.close_all_pools()
        self.assertGreaterEqual(n, 1)
