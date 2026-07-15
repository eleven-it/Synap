"""Contrato JSON mínimo — dashboard gerencial (sin MySQL)."""
from datetime import date
from dataclasses import replace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone

from reports.services.executive_dashboard.base import DashboardFilters, resolve_filters_from_query_params
from reports.services.executive_dashboard.command_center import run_command_center, _safe_legacy_area
from reports.services.executive_dashboard.cross_metrics import (
    fetch_cruzados_resumen,
    list_backorder_detalle,
)
from reports.services.executive_dashboard.exceptions import InvalidDashboardFilters
from reports.services.executive_dashboard.inventory_metrics import (
    fetch_inventario_resumen,
    list_existencias,
)
from reports.services.executive_dashboard.manufacturing_metrics import fetch_manufactura_resumen
from reports.services.executive_dashboard.purchase_metrics import fetch_compras_resumen
from reports.services.executive_dashboard.banco_metrics import fetch_tesoreria_banco_resumen
from reports.services.executive_dashboard.tesoreria_metrics import (
    fetch_tesoreria_resumen,
    list_movimientos_caja,
    _sum_saldo_cajas,
)
from reports.services.executive_dashboard.ventas_cobros_metrics import (
    fetch_ventas_cobros_resumen,
    list_cobros_detalle,
)
from reports.services.executive_dashboard.ventas_metrics import (
    fetch_ventas_resumen,
    list_pedidos_pendientes,
    list_remitos_no_facturados,
)


def _filters() -> DashboardFilters:
    return DashboardFilters(
        base_empresa="administranet_test",
        fecha_referencia=date(2026, 5, 11),
        fecha_inicio=date(2026, 5, 1),
        fecha_fin=date(2026, 5, 11),
        cod_sucursal=None,
    )


def _cursor_zeros():
    cursor = MagicMock()
    cursor.execute = MagicMock(return_value=None)
    cursor.fetchone = MagicMock(return_value=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    cursor.fetchall = MagicMock(return_value=[])
    return cursor


class ExecutiveDashboardContractTests(SimpleTestCase):
    def test_resolve_filters_periodo_default_hoy(self):
        with patch.object(timezone, "localdate", return_value=date(2026, 5, 11)):
            f = resolve_filters_from_query_params({}, base_empresa="be1")
        self.assertEqual(f.fecha_inicio, date(2026, 5, 11))
        self.assertEqual(f.fecha_fin, date(2026, 5, 11))
        self.assertEqual(f.fecha_referencia, date(2026, 5, 11))

    def test_resolve_filters_fecha_legacy_un_dia(self):
        f = resolve_filters_from_query_params(
            {"fecha": "2026-05-11"}, base_empresa="be1"
        )
        self.assertEqual(f.fecha_inicio, date(2026, 5, 11))
        self.assertEqual(f.fecha_fin, date(2026, 5, 11))

    def test_resolve_filters_intervalo_explicito(self):
        f = resolve_filters_from_query_params(
            {"fecha_inicio": "2026-05-01", "fecha_fin": "2026-05-11"},
            base_empresa="be1",
        )
        self.assertEqual(f.fecha_inicio, date(2026, 5, 1))
        self.assertEqual(f.fecha_fin, date(2026, 5, 11))
        self.assertEqual(f.fecha_referencia, date(2026, 5, 11))

    def test_resolve_filters_fechas_invertidas(self):
        with self.assertRaises(InvalidDashboardFilters):
            resolve_filters_from_query_params(
                {
                    "fecha_inicio": "2026-05-20",
                    "fecha_fin": "2026-05-01",
                },
                base_empresa="be1",
            )

    def test_fetch_ventas_resumen_estructura(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(100.0,))
        out = fetch_ventas_resumen(cursor, _filters())
        self.assertEqual(out["ventas_netas"], 100.0)
        self.assertEqual(out["remitos_no_facturados_monto"], 100.0)
        self.assertEqual(out["pedidos_pendientes_monto"], 100.0)
        self.assertEqual(out["total_operativo"], 300.0)
        self.assertTrue(out["disponible"])
        self.assertEqual(out["meta"]["definicion"], "executive-dashboard-v1")

    def test_fetch_inventario_resumen_estructura(self):
        cursor = MagicMock()
        seq = [(1000.0, 5, 2), (1,)]
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=seq)
        out = fetch_inventario_resumen(cursor, _filters())
        self.assertIn("valor_stock", out)
        sql_valor = cursor.execute.call_args_list[0][0][0]
        self.assertIn("PrecioCosto", sql_valor)
        self.assertNotIn("Precio1V", sql_valor)
        self.assertIn("productos_bajo_minimo", out)
        self.assertTrue(out["disponible"])
        sql_bajo_min = cursor.execute.call_args_list[1][0][0]
        self.assertIn("cp_res.Fecha >= %s", sql_bajo_min)

    def test_fetch_compras_resumen_estructura(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(3, 10.0, 500.0))
        out = fetch_compras_resumen(cursor, _filters())
        self.assertEqual(out["oc_pendientes_cantidad"], 3)
        self.assertEqual(out["oc_pendientes_importe"], 500.0)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("cp_oc.Fecha >= %s", sql)
        self.assertEqual(cursor.execute.call_args[0][1], ["2026-05-01", "2026-05-11"])
        notas = out["meta"]["notas_semanticas"]
        self.assertFalse(any("pendiente_vb6" in n for n in notas))

    def test_fetch_tesoreria_resumen_estructura(self):
        cursor = MagicMock()
        seq = [(0.0,), (100.0,), (50.0, 30.0, 40.0, 10.0, 20.0)]
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=seq)
        cursor.fetchall = MagicMock(return_value=[])
        out = fetch_tesoreria_resumen(cursor, _filters())
        self.assertEqual(out["saldo_inicial"], 0.0)
        self.assertEqual(out["saldo_final_sistema"], 100.0)
        self.assertEqual(out["saldo_final"], 20.0)
        self.assertEqual(out["saldo_final_coherente"], 20.0)
        self.assertEqual(out["drift_sistema"], 80.0)
        self.assertFalse(out["banco_disponible"])
        self.assertTrue(out["disponible"])
        self.assertIn("ingresos_ventas", out)

    def test_fetch_ventas_cobros_resumen_estructura(self):
        cursor = MagicMock()
        seq = [
            (10.0, 20.0, 5.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        ]
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=seq)
        cursor.fetchall = MagicMock(return_value=[("REC", "Cobranza Efectivo", 15.0)])
        out = fetch_ventas_cobros_resumen(cursor, _filters())
        self.assertIn("facturado_por_medio", out)
        self.assertIn("cobrado_caja_por_medio", out)
        self.assertEqual(out["facturado_por_medio"]["total"], 35.0)
        self.assertNotIn("impuestos", out)

    def test_fetch_cruzados_resumen_estructura(self):
        cursor = MagicMock()
        seq = [(50.0, 2.0), (1.0,), (200.0,)]
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=seq)
        out = fetch_cruzados_resumen(cursor, _filters())
        self.assertEqual(out["backorder_importe"], 50.0)
        self.assertEqual(out["facturacion_periodo"], 200.0)
        self.assertIsNotNone(out["demand_coverage_pct"])

    @patch("reports.services.executive_dashboard.command_center.mpr_modulo_activo", return_value=True)
    @patch("reports.services.executive_dashboard.command_center.fetch_manufactura_resumen")
    @patch("reports.services.executive_dashboard.command_center.legacy_cursor")
    def test_run_command_center_estructura(self, mock_legacy, mock_mfg, _mpr_on):
        cursor = _cursor_zeros()
        mock_legacy.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_legacy.return_value.__exit__ = MagicMock(return_value=False)
        mock_mfg.return_value = {
            "pedidos_fabrica_pendientes": 1,
            "opt_atrasadas": 0,
            "unidades_pendientes_produccion": 0,
            "items_urgentes": 0,
            "disponible": True,
            "meta": {},
        }
        out = run_command_center(_filters())
        self.assertIn("areas", out)
        self.assertIn("ventas", out["areas"])
        self.assertIn("tesoreria", out["areas"])
        self.assertIn("ventas_cobros", out["areas"])
        self.assertNotIn("crm", out["areas"])
        self.assertNotIn("impuestos", out["areas"])
        self.assertIn("sucursales_disponibles", out)
        self.assertEqual(out["meta"]["definicion"], "executive-dashboard-v1")
        self.assertIn("endpoints", out["meta"])
        self.assertIn("tesoreria", out["meta"]["endpoints"])
        self.assertIn("ventas_cobros", out["meta"]["endpoints"])
        self.assertIn("tesoreria_banco", out["meta"]["endpoints"])
        self.assertTrue(out["meta"]["modulos"]["mpr"])
        tes = out["areas"].get("tesoreria") or {}
        self.assertIn("banco", tes)

    @patch("reports.services.executive_dashboard.command_center.mpr_modulo_activo", return_value=False)
    @patch("reports.services.executive_dashboard.command_center.fetch_manufactura_resumen")
    @patch("reports.services.executive_dashboard.command_center.legacy_cursor")
    def test_run_command_center_sin_mpr_oculta_manufactura(self, mock_legacy, mock_mfg, _mpr_off):
        cursor = _cursor_zeros()
        mock_legacy.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_legacy.return_value.__exit__ = MagicMock(return_value=False)
        out = run_command_center(_filters())
        self.assertNotIn("manufactura", out["areas"])
        self.assertFalse(out["meta"]["modulos"]["mpr"])
        mock_mfg.assert_not_called()

    @patch("reports.services.executive_dashboard.command_center.mpr_modulo_activo", return_value=True)
    @patch("reports.services.executive_dashboard.command_center.fetch_manufactura_resumen")
    @patch("reports.services.executive_dashboard.command_center.legacy_cursor")
    @patch(
        "reports.services.executive_dashboard.command_center.fetch_ventas_cobros_resumen",
        return_value={"disponible": True, "meta": {}, "facturado_por_medio": {}, "cobrado_caja_por_medio": {}},
    )
    @patch(
        "reports.services.executive_dashboard.command_center.fetch_cruzados_resumen",
        return_value={"disponible": True, "meta": {}, "backorder_importe": 0},
    )
    @patch(
        "reports.services.executive_dashboard.command_center.fetch_compras_resumen",
        return_value={"disponible": True, "meta": {}, "oc_pendientes_cantidad": 0},
    )
    @patch(
        "reports.services.executive_dashboard.command_center.fetch_inventario_resumen",
        return_value={"disponible": True, "meta": {}, "valor_stock": 0},
    )
    @patch(
        "reports.services.executive_dashboard.command_center.fetch_ventas_resumen",
        return_value={"disponible": True, "meta": {"notas_semanticas": []}, "ventas_netas": 1},
    )
    def test_run_command_center_aisla_fallo_tesoreria(
        self, mock_ventas, mock_inv, mock_comp, mock_cruz, mock_cob, mock_legacy, mock_mfg, _mpr_on
    ):
        cursor = MagicMock()
        mock_legacy.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_legacy.return_value.__exit__ = MagicMock(return_value=False)

        class FakeMysqlError(Exception):
            pass

        FakeMysqlError.__module__ = "MySQLdb"

        with patch(
            "reports.services.executive_dashboard.command_center.fetch_tesoreria_resumen",
            side_effect=FakeMysqlError("(1028, 'maximum statement execution time exceeded')"),
        ):
            mock_mfg.return_value = {
                "pedidos_fabrica_pendientes": 0,
                "opt_atrasadas": 0,
                "unidades_pendientes_produccion": 0,
                "items_urgentes": 0,
                "disponible": True,
                "meta": {},
            }
            out = run_command_center(_filters())

        self.assertIn("ventas", out["areas"])
        self.assertFalse(out["areas"]["tesoreria"]["disponible"])
        self.assertEqual(
            out["areas"]["tesoreria"]["error"]["tipo"], "legacy_transient_failure"
        )

    def test_sum_saldo_cajas_usa_agregacion_sin_subconsulta_correlacionada(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(250.0,))
        total = _sum_saldo_cajas(
            cursor, "2026-05-01", antes_de=True, cod_sucursal=None
        )
        self.assertEqual(total, 250.0)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("MAX(fecha)", sql)
        self.assertIn("MAX(codigo_movimiento)", sql)
        self.assertNotIn("SELECT c2.saldo FROM caja c2", sql)

    def test_safe_legacy_area_captura_operational_error(self):
        class FakeOperationalError(Exception):
            pass

        def _boom():
            raise FakeOperationalError("timeout")

        with patch(
            "reports.services.executive_dashboard.command_center.is_legacy_db_error",
            return_value=True,
        ):
            out = _safe_legacy_area("tesoreria", _boom)
        self.assertFalse(out["disponible"])

    @patch(
        "reports.services.executive_dashboard.manufacturing_metrics.listar_ventana_pack",
        return_value=[],
    )
    @patch(
        "reports.services.executive_dashboard.manufacturing_metrics.listar_opt_listado",
        return_value=[],
    )
    @patch(
        "reports.services.executive_dashboard.manufacturing_metrics.listar_pedidos_fabrica",
        return_value=[{"x": 1}],
    )
    @patch(
        "reports.services.executive_dashboard.manufacturing_metrics.listar_lista_produccion_agrupada",
        return_value=[{"cantidad_pendiente_prod": 5}],
    )
    def test_fetch_manufactura_resumen_ok(
        self,
        mock_agrupada,
        mock_pedidos,
        mock_opt,
        mock_pack,
    ):
        out = fetch_manufactura_resumen("be1", _filters())
        self.assertTrue(out["disponible"])
        self.assertEqual(out["pedidos_fabrica_pendientes"], 1)
        self.assertEqual(out["unidades_pendientes_produccion"], 5.0)
        fi, ff = date(2026, 5, 1), date(2026, 5, 11)
        mock_agrupada.assert_called_once_with(
            "be1",
            limit=50,
            excluir_filas_opt_liberadas_mstock=True,
            fecha_desde=fi,
            fecha_hasta=ff,
        )
        mock_pedidos.assert_called_once_with(
            "be1", limit=5000, estado="Pendiente", fecha_desde=fi, fecha_hasta=ff
        )
        mock_opt.assert_called_once_with(
            "be1", limit=500, solo_atrasadas=True, fecha_desde=fi, fecha_hasta=ff
        )
        mock_pack.assert_called_once_with(
            "be1", limit=15, fecha_desde=fi, fecha_hasta=ff
        )

    def test_list_pedidos_pendientes_paginado(self):
        cursor = MagicMock()
        seq_count = [(2, 1500.0)]
        seq_rows = [
            (
                100,
                "PED-1",
                "01/05/2026",
                10,
                "Cliente SA",
                "Preparado",
                750.0,
            ),
        ]
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=seq_count)
        cursor.description = [
            ("codigo_movimiento",),
            ("nro_comprobante",),
            ("fecha",),
            ("codigo_cliente",),
            ("nombre_cliente",),
            ("estado",),
            ("subtotal_desc",),
        ]
        cursor.fetchall = MagicMock(return_value=seq_rows)
        f = _filters()
        out = list_pedidos_pendientes(cursor, f)
        self.assertEqual(out["total_registros"], 2)
        self.assertEqual(out["total_monto"], 1500.0)
        self.assertEqual(len(out["filas"]), 1)
        self.assertEqual(out["filas"][0]["codigo_movimiento"], 100)
        self.assertEqual(out["limit"], f.limit)

    def test_list_remitos_no_facturados_paginado(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(1, 200.0))
        cursor.description = [
            ("codigo_movimiento",),
            ("nro_comprobante",),
            ("fecha",),
            ("codigo_cliente",),
            ("nombre_cliente",),
            ("estado",),
            ("subtotal_desc",),
        ]
        cursor.fetchall = MagicMock(
            return_value=[(1, "REM-1", "01/05/2026", 5, "C", "Pendiente", 200.0)]
        )
        out = list_remitos_no_facturados(cursor, _filters())
        self.assertEqual(out["total_registros"], 1)
        self.assertIn("filas", out)

    def test_list_backorder_detalle_paginado(self):
        cursor = MagicMock()
        seq = [(3,), (500.0,)]
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=seq)
        cursor.fetchall = MagicMock(
            return_value=[
                (1, "A1", "Art", "Rub", 2.0, 100.0, 10.0, 1.0, 9.0, 0.0),
            ]
        )
        out = list_backorder_detalle(cursor, _filters())
        self.assertEqual(out["total_registros"], 3)
        self.assertEqual(out["total_monto"], 500.0)
        self.assertIn("bo_importe", out["filas"][0])

    def test_list_existencias_paginado(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(10,))
        cursor.description = [("id_art",), ("stock",)]
        cursor.fetchall = MagicMock(return_value=[(1, 5.0)])
        out = list_existencias(cursor, _filters())
        self.assertEqual(out["total_registros"], 10)
        self.assertNotIn("total_monto", out)

    def test_list_existencias_busqueda_en_sql(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(2,))
        cursor.description = [("nombre",), ("stock",)]
        cursor.fetchall = MagicMock(return_value=[])
        filtros = replace(_filters(), busqueda="aceite")
        list_existencias(cursor, filtros)
        sql_count = cursor.execute.call_args_list[0][0][0]
        self.assertIn("NombreArticulo LIKE", sql_count)
        self.assertIn("ESCAPE", sql_count)

    def test_resolve_filters_busqueda_minimo_dos_caracteres(self):
        class Q:
            def get(self, k, default=None):
                return {"busqueda": "a", "fecha": "2026-05-11"}.get(k, default)

        f = resolve_filters_from_query_params(Q(), base_empresa="x")
        self.assertIsNone(f.busqueda)

        class Q2:
            def get(self, k, default=None):
                return {"busqueda": "ab", "fecha": "2026-05-11"}.get(k, default)

        f2 = resolve_filters_from_query_params(Q2(), base_empresa="x")
        self.assertEqual(f2.busqueda, "ab")

    def test_fetch_tesoreria_banco_resumen_estructura(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(
            side_effect=[(500.0,), (600.0,), (100.0, 50.0), (3,)]
        )
        cursor.fetchall = MagicMock(return_value=[])
        out = fetch_tesoreria_banco_resumen(cursor, _filters())
        self.assertEqual(out["saldo_banco_inicial"], 500.0)
        self.assertEqual(out["saldo_banco_final"], 600.0)
        self.assertEqual(out["creditos_periodo"], 100.0)
        self.assertEqual(out["debitos_periodo"], 50.0)
        self.assertEqual(out["pendiente_conciliar"], 3)
        self.assertTrue(out["disponible"])
        self.assertIn("por_cuenta_banco", out)
        self.assertEqual(out["meta"]["definicion"], "executive-dashboard-v1")

    def test_list_cobros_detalle_paginado(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(side_effect=[(1,), (0,)])
        cursor.description = [
            ("fecha",),
            ("tipo",),
            ("nro_comprobante",),
            ("tipo_comprobante",),
            ("importe",),
            ("id_cliente",),
            ("nombre_cliente",),
            ("medio_mcp",),
        ]
        cursor.fetchall = MagicMock(
            return_value=[
                ("01/05/2026", "Cobranza Efectivo", "REC-1", "REC", 500.0, 10, "Cliente SA", None),
            ]
        )
        out = list_cobros_detalle(cursor, _filters())
        self.assertEqual(out["total_registros"], 1)
        self.assertEqual(len(out["filas"]), 1)
        self.assertEqual(out["filas"][0]["importe"], 500.0)
        self.assertIn("medio", out["filas"][0])

    def test_list_movimientos_caja_paginado(self):
        cursor = MagicMock()
        cursor.execute = MagicMock(return_value=None)
        cursor.fetchone = MagicMock(return_value=(2,))
        cursor.description = [
            ("fecha",),
            ("tipo",),
            ("tipo_comprobante",),
            ("nro_comprobante",),
            ("ingreso",),
            ("egreso",),
            ("codigo_movimiento",),
            ("cod_sucursal",),
        ]
        cursor.fetchall = MagicMock(
            return_value=[
                ("01/05/2026", "Cobranza", "REC", "R-1", 100.0, 0.0, 99, 1),
            ]
        )
        out = list_movimientos_caja(cursor, _filters())
        self.assertEqual(out["total_registros"], 2)
        self.assertEqual(len(out["filas"]), 1)
        sql_count = cursor.execute.call_args_list[0][0][0]
        self.assertIn("Transferencia de Fondos", sql_count)
