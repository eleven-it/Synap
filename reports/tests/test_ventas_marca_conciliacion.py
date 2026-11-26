"""Regresión del descuadre marca vs vendedor del tablero Jesels."""
from datetime import date
from unittest import TestCase
from unittest.mock import patch

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.ventas_marca_conciliacion import (
    list_ventas_marca_conciliada,
)


class SalesCursor:
    def __init__(self):
        self.calls = []
        self.kind = None

    def execute(self, sql, params=None):
        self.calls.append((sql, list(params or [])))
        if "SELECT COALESCE(a.CodigoMarca,0)" in sql:
            self.kind = "stock"
        elif "SELECT COALESCE(cc.id_marca,0)" in sql:
            self.kind = "notes"
        elif "SELECT COALESCE(SUM(" in sql:
            self.kind = "header"
        else:
            raise AssertionError(sql)

    def fetchall(self):
        if self.kind == "stock":
            return [(1, "PUM", 1000, 20), (2, "PUS", 300, 5)]
        if self.kind == "notes":
            return [(1, "PUM", 100, 0, 1), (2, "PUS", 0, 20, 1),
                    (0, "", 50, 10, 2)]
        raise AssertionError(self.kind)

    def fetchone(self):
        if self.kind == "header":
            return (1080, 5)
        raise AssertionError(self.kind)


class MarcaConciliacionTest(TestCase):
    def filters(self):
        return DashboardFilters(
            base_empresa="administranet", fecha_referencia=date(2026, 10, 31),
            fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 31),
            sucursales_filtro=(1,), puntos_venta=(2,),
        )

    @patch("reports.services.executive_dashboard.ventas_marca_conciliacion._has_id_marca", return_value=True)
    @patch("reports.services.executive_dashboard.ventas_marca_conciliacion._table_exists", return_value=True)
    def test_marca_nc_nd_y_ajustes_concilian_kpi(self, _tables, _field):
        cursor = SalesCursor()
        result = list_ventas_marca_conciliada(cursor, self.filters())
        rows = {row["etiqueta"]: row for row in result["filas"]}

        self.assertEqual(result["total_importe"], 1080)
        self.assertEqual(sum(row["importe"] for row in result["filas"]), 1080)
        self.assertEqual(rows["PUM"]["importe"], 900)
        self.assertEqual(rows["PUM"]["nc"], 100)
        self.assertEqual(rows["PUS"]["importe"], 320)
        self.assertEqual(rows["PUS"]["nd"], 20)
        self.assertEqual(rows["NC sin marca asignada"]["importe"], -50)
        self.assertEqual(rows["ND sin marca asignada"]["importe"], 10)
        self.assertEqual(rows["Facturas sin artículos"]["importe"], 5)
        self.assertEqual(rows["Descuentos / ajustes al pie"]["importe"], -105)
        self.assertEqual(result["total_cantidad"], 25)

        stock, notes, header = cursor.calls
        for sql, params in cursor.calls:
            self.assertIn("cc.id_pv IN (%s)", sql)
            self.assertIn("cc.CodSucursal IN (%s)", sql)
            self.assertIn([2, 1], [params[index:index + 2]
                                  for index in range(len(params) - 1)])
        self.assertIn("st.visualiza_ensamble", stock[0])
        self.assertIn("NOT EXISTS", notes[0])
        self.assertIn("id_marca", notes[0])
        self.assertIn("'NDA','NDB','NDC','NDE','NDM'", header[0])

    @patch("reports.services.executive_dashboard.ventas_marca_conciliacion._has_id_marca", return_value=False)
    @patch("reports.services.executive_dashboard.ventas_marca_conciliacion._table_exists", return_value=True)
    def test_sin_id_marca_no_inventa_asignacion(self, _tables, _field):
        cursor = SalesCursor()
        result = list_ventas_marca_conciliada(cursor, self.filters())
        self.assertFalse(result["disponible"])
        self.assertEqual(result["motivo"], "campo_id_marca_faltante")
        self.assertEqual(cursor.calls, [])

    @patch("reports.services.executive_dashboard.ventas_marca_conciliacion._period_rows")
    @patch("reports.services.executive_dashboard.ventas_marca_conciliacion._has_id_marca", return_value=True)
    @patch("reports.services.executive_dashboard.ventas_marca_conciliacion._table_exists", return_value=True)
    def test_marca_solo_del_periodo_anterior_muestra_importes_actuales_cero(
            self, _tables, _field, period_rows):
        current = {"filas": [{"tipo_fila": "marca", "id_marca": 1,
                              "etiqueta": "PUM", "importe": 100, "cantidad": 2}], "kpi": 100}
        previous = {"filas": [{"tipo_fila": "marca", "id_marca": 2,
                               "etiqueta": "PUS", "importe": 50, "neto": 60,
                               "nc": 10, "nd": 0, "cantidad": 3}], "kpi": 50}
        period_rows.side_effect = [current, previous]

        result = list_ventas_marca_conciliada(SalesCursor(), self.filters(), compare=True)
        old_brand = next(row for row in result["filas"] if row["id_marca"] == 2)
        self.assertEqual(old_brand["importe"], 0)
        self.assertEqual(old_brand["anterior"], 50)
        self.assertEqual(old_brand["neto"], 0)
        self.assertEqual(old_brand["nc"], 0)
        self.assertEqual(old_brand["cantidad"], 0)
        self.assertEqual(result["total_cantidad"], 2)
