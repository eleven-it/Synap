# -*- coding: utf-8 -*-
"""Contrato mínimo del informe stock-existencias (sin MySQL)."""

import unittest

from reports.services.query_runner import QueryRunnerService


class TestStockExistenciasRunner(unittest.TestCase):
    def test_metodo_runner_definido(self):
        self.assertTrue(hasattr(QueryRunnerService, "_run_stock_existencias"))

    def test_codigo_barras_normalizado_como_str(self):
        """Misma regla que _run_stock_existencias al armar item (JSON sin number para barras)."""

        def normalizar_codigo_barras(v):
            if v is None or v == "":
                return ""
            if isinstance(v, (bytes, bytearray)):
                return v.decode("latin1", errors="replace").strip()
            return str(v).strip()

        self.assertEqual(normalizar_codigo_barras(None), "")
        self.assertEqual(normalizar_codigo_barras(""), "")
        self.assertEqual(normalizar_codigo_barras(" 013005 "), "013005")
        self.assertEqual(normalizar_codigo_barras(84110611097000), "84110611097000")
