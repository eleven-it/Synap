"""Contrato de los 14 KPI Stock V45 y protección del costo."""
from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.stock_v45 import (
    STOCK_V45_KEYS,
    fetch_stock_v45,
)


def _filters():
    return DashboardFilters(
        base_empresa="best_sox", fecha_referencia=date(2026, 10, 8),
        fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 8),
        depositos_filtro=(6,),
    )


class StockV45Tests(SimpleTestCase):
    def test_14_kpi_y_costo_restringido(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (847696733.54, 295864, 724, 46, 253303, 0),
            (0, 0, 0),
            (55803, 38467, 259911163.9, 210232913.9),
            (0,),
        ]
        cursor.fetchall.return_value = []
        data = fetch_stock_v45(cursor, _filters(), show_costs=False)
        self.assertEqual(set(data["kpis"]), set(STOCK_V45_KEYS))
        self.assertEqual(data["kpis"]["articulos_con_stock"], 724)
        self.assertEqual(data["kpis"]["unidades_disponibles"], 295864)
        self.assertIsNone(data["kpis"]["stock_valorizado"])
        self.assertIsNone(data["kpis"]["valor_entradas"])
        self.assertIsNone(data["series_depositos"])
        self.assertEqual(cursor.execute.call_count, 5)
        for call in cursor.execute.call_args_list:
            self.assertIn("dep.CodDeposito IN (%s)", call.args[0])
            self.assertIn(6, call.args[1])

    def test_presentacion_desconocida_falla(self):
        with self.assertRaises(ValueError):
            fetch_stock_v45(MagicMock(), _filters(), presentation="pallet")
