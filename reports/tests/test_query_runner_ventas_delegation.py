"""QueryRunnerService delega totales ventas/remitos/pedidos en ventas_metrics."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from reports.services.query_runner import QueryRunnerService


class QueryRunnerVentasDelegationTests(SimpleTestCase):
    def setUp(self):
        self.runner = QueryRunnerService(MagicMock())
        self.cursor = MagicMock()

    @patch(
        "reports.services.executive_dashboard.ventas_metrics.get_ventas_netas_total",
        return_value=1500.0,
    )
    def test_get_ventas_netas_total_delega(self, mock_fn):
        out = self.runner._get_ventas_netas_total(
            self.cursor,
            "2026-05-01",
            "2026-05-11",
            sucursales=[1, 2],
            puntos_venta=[10],
            clientes_excluidos=["99"],
        )
        self.assertEqual(out, 1500.0)
        mock_fn.assert_called_once_with(
            self.cursor,
            "2026-05-01",
            "2026-05-11",
            sucursales=[1, 2],
            puntos_venta=[10],
            clientes_excluidos=["99"],
        )

    @patch(
        "reports.services.executive_dashboard.ventas_metrics.get_remitos_no_facturados_total",
        return_value=200.0,
    )
    def test_get_remitos_no_facturados_total_delega(self, mock_fn):
        out = self.runner._get_remitos_no_facturados_total(
            self.cursor, "2026-05-01", "2026-05-11", sucursales=[3]
        )
        self.assertEqual(out, 200.0)
        mock_fn.assert_called_once_with(
            self.cursor,
            "2026-05-01",
            "2026-05-11",
            sucursales=[3],
            puntos_venta=None,
            clientes_excluidos=None,
        )

    @patch(
        "reports.services.executive_dashboard.ventas_metrics.get_pedidos_pendientes_total",
        return_value=75.5,
    )
    def test_get_pedidos_pendientes_total_delega_sin_fecha(self, mock_fn):
        out = self.runner._get_pedidos_pendientes_total(
            self.cursor,
            "2026-05-01",
            "2026-05-11",
            filtrar_por_fecha=False,
        )
        self.assertEqual(out, 75.5)
        mock_fn.assert_called_once_with(
            self.cursor,
            "2026-05-01",
            "2026-05-11",
            sucursales=None,
            puntos_venta=None,
            clientes_excluidos=None,
            filtrar_por_fecha=False,
        )
