"""Extractors: CI/FV no filtran proveedor; PD/ES/VD sí."""

import inspect

from django.test import SimpleTestCase

from mtrix.extractors import ci, es, fv, pd, vd
from datetime import date

from mtrix.extractors.base import (
    calcular_rango_exportacion,
    conservar_si_ean_o_venta,
    parse_proveedores,
)


class ExtractorsContratoTests(SimpleTestCase):
    def test_ci_fv_no_aceptan_filtro_proveedor(self):
        self.assertNotIn("codigo_prov", inspect.signature(ci.fetch_rows).parameters)
        self.assertNotIn("codigo_prov", inspect.signature(fv.fetch_rows).parameters)
        self.assertNotIn("CodigoProveedor", ci._SQL)
        self.assertNotIn("CodigoProveedor", fv._SQL)
        self.assertNotIn("nombre_cliente", fv._SQL)

    def test_pd_es_vd_filtran_proveedor_cuando_no_es_todos(self):
        sql_pd, params_pd = pd._sql("23")
        self.assertIn("CodigoProveedor IN (", sql_pd)
        self.assertEqual(params_pd, [23])
        sql_todos, params_todos = pd._sql("TODOS")
        self.assertNotIn("CodigoProveedor", sql_todos)
        self.assertEqual(params_todos, [])

        sql_es, params_es = es._sql("29")
        self.assertIn("CodigoProveedor IN (", sql_es)
        self.assertEqual(params_es, [29])

        from mtrix.tests import export_cfg_test

        cfg = export_cfg_test(pvnf=False)
        sql_vd, params_vd = vd._sql(cfg, "31")
        self.assertIn("CodigoProveedor IN (", sql_vd)
        self.assertIn(31, params_vd)
        self.assertIn("punto_venta.cont", sql_vd)
        self.assertIn("LEFT JOIN distrito", sql_vd)

        cfg_todos = export_cfg_test(pvnf=True)
        sql_vd_todos, _params = vd._sql(cfg_todos, "TODOS")
        self.assertNotIn("CodigoProveedor", sql_vd_todos)
        self.assertNotIn("punto_venta.cont", sql_vd_todos)

    def test_pd_es_vd_un_sql_con_in_para_lista(self):
        sql_pd, params_pd = pd._sql(codigos_prov=["23", "29", "31"])
        self.assertIn("IN (%s, %s, %s)", sql_pd)
        self.assertEqual(params_pd, [23, 29, 31])
        sql_es, params_es = es._sql(codigos_prov=["23", "29"])
        self.assertEqual(params_es, [23, 29])
        from mtrix.tests import export_cfg_test

        sql_vd, params_vd = vd._sql(export_cfg_test(), codigos_prov=["23", "29"])
        self.assertIn("IN (%s, %s)", sql_vd)
        self.assertEqual(params_vd[2:], [23, 29])

    def test_parse_proveedores_vacio_es_todos(self):
        self.assertEqual(parse_proveedores(""), ["TODOS"])
        self.assertEqual(parse_proveedores("23,29"), ["23", "29"])

    def test_ci_solo_clientes_con_ventas(self):
        self.assertIn("cc.Codigo IS NOT NULL", ci._SQL)
        self.assertIn("distrito.cod_postal", ci._SQL)
        self.assertIn("AS CIUDAD", ci._SQL)
        self.assertNotIn("NULLIF", ci._SQL)
        self.assertIn("'9400'", ci._SQL)

    def test_vd_cep_default_9400(self):
        from mtrix.tests import export_cfg_test

        sql, _ = vd._sql(export_cfg_test(), "TODOS")
        self.assertIn("'9400'", sql)
        self.assertNotIn("'NA') AS CEP", sql)

    def test_vd_excluye_anulado_y_rec(self):
        from mtrix.tests import export_cfg_test

        sql, _ = vd._sql(export_cfg_test(), "TODOS")
        self.assertIn("Anulado = 'No'", sql)
        self.assertIn("TipoComprobante <> 'REC'", sql)


class RangoExportacionTests(SimpleTestCase):
    def test_primera_corrida_usa_dias(self):
        self.assertEqual(
            calcular_rango_exportacion(hoy="2026-08-27", dias=5),
            ("2026-08-22", "2026-08-27"),
        )

    def test_marca_agua_solapa_un_dia(self):
        self.assertEqual(
            calcular_rango_exportacion(
                hoy="2026-08-27",
                last_vd_enviado_hasta=date(2026, 8, 26),
            ),
            ("2026-08-26", "2026-08-27"),
        )

    def test_personalizada_solo_si_flag(self):
        self.assertEqual(
            calcular_rango_exportacion(
                hoy="2026-08-27",
                last_vd_enviado_hasta=date(2026, 8, 20),
                usar_personalizada=True,
                fecha_inicio=date(2026, 6, 1),
                fecha_final=date(2026, 8, 1),
            ),
            ("2026-06-01", "2026-08-01"),
        )
        self.assertEqual(
            calcular_rango_exportacion(
                hoy="2026-08-27",
                last_vd_enviado_hasta=date(2026, 8, 20),
                usar_personalizada=False,
                fecha_inicio=date(2026, 6, 1),
                fecha_final=date(2026, 8, 1),
            ),
            ("2026-08-20", "2026-08-27"),
        )


class EanCatalogoTests(SimpleTestCase):
    def test_conserva_ean_valido_aunque_no_haya_venta(self):
        self.assertTrue(conservar_si_ean_o_venta({"EAN": "7798130180152", "ID_ART": 9}, set()))

    def test_descarta_ean_cero_sin_venta(self):
        self.assertFalse(conservar_si_ean_o_venta({"EAN": "0", "ID_ART": 9}, set()))

    def test_conserva_ean_cero_si_hubo_venta(self):
        self.assertTrue(conservar_si_ean_o_venta({"EAN": "0", "ID_ART": 9}, {9}))
