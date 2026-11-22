import unittest
from unittest.mock import patch

from ecom.services.catalogo_producto import _foto_url_articulo, fotos_urls_articulos


class _CursorFoto:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.params = None

    def execute(self, sql, params):
        self.params = params
        if self.error:
            raise self.error

    def fetchall(self):
        return self.rows


class TestFotoArticulo(unittest.TestCase):
    def test_elige_url_http_del_articulo(self):
        cursor = _CursorFoto([("javascript:alert(1)", ""), ("https://ejemplo.test/foto.jpg", "")])
        self.assertEqual(_foto_url_articulo(cursor, 27), "https://ejemplo.test/foto.jpg")
        self.assertEqual(cursor.params, [27])

    def test_tabla_opcional_sin_foto(self):
        self.assertEqual(_foto_url_articulo(_CursorFoto(), 27), "")
        self.assertEqual(_foto_url_articulo(_CursorFoto(error=RuntimeError("sin tabla")), 27), "")

    def test_consulta_lotes_de_fotos_para_plantilla(self):
        class Cursor:
            batches = []
            def execute(self, _sql, params):
                self.batches.append(params)
                self.params = params
            def fetchall(self):
                return [(i, f"https://ejemplo.test/{i}.jpg", "") for i in self.params]

        class Conn:
            cursor_obj = Cursor()
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def cursor(self): return self.cursor_obj

        conn = Conn()
        with patch("ecom.services.catalogo_producto._mysql_conn", return_value=conn):
            fotos = fotos_urls_articulos("prueba", list(range(1, 452)), max_ids=5000)
        self.assertEqual(len(fotos), 451)
        self.assertEqual(len(conn.cursor_obj.batches), 2)
        self.assertEqual(fotos[451], "https://ejemplo.test/451.jpg")
