"""Contrato de los 14 KPI Stock V45 y protección del costo."""
from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.stock_v45 import (
    STOCK_V45_KEYS,
    fetch_stock_v45,
)
from reports.services.executive_dashboard.stock_v45_detail import list_stock_v45_detail


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

    def test_detalle_costo_exige_permiso(self):
        cursor = MagicMock()
        with self.assertRaises(PermissionError):
            list_stock_v45_detail(cursor, _filters(), kpi="stock_valorizado")
        cursor.execute.assert_not_called()

    def test_detalle_de_movimientos_conserva_deposito_y_periodo(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1, 12)
        cursor.description = [(name,) for name in (
            "id", "fecha", "articulo", "codigo_manual", "codigo_sistema",
            "deposito", "documento", "importe", "stock_actual", "stock_minimo",
            "punto_pedido", "stock_maximo", "reservado", "pendiente_recibir",
        )]
        cursor.fetchall.return_value = [(
            17, date(2026, 10, 8), "Producto", "P", "8", "Terminado",
            "FA 10", 12, None, None, None, None, None, None,
        )]
        data = list_stock_v45_detail(cursor, _filters(), kpi="salidas_periodo")
        self.assertEqual(data["total_registros"], 1)
        self.assertEqual(data["filas"][0]["fecha"], "2026-10-08")
        self.assertEqual(data["filas"][0]["importe"], 12)
        self.assertFalse(data["foto_actual"])
        for call in cursor.execute.call_args_list:
            self.assertIn("dep.CodDeposito IN (%s)", call.args[0])
            self.assertIn(6, call.args[1])
