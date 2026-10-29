import unittest

from ecom.services.catalogo_producto import _foto_url_articulo


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
