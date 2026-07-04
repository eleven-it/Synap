"""
Tests de restricciones de catálogo por punto de venta (Fase P3).
"""

from django.test import TestCase, SimpleTestCase

from ecom.models import EcomCatalogoRestriccionPV
from ecom.services.catalogo_producto import _construir_where_catalogo
from ecom.services.catalogo_restricciones import (
    aplicar_restricciones_a_filtros,
    restricciones_para_pv,
)


class TestConstruirWhereExclusiones(SimpleTestCase):
    def test_sin_exclusiones(self):
        where, params = _construir_where_catalogo({})
        self.assertNotIn("NOT IN", where)
        self.assertEqual(params, [])

    def test_excluir_articulos_y_rubros(self):
        where, params = _construir_where_catalogo(
            {"excluir_articulos": [10, 20], "excluir_rubros": [3]}
        )
        self.assertIn("articulo.IDArt NOT IN (%s,%s)", where)
        self.assertIn("articulo.CodigoRubro NOT IN (%s)", where)
        self.assertEqual(params, [10, 20, 3])

    def test_ignora_ids_invalidos(self):
        where, params = _construir_where_catalogo({"excluir_articulos": [None, "x", 5]})
        self.assertIn("articulo.IDArt NOT IN (%s)", where)
        self.assertEqual(params, [5])


class TestRestriccionesPV(TestCase):
    def setUp(self):
        EcomCatalogoRestriccionPV.objects.create(
            base_empresa="emp1", id_punto_venta=7, tipo="articulo", valor_id=100
        )
        EcomCatalogoRestriccionPV.objects.create(
            base_empresa="emp1", id_punto_venta=7, tipo="articulo", valor_id=101
        )
        EcomCatalogoRestriccionPV.objects.create(
            base_empresa="emp1", id_punto_venta=7, tipo="rubro", valor_id=5
        )
        # inactiva → no debe aparecer
        EcomCatalogoRestriccionPV.objects.create(
            base_empresa="emp1", id_punto_venta=7, tipo="articulo", valor_id=999, activo=False
        )
        # otro PV → no debe aparecer
        EcomCatalogoRestriccionPV.objects.create(
            base_empresa="emp1", id_punto_venta=8, tipo="articulo", valor_id=200
        )

    def test_restricciones_para_pv(self):
        r = restricciones_para_pv("emp1", 7)
        self.assertCountEqual(r.get("excluir_articulos", []), [100, 101])
        self.assertEqual(r.get("excluir_rubros", []), [5])
        self.assertNotIn(999, r.get("excluir_articulos", []))

    def test_pv_sin_restricciones(self):
        self.assertEqual(restricciones_para_pv("emp1", 999), {})

    def test_sin_pv(self):
        self.assertEqual(restricciones_para_pv("emp1", None), {})

    def test_aplicar_a_filtros_preserva_existentes(self):
        filtros = {"rubro": 2, "excluir_articulos": [1]}
        out = aplicar_restricciones_a_filtros(filtros, "emp1", 7)
        self.assertEqual(out["rubro"], 2)
        self.assertCountEqual(out["excluir_articulos"], [1, 100, 101])
        # no muta el original
        self.assertEqual(filtros["excluir_articulos"], [1])
