"""Catálogo de rutas para Entregas (filtro por chofer y pendientes)."""
from __future__ import annotations

from unittest.mock import MagicMock

from django.test import SimpleTestCase

from logistica.services.lista_comprobantes_rutas import listar_rutas_catalogo_entregas


class TestListarRutasCatalogoEntregas(SimpleTestCase):
    def test_sin_ids_chofer_no_consulta_mysql(self):
        conn = MagicMock()
        self.assertEqual(listar_rutas_catalogo_entregas(conn, []), [])
        conn.cursor.assert_not_called()
