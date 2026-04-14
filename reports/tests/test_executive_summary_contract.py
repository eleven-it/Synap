"""Contrato numérico mínimo del servicio de resumen ejecutivo (sin MySQL)."""
from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.executive_sales_summary import run_executive_summary


class ExecutiveSummaryContractTests(SimpleTestCase):
    def test_run_executive_summary_con_cursor_vacio_devuelve_estructura(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(0.0,))
        cursor.fetchall = MagicMock(return_value=[])

        out = run_executive_summary(cursor, date(2026, 4, 1), [], [])

        self.assertIn("fecha_referencia", out)
        self.assertIn("kpis", out)
        self.assertIn("serie_horaria", out)
        self.assertEqual(len(out["serie_horaria"]), 24)
        self.assertIn("serie_7_dias", out)
        self.assertEqual(len(out["serie_7_dias"]), 7)
        self.assertIn("split_mayorista_minorista", out)
