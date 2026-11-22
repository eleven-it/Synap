import unittest
from unittest.mock import patch

from ecom.services.catalogo_producto import _foto_local_para_articulo, _foto_url_articulo, fotos_urls_articulos


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

    @patch("ecom.services.catalogo_producto._fotos_locales_bestsox", return_value={"14000555-550": "ecom/img/bestsox_productos/14000555-550.png"})
    def test_foto_local_coincide_con_codigo_de_color_y_talle(self, _mapa):
        fila = (123, "64", "", "14000555-550 XL", "Puma Boxer")
        self.assertEqual(
            _foto_local_para_articulo(fila),
            "/static/ecom/img/bestsox_productos/14000555-550.png",
        )
        self.assertEqual(
            _foto_local_para_articulo(fila, site_url="https://bestsox.test"),
            "https://bestsox.test/static/ecom/img/bestsox_productos/14000555-550.png",
        )

    @patch("ecom.services.catalogo_producto._es_empresa_bestsox", return_value=True)
    @patch("ecom.services.catalogo_producto._fotos_locales_bestsox", return_value={"14000555-550": "ecom/img/bestsox_productos/14000555-550.png"})
    def test_foto_local_completa_lote_sin_reemplazar_foto_erp(self, _mapa, _empresa):
        class Cursor:
            sql = ""
            def execute(self, sql, _params): self.sql = sql
            def fetchall(self):
                if "FROM articulo_foto" in self.sql:
                    return [(1, "https://erp.test/1.jpg", "")]
                return [(2, "64", "", "14000555-550 XL", "Puma Boxer")]

        class Conn:
            def __enter__(self): return self
            def __exit__(self, *_args): return None
            def cursor(self): return Cursor()

        with patch("ecom.services.catalogo_producto._mysql_conn", return_value=Conn()):
            fotos = fotos_urls_articulos("bestsox", [1, 2], site_url="https://bestsox.test")
        self.assertEqual(fotos[1], "https://erp.test/1.jpg")
        self.assertEqual(fotos[2], "https://bestsox.test/static/ecom/img/bestsox_productos/14000555-550.png")
