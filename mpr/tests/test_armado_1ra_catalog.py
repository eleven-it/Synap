"""Tests catálogo Armado 1ra: listado y habilitación sin N+1."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.services import (
    articulo_habilitado_armado_1ra,
    listar_packs_armado_1ra,
    _tablas_armado_1ra,
)


def _fake_mysql_cursor(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = rows[0] if rows else None

    @contextmanager
    def _ctx(*_args, **_kwargs):
        yield cursor

    return _ctx, cursor


class TablasArmado1raTest(SimpleTestCase):
    def test_resuelve_tablas_con_filas_dict_cursor(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            {"Tables_in_administranet96": "Articulo"},
            {"Tables_in_administranet96": "EN_ABM"},
            {"Tables_in_administranet96": "en_abm_formula"},
            {"Tables_in_administranet96": "otra"},
        ]
        tbl_art, tbl_abm, tbl_formula = _tablas_armado_1ra(cursor)
        self.assertEqual(tbl_art, "Articulo")
        self.assertEqual(tbl_abm, "EN_ABM")
        self.assertEqual(tbl_formula, "en_abm_formula")


class ListarPacksArmado1raTest(SimpleTestCase):
    def test_lista_packs_con_join_unico(self):
        rows = [
            {
                "id_articulo": 42,
                "codigo_articulo": "PK1RA",
                "descripcion_articulo": "Pack primera",
            }
        ]
        ctx, cursor = _fake_mysql_cursor(rows)
        with patch("mpr.services._tablas_armado_1ra", return_value=("articulo", "en_abm", "en_abm_formula")):
            with patch("mpr.services.mysql_cursor", side_effect=ctx):
                packs = listar_packs_armado_1ra("emp")
        self.assertEqual(len(packs), 1)
        self.assertEqual(packs[0]["id_articulo"], 42)
        self.assertEqual(cursor.execute.call_count, 1)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("INNER JOIN en_abm", sql)
        self.assertIn("INNER JOIN en_abm_formula", sql)
        self.assertIn("DISTINCT", sql)
        self.assertIn("MSTOCK", sql)

    def test_sin_tabla_articulo_devuelve_vacio(self):
        ctx, _cursor = _fake_mysql_cursor([])
        with patch("mpr.services._tablas_armado_1ra", return_value=(None, "en_abm", "en_abm_formula")):
            with patch("mpr.services.mysql_cursor", side_effect=ctx):
                self.assertEqual(listar_packs_armado_1ra("emp"), [])


class ArticuloHabilitadoArmado1raTest(SimpleTestCase):
    def test_habilitado_con_bom_mstock(self):
        ctx, cursor = _fake_mysql_cursor([{"ok": 1}])
        with patch("mpr.services._tablas_armado_1ra", return_value=("articulo", "en_abm", "en_abm_formula")):
            with patch("mpr.services.mysql_cursor", side_effect=ctx):
                self.assertTrue(articulo_habilitado_armado_1ra("emp", 99))
        self.assertEqual(cursor.execute.call_count, 1)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("a.IDArt = %s", sql)
        self.assertEqual(cursor.execute.call_args[0][1], [99])

    def test_no_habilitado_sin_fila(self):
        ctx, _cursor = _fake_mysql_cursor([])
        with patch("mpr.services._tablas_armado_1ra", return_value=("articulo", "en_abm", "en_abm_formula")):
            with patch("mpr.services.mysql_cursor", side_effect=ctx):
                self.assertFalse(articulo_habilitado_armado_1ra("emp", 1))
