"""Tests: parte de producción por docenas + unidades (factor docena fijo 12)."""
from django.http import QueryDict
from django.test import SimpleTestCase

from mpr.views import (
    UNIDADES_POR_DOCENA_OPP,
    _parte_cantidad_unidades_desde_post,
    _parte_lineas_desde_post,
)


class ParteCantidadUnidadesDesdePostTest(SimpleTestCase):
    """Valida helpers del parte sin base de datos."""

    def test_nueve_docenas_mas_dos_unidades(self):
        post = QueryDict(mutable=True)
        post["parte_art_100_op_3_docenas"] = "9"
        post["parte_art_100_op_3_unidades"] = "2"
        self.assertEqual(_parte_cantidad_unidades_desde_post(post, 100, 3), 110)

    def test_lineas_desde_post_agrega_solo_positivas(self):
        post = QueryDict(mutable=True)
        post["parte_art_10_op_1_docenas"] = "1"
        post["parte_art_10_op_1_unidades"] = "0"
        post["parte_art_10_op_2_docenas"] = "0"
        post["parte_art_10_op_2_unidades"] = "0"
        lineas = _parte_lineas_desde_post(post)
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0]["id_articulo"], 10)
        self.assertEqual(lineas[0]["id_operario"], 1)
        self.assertEqual(int(lineas[0]["cantidad"]), 12)

    def test_suma_dos_operarios_mismo_articulo(self):
        post = QueryDict(mutable=True)
        post["parte_art_42_op_1_docenas"] = "0"
        post["parte_art_42_op_1_unidades"] = "4"
        post["parte_art_42_op_2_docenas"] = "0"
        post["parte_art_42_op_2_unidades"] = "4"
        lineas = _parte_lineas_desde_post(post)
        self.assertEqual(len(lineas), 2)
        self.assertEqual(sum(int(l["cantidad"]) for l in lineas), 8)

    def test_constante_docena_es_doce(self):
        self.assertEqual(UNIDADES_POR_DOCENA_OPP, 12)
