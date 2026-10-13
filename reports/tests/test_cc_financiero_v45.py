"""Las fotos financieras sin clave territorial nunca se exponen con filtro."""
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.financiero_v45 import _cash_and_checks
from reports.services.executive_dashboard.financiero_v45_detail import (
    _check_source, list_financiero_v45_detail,
)


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

    def test_cheques_sin_clave_territorial_no_se_consultan_con_sucursal(self):
        class NoGlobalCursor:
            def execute(self, *_args, **_kwargs):
                raise AssertionError("Se consultó un cheque global con sucursal")

        filters = DashboardFilters(
            "best_sox", date(2026, 10, 13), date(2026, 10, 1),
            date(2026, 10, 13), sucursales_filtro=(2,),
        )
        result = list_financiero_v45_detail(
            NoGlobalCursor(), filters, view="cheques_cartera", mode="ranking",
        )
        self.assertFalse(result["disponible"])
        self.assertEqual(result["motivo"], "sin_alcance_territorial")

    def test_condiciones_del_detalle_coinciden_con_tarjetas(self):
        cartera = _check_source("cheques_cartera")
        propios = _check_source("cheques_emitidos")
        rechazados = _check_source("cheques_rechazados")
        self.assertIn("ch.Encartera,'')='SI'", cartera)
        self.assertIn("ch.pagado,'')='NO'", propios)
        self.assertIn("ch.en_nd_proveedor,'')='NO'", propios)
        self.assertIn("UNION ALL", rechazados)
        self.assertEqual(rechazados.count("ch.rechazado,'')='SI'"), 1)
        self.assertEqual(rechazados.count("ch.Rechazado,'')='SI'"), 1)

    def test_ranking_cheques_concilia_total_y_agrupacion(self):
        class Cursor:
            def __init__(self):
                self.queries = []
            def execute(self, sql, params):
                self.queries.append((sql, params))
            def fetchone(self):
                return (2, 150)
            def fetchall(self):
                return [("Banco A", 100, 1), ("Banco B", 50, 1)]

        filters = DashboardFilters(
            "best_sox", date(2026, 10, 13), date(2026, 10, 1), date(2026, 10, 13),
        )
        cursor = Cursor()
        with patch("reports.services.executive_dashboard.financiero_v45_detail._table_exists", return_value=True):
            result = list_financiero_v45_detail(
                cursor, filters, view="cheques_cartera", mode="ranking", group="banco",
            )
        self.assertEqual(result["total_importe"], 150)
        self.assertEqual(result["total_cantidad"], 2)
        self.assertEqual(sum(row["importe"] for row in result["filas"]), result["total_importe"])
        self.assertIn("q.banco etiqueta", cursor.queries[1][0])
