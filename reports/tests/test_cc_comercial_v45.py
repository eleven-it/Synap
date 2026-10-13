"""Fórmulas comerciales V45 y alcance de las consultas."""
from datetime import date
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.comercial_v45 import (
    fetch_comercial_ventas_v45,
    list_comercial_v45_detail,
)


def _filters(**overrides):
    data = dict(
        base_empresa="best_sox",
        fecha_referencia=date(2026, 10, 8),
        fecha_inicio=date(2026, 10, 1),
        fecha_fin=date(2026, 10, 8),
        sucursales_filtro=(1,),
        puntos_venta=(2, 3),
    )
    data.update(overrides)
    return DashboardFilters(**data)


class ComercialV45Tests(SimpleTestCase):
    def test_16_kpi_y_permiso_costos(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (0, 0, 180, 513873093.5, 108, 368254613.61, 95),
            (171207874.10, 82, 23657365.04, 0),
            (72,), (1,),
        ]
        payload = fetch_comercial_ventas_v45(cursor, _filters(), include_profit=False)
        kpis = payload["kpis"]
        self.assertEqual(kpis["facturas"], 82)
        self.assertEqual(kpis["pedidos"], 180)
        self.assertEqual(kpis["pedidos_en_remito"], 72)
        self.assertEqual(kpis["rentabilidad"], None)
        self.assertEqual(kpis["margen_porcentaje"], None)
        self.assertEqual(len({
            key for key in kpis if key not in ("venta_base_rentabilidad", "costo_ventas")
        }), 16)
        sql, params = cursor.execute.call_args_list[1].args
        self.assertIn("cc.id_pv IN (%s,%s)", sql)
        self.assertIn("cc.CodSucursal IN (%s)", sql)
        self.assertEqual(params[:2], ["2026-10-01", "2026-10-09"])
        self.assertEqual(params[2:], [2, 3, 1])

    def test_gross_usa_importe_cobro_en_creditos(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(0,) * 7, (0,) * 4, (0,), (0,)]
        fetch_comercial_ventas_v45(cursor, _filters(), gross=True)
        sql = cursor.execute.call_args_list[1].args[0]
        self.assertIn("cc.ImporteCobro", sql)
        self.assertIn("cc.ImporteVenta", sql)

    def test_comparacion_periodo_equivalente(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (0,) * 7, (100, 2, 0, 0), (0,), (0,),
            (0,) * 7, (80, 2, 0, 0), (0,), (0,),
        ]
        cursor.fetchall.return_value = []
        payload = fetch_comercial_ventas_v45(cursor, _filters(), compare_previous=True)
        self.assertEqual(payload["comparacion"]["periodo"], {
            "inicio": "2026-09-23", "fin": "2026-09-30",
        })
        self.assertEqual(payload["comparacion"]["diferencias"]["ventas_netas"], 20)
        previous_docs_params = cursor.execute.call_args_list[4].args[1]
        self.assertEqual(previous_docs_params[:2], ["2026-09-23", "2026-10-01"])

    def test_detalle_costos_requiere_permiso(self):
        with self.assertRaises(PermissionError):
            list_comercial_v45_detail(
                MagicMock(), _filters(), kpi="rentabilidad", allow_cost=False,
            )

    def test_detalle_paginado_interseca_pv_y_busqueda(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (42, 1234)
        cursor.fetchall.return_value = [
            (123, "2026-10-08", "FA", "A-1", 5, "PUMA", 1234),
        ]
        out = list_comercial_v45_detail(
            cursor, _filters(busqueda="PUMA", limit=25, offset=25),
            kpi="ventas_netas", order="importe_desc",
        )
        self.assertEqual(out["total_registros"], 42)
        self.assertEqual(out["filas"][0]["importe"], 1234)
        sql, params = cursor.execute.call_args_list[1].args
        self.assertIn("d.id_pv IN (%s,%s)", sql)
        self.assertIn("d.CodSucursal IN (%s)", sql)
        self.assertIn("ORDER BY importe DESC", sql)
        self.assertEqual(params[-2:], [25, 25])
