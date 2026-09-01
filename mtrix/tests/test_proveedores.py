"""Búsqueda predictiva de proveedores Mtrix."""

from unittest.mock import patch

from django.test import TestCase

from mtrix.services.proveedores import (
    buscar_proveedores_mtrix,
    obtener_proveedores_por_codigos,
    proveedores_seleccionados_config,
)


class ProveedoresMtrixTests(TestCase):
    @patch("mtrix.services.proveedores.buscar_proveedores")
    def test_buscar_mapea_codigo_nombre_cuit(self, mock_buscar):
        mock_buscar.return_value = [
            {"Codigo": 5, "Nombre": "DIVERSEY DE ARGENTINA SA", "CUIT": "30-50000000-1"},
            {"Codigo": None, "Nombre": "BASURA", "CUIT": ""},
        ]
        filas = buscar_proveedores_mtrix("emp", "diver")
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["codigo"], 5)
        self.assertEqual(filas[0]["nombre"], "DIVERSEY DE ARGENTINA SA")
        mock_buscar.assert_called_once_with("emp", "diver", limite=15)

    @patch("mtrix.services.proveedores.mysql_cursor")
    def test_obtener_por_codigos(self, mock_cursor_cm):
        cursor = mock_cursor_cm.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            {"Codigo": 5, "Nombre": "DIVERSEY DE ARGENTINA SA", "CUIT": "30-1"},
        ]
        filas = obtener_proveedores_por_codigos("emp", ["5", "5", "x"])
        self.assertEqual(filas[0]["codigo"], 5)
        cursor.execute.assert_called_once()
        args = cursor.execute.call_args[0]
        self.assertIn("IN (%s)", args[0])
        self.assertEqual(args[1], [5])

    def test_seleccionados_vacio_es_todos(self):
        self.assertEqual(proveedores_seleccionados_config("emp", ""), [])
        self.assertEqual(proveedores_seleccionados_config("emp", "TODOS"), [])

    @patch("mtrix.services.proveedores.obtener_proveedores_por_codigos")
    def test_seleccionados_resuelve_lista(self, mock_obt):
        mock_obt.return_value = [{"codigo": 5, "nombre": "DIVERSEY", "cuit": ""}]
        filas = proveedores_seleccionados_config("emp", "5")
        mock_obt.assert_called_once_with("emp", ["5"])
        self.assertEqual(filas[0]["codigo"], 5)
