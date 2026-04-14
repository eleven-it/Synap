# -*- coding: utf-8 -*-
"""Contrato mínimo del informe stock-existencias (sin MySQL)."""

import unittest

from reports.services.query_runner import QueryRunnerService


class TestStockExistenciasRunner(unittest.TestCase):
    def test_metodo_runner_definido(self):
        self.assertTrue(hasattr(QueryRunnerService, "_run_stock_existencias"))
