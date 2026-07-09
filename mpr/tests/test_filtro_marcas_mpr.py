"""Tests del filtro de marcas en pantallas operativas MPR."""

from unittest.mock import patch

from django.test import SimpleTestCase

from mpr.services import _filtrar_ids_por_marcas, listar_tablero_por_articulo


class TestFiltrarIdsPorMarcas(SimpleTestCase):
    @patch("mpr.services._fetch_codigo_marca_articulo")
    def test_sin_marcas_devuelve_todos(self, mock_fetch):
        mock_fetch.return_value = {1: 10, 2: 20}
        result = _filtrar_ids_por_marcas("emp", [1, 2], None)
        self.assertEqual(result, {1, 2})
        mock_fetch.assert_not_called()

    @patch("mpr.services._fetch_codigo_marca_articulo")
    def test_filtra_por_codigo_marca(self, mock_fetch):
        mock_fetch.return_value = {1: 10, 2: 20, 3: 10}
        result = _filtrar_ids_por_marcas("emp", [1, 2, 3], [10])
        self.assertEqual(result, {1, 3})


class TestListarTableroPorArticuloMarcas(SimpleTestCase):
    @patch("mpr.services._filtrar_ids_por_marcas", return_value=set())
    @patch("mpr.services.listar_demanda_pack_desde_pedidos", return_value=[])
    @patch("mpr.services._query_enviados_todos_componentes", return_value={10: 5})
    def test_sin_componentes_tras_filtro_marca(self, *_mocks):
        filas = listar_tablero_por_articulo("emp", marcas_incluidos=[99])
        self.assertEqual(filas, [])
