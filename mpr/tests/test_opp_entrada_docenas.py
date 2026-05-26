"""Tests unitarios: entrada OPP por docenas + unidades (factor docena fijo 12)."""
from django.http import QueryDict
from django.test import SimpleTestCase

from mpr.views import (
    UNIDADES_POR_DOCENA_OPP,
    _opp_cantidad_unidades_desde_post,
    _opp_max_distribuible_unidades,
)


class OppCantidadUnidadesDesdePostTest(SimpleTestCase):
    """Valida `_opp_cantidad_unidades_desde_post` sin base de datos."""

    def test_nueve_docenas_mas_dos_unidades_es_ciento_diez(self):
        post = QueryDict(mutable=True)
        post["opp_comp_100_dep_3_docenas"] = "9"
        post["opp_comp_100_dep_3_unidades"] = "2"
        self.assertEqual(_opp_cantidad_unidades_desde_post(post, 100, 3), 110)

    def test_cero_docenas_solo_unidades_equivalente_legacy(self):
        post = QueryDict(mutable=True)
        post["opp_comp_1_dep_5_docenas"] = "0"
        post["opp_comp_1_dep_5_unidades"] = "110"
        self.assertEqual(_opp_cantidad_unidades_desde_post(post, 1, 5), 110)

    def test_campos_ausentes_son_cero(self):
        post = QueryDict(mutable=True)
        self.assertEqual(_opp_cantidad_unidades_desde_post(post, 99, 1), 0)

    def test_negativos_y_no_numericos_se_tratan_como_cero_o_max_cero(self):
        post = QueryDict(mutable=True)
        post["opp_comp_10_dep_2_docenas"] = "-5"
        post["opp_comp_10_dep_2_unidades"] = "-3"
        self.assertEqual(_opp_cantidad_unidades_desde_post(post, 10, 2), 0)

        post2 = QueryDict(mutable=True)
        post2["opp_comp_10_dep_2_docenas"] = "x"
        post2["opp_comp_10_dep_2_unidades"] = "y"
        self.assertEqual(_opp_cantidad_unidades_desde_post(post2, 10, 2), 0)

    def test_constante_docena_es_doce(self):
        self.assertEqual(UNIDADES_POR_DOCENA_OPP, 12)

    def test_max_distribuible_respeta_cero_sin_fallback_a_disponible(self):
        comp = {"max_distribuible_unidades": 0, "disponible_unidades": 1885}
        self.assertEqual(_opp_max_distribuible_unidades(comp), 0)

    def test_max_distribuible_usa_disponible_si_max_no_existe(self):
        comp = {"disponible_unidades": 120}
        self.assertEqual(_opp_max_distribuible_unidades(comp), 120)
