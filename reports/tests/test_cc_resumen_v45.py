"""Límites de acceso del Resumen gerencial V45."""
from datetime import date

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.resumen_v45 import (
    _purchase_account_source,
    _sales_account_source,
    _snapshots,
)
from reports.services.executive_dashboard.resumen_v45_detail import list_resumen_v45_detail


class ResumenV45ScopeTests(SimpleTestCase):
    def test_consultas_de_cuenta_corriente_aceptan_parametros_mysql(self):
        filters = DashboardFilters(
            "best_sox", date(2026, 10, 12),
            date(2026, 10, 1), date(2026, 10, 12),
        )
        for has_rv in (False, True):
            source, params = _sales_account_source(filters, gross=False, has_rv=has_rv)
            formatted = source % tuple(params)
            self.assertIn("LIKE 'CTA/CTE%'", formatted)
            self.assertNotIn("CTA/CTE%%", formatted)
        source, params = _purchase_account_source(filters)
        formatted = source % tuple(params)
        self.assertIn("LIKE 'CTA/CTE%'", formatted)

    def test_no_consulta_saldos_globales_con_filtro_territorial(self):
        class NoGlobalCursor:
            def execute(self, *_args, **_kwargs):
                raise AssertionError("No consultar saldos globales con PV/sucursal")

        filters = DashboardFilters(
            "best_sox", date(2026, 10, 12),
            date(2026, 10, 1), date(2026, 10, 12),
            puntos_venta=(1,),
        )
        values = _snapshots(NoGlobalCursor(), filters)
        self.assertIsNone(values["bancos_actual"])
        self.assertIsNone(values["vencimiento_cobrar"])

    def test_detalle_global_tambien_rechaza_filtro_territorial(self):
        class NoGlobalCursor:
            def execute(self, *_args, **_kwargs):
                raise AssertionError("No consultar detalle global con PV/sucursal")

        filters = DashboardFilters(
            "best_sox", date(2026, 10, 12),
            date(2026, 10, 1), date(2026, 10, 12),
            puntos_venta=(1,),
        )
        for key in ("bancos_actual", "vencimiento_cobrar"):
            result = list_resumen_v45_detail(NoGlobalCursor(), filters, key=key)
            self.assertFalse(result["disponible"])
            self.assertEqual(result["motivo"], "sin_alcance_territorial")
