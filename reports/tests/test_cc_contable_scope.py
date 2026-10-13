"""Los impuestos y ejercicios generales no se consultan bajo alcance territorial."""
from datetime import date

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.contable_v45 import _open_periods, _tax
from reports.services.executive_dashboard.contable_v45_detail import list_contable_v45_detail


class ContableTerritoryTests(SimpleTestCase):
    def test_no_consulta_datos_generales_con_sucursal(self):
        class NoGlobalCursor:
            def execute(self, *_args, **_kwargs):
                raise AssertionError("No consultar datos contables generales")

        filters = DashboardFilters(
            "best_sox", date(2026, 10, 12), date(2026, 10, 1),
            date(2026, 10, 12), sucursales_filtro=(1,), puntos_venta=(2,),
        )
        cursor = NoGlobalCursor()
        self.assertIsNone(_tax(cursor, filters)["impuestos_determinados"])
        self.assertIsNone(_open_periods(cursor, filters, exercise=True))
        for view in ("impuestos", "periodos", "ejercicios"):
            result = list_contable_v45_detail(cursor, filters, view=view)
            self.assertEqual(result["motivo"], "sin_alcance_territorial")
