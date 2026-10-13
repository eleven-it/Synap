"""Contrato de alcance de Compras V45."""
from datetime import date

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.compras_v45 import _scope


class ComprasV45ScopeTests(SimpleTestCase):
    def test_filtro_de_compras_usa_sucursal_sin_pv(self):
        filters = DashboardFilters(
            "best_sox", date(2026, 10, 12), date(2026, 10, 1),
            date(2026, 10, 12), sucursales_filtro=(3,), puntos_venta=(9,),
        )
        clause, params = _scope("cp", filters)
        self.assertIn("cp.CodSucursal IN (%s)", clause)
        self.assertNotIn("id_pv", clause)
        self.assertEqual(params, [3])
