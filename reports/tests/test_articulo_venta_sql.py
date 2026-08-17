# -*- coding: utf-8 -*-
"""Contrato: reportes de artículos de venta excluyen tipo_art = Gasto."""
from django.test import SimpleTestCase

from reports.services.articulo_venta_sql import (
    TIPO_ART_GASTO,
    sql_excluir_tipo_art_gasto,
)
from reports.services.ventas_marcas_mensual_rules import sql_base_where_clauses
from reports.services.ventas_mensuales_licenciatarios_query import build_anet_sales_sql


class ArticuloVentaSqlTests(SimpleTestCase):
    def test_helper_excluye_gasto_y_conserva_sin_articulo(self):
        clause = sql_excluir_tipo_art_gasto("art")
        self.assertEqual(TIPO_ART_GASTO, "Gasto")
        self.assertIn("art.IDArt IS NULL", clause)
        self.assertIn("art.tipo_art IS NULL", clause)
        self.assertIn("art.tipo_art <> 'Gasto'", clause)

    def test_alias_personalizado(self):
        clause = sql_excluir_tipo_art_gasto("a")
        self.assertIn("a.tipo_art <> 'Gasto'", clause)
        self.assertNotIn("art.tipo_art", clause)

    def test_vmm_where_base_incluye_gasto(self):
        joined = " ".join(sql_base_where_clauses())
        self.assertIn("art.tipo_art <> 'Gasto'", joined)

    def test_vml_sql_anet_incluye_gasto(self):
        sql = build_anet_sales_sql()
        self.assertIn("art.tipo_art <> 'Gasto'", sql)
