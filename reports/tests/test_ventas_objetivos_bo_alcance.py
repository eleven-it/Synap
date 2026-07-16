# -*- coding: utf-8 -*-
"""Alcance comercial en informe ventas-objetivos-vs-bo (REQ-OBJ-02)."""

import unittest
from unittest.mock import MagicMock, patch

from reports.services.ventas_objetivos_bo_runner import (
    _sql_in_viajantes,
    run_ventas_objetivos_vs_bo,
)


class TestSqlInViajantes(unittest.TestCase):
    def test_vacio(self):
        sql, params = _sql_in_viajantes("cl", [])
        self.assertEqual(sql, "")
        self.assertEqual(params, [])

    def test_in_clause(self):
        sql, params = _sql_in_viajantes("cl_bo", [3, 5])
        self.assertIn("cl_bo.CodViajante IN", sql)
        self.assertEqual(params, [3, 5])


class TestRunnerAlcanceVacio(unittest.TestCase):
    @patch("reports.services.ventas_objetivos_bo_runner.alcance_objetivos_cod_viajante", return_value=[])
    @patch("reports.services.ventas_objetivos_bo_runner.ctx_desde_runner", return_value={"id_vendedor_usr": 9})
    def test_alcance_vacio_sin_datos(self, _ctx, _alc):
        report = MagicMock()
        report.slug = "ventas-objetivos-vs-bo"
        report.name = "Objetivos"
        report.category = "ventas"
        report.version = 1
        user = MagicMock()
        user.base_empresa = "emp1"
        payload = {
            "filters": {
                "base_empresa": "emp1",
                "fecha_inicio": "2026-01-01",
                "fecha_fin": "2026-01-31",
            }
        }
        result = run_ventas_objetivos_vs_bo(report, payload, user)
        self.assertEqual(result.data, [])
        self.assertTrue(any("alcance" in str(n).lower() for n in (result.notes or [])))


class TestAgruparInformeArbol(unittest.TestCase):
    @patch("ventas.services.objetivos_mysql.usar_vista_arbol_org", return_value=False)
    def test_off_mantiene_arbol_vendedor(self, _u):
        from ventas.services.objetivos_mysql import agrupar_jerarquia_informe_arbol_org

        arbol = [{"cod_viajante": 5, "nombre_vendedor": "V5", "children": []}]
        out = agrupar_jerarquia_informe_arbol_org("emp1", {"id_vendedor_usr": 5}, arbol)
        self.assertEqual(out, arbol)
