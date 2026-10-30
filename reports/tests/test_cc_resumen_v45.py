"""Límites de acceso del Resumen gerencial V45."""
from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.resumen_v45 import (
    _purchase_account_source,
    _sales_account_source,
    _snapshots,
)
from reports.services.executive_dashboard.resumen_v45_detail import (
    _allowed_dimensions, _ranking_source, _source,
    list_resumen_v45_detail, list_resumen_v45_ranking,
)


class ResumenV45ScopeTests(SimpleTestCase):
    def test_ranking_ventas_respeta_filtros_y_fuentes(self):
        filters = DashboardFilters(
            "best_sox", date(2026, 10, 13),
            date(2026, 10, 1), date(2026, 10, 13),
            sucursales_filtro=(2,), puntos_venta=(8,),
        )
        with patch("reports.services.executive_dashboard.resumen_v45_detail._table_exists", return_value=False):
            seller, params, tables, _ = _ranking_source(None, filters, "ventas", False, "vendedor")
            self.assertIn("cc.CodViajante", seller)
            self.assertIn("cc.CodSucursal IN (%s)", seller)
            self.assertIn("cc.id_pv IN (%s)", seller)
            self.assertEqual(params[-2:], [8, 2])
            self.assertIn("viajantes", tables)
            brand, _, tables, note = _ranking_source(None, filters, "ventas", False, "marca")
            self.assertIn("st.PrecioNetoxR", brand)
            self.assertIn("st.Anulado='No'", brand)
            self.assertIn("ajustes de cabecera", note)
            self.assertIn("marca", tables)
            documents, _, required = _source(filters, "ventas", False)
            self.assertIn("c.CUIT", documents)
            self.assertIn("cc.CondVenta", documents)
            self.assertIn("importe_final", documents)
            self.assertIn("cc.id_pv punto_venta", documents)
            self.assertIn("viajantes", required)

    def test_agrupadores_corresponden_a_columnas_reales(self):
        filters = DashboardFilters(
            "best_sox", date(2026, 10, 13), date(2026, 10, 1), date(2026, 10, 13),
        )
        self.assertIn("condicion_venta", _allowed_dimensions("ventas"))
        self.assertNotIn("condicion_venta", _allowed_dimensions("compras_netas"))
        self.assertNotIn("fecha", _allowed_dimensions("bancos_actual"))
        for key, dimension, fragment in (
            ("ventas", "sucursal", "q.sucursal"),
            ("ventas", "condicion_venta", "q.condicion_venta"),
            ("ventas", "proveedor_habitual", "a.CodigoProveedor"),
            ("ventas", "actividad_iibb", "a.cod_act_iibb"),
            ("ventas", "distrito", "c.IDDistrito"),
            ("ventas", "medio_cobro", "resumen_venta_cv"),
            ("ventas", "tipo_entrega", "ped_fact"),
            ("compras_netas", "punto_venta", "q.punto_venta"),
            ("compras_netas", "categoria", "rc.nombre_categoria"),
            ("pedidos", "fecha", "DATE_FORMAT(q.fecha"),
        ):
            source, _, _, _ = _ranking_source(None, filters, key, False, dimension)
            self.assertIn(fragment, source)
        for dimension in ("medio_cobro", "tipo_entrega"):
            source, params, _, _ = _ranking_source(None, filters, "ventas", False, dimension)
            source % tuple(params)

    def test_ranking_comparacion_usa_periodo_anterior_y_conserva_negativos(self):
        filters = DashboardFilters(
            "best_sox", date(2026, 10, 13),
            date(2026, 10, 1), date(2026, 10, 13),
        )

        class Cursor:
            description = [("etiqueta",), ("importe",), ("cantidad",)]
            def __init__(self):
                self.periods = []
                self.aggregate = False
            def execute(self, query, params):
                if "FROM information_schema" in query:
                    self.aggregate = None
                elif "SELECT COALESCE(SUM(r.importe)" in query:
                    self.aggregate = True
                    self.periods.append(params[0])
                else:
                    self.aggregate = False
            def fetchone(self):
                if self.aggregate is None:
                    return (1,)
                if self.aggregate:
                    return (80, 2) if self.periods[-1] == "2026-10-01" else (120, 3)
                return None
            def fetchall(self):
                return [("Cliente A", 100, 1), ("Devolución", -20, 1)] if self.periods[-1] == "2026-10-01" else [("Cliente A", 120, 3)]

        cursor = Cursor()
        data = list_resumen_v45_ranking(cursor, filters, key="ventas", compare=True)
        self.assertEqual(cursor.periods, ["2026-10-01", "2026-09-18"])
        self.assertEqual(data["total_importe"], 80)
        self.assertEqual(data["total_anterior"], 120)
        self.assertEqual(data["filas"][1]["importe"], -20)
        self.assertEqual(data["filas"][1]["variacion"], -20)

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
            ranking = list_resumen_v45_ranking(NoGlobalCursor(), filters, key=key)
            self.assertFalse(ranking["disponible"])
            self.assertEqual(ranking["motivo"], "sin_alcance_territorial")
