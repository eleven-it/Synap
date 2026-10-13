"""Las dimensiones de rutas compartidas no se exponen bajo alcance territorial."""
from datetime import date

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.logistica_v45_detail import list_logistica_v45_detail


class LogisticaTerritoryTests(SimpleTestCase):
    def test_dimension_de_zona_no_consulta_rutas_compartidas(self):
        class NoGlobalCursor:
            def execute(self, *_args, **_kwargs):
                raise AssertionError("No consultar dimensiones globales")

        filters = DashboardFilters(
            "best_sox", date(2911, 7, 24), date(2911, 7, 1),
            date(2911, 7, 24), puntos_venta=(2,), sucursales_filtro=(1,),
        )
        result = list_logistica_v45_detail(
            NoGlobalCursor(), filters, view="por_zona",
        )
        self.assertEqual(result["motivo"], "sin_alcance_territorial")
