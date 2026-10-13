"""Las fotos financieras sin clave territorial nunca se exponen con filtro."""
from datetime import date

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.financiero_v45 import _cash_and_checks


class FinancieroV45ScopeTests(SimpleTestCase):
    def test_saldos_globales_no_se_consultan_con_pv(self):
        class NoGlobalCursor:
            def execute(self, *_args, **_kwargs):
                raise AssertionError("Se consultó un saldo global")

        filters = DashboardFilters(
            "best_sox", date(2026, 10, 12), date(2026, 10, 1),
            date(2026, 10, 12), puntos_venta=(2,),
        )
        result = _cash_and_checks(NoGlobalCursor(), filters)
        self.assertIsNone(result["bancos"])
        self.assertIsNone(result["cheques_cartera"])
