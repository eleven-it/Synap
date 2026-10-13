"""Alcance territorial: evita ampliar el universo con filtros vacíos o ajenos."""
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from reports.services.executive_dashboard.base import DashboardFilters
from reports.services.executive_dashboard.inventory_metrics import (
    fetch_inventario_resumen,
    list_existencias,
)
from reports.services.executive_dashboard.territory import (
    TerritoryAccessDenied,
    constrain_filters_to_user,
)


def _filters(**kwargs):
    data = dict(
        base_empresa="best_sox", fecha_referencia=date(2026, 10, 9),
        fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 9),
    )
    data.update(kwargs)
    return DashboardFilters(**data)


def _user():
    return SimpleNamespace(id_usuario=3, cod_usuario="operador", is_authenticated=True, is_superuser=False)


class CommandCenterTerritoryTests(SimpleTestCase):
    @patch("reports.services.executive_dashboard.territory.legacy_cursor")
    def test_stock_usa_solo_depositos_del_usuario(self, legacy):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(6,), (6,), (8,)]
        legacy.return_value.__enter__.return_value = cursor
        out = constrain_filters_to_user(_user(), _filters(), area_key="inventario")
        self.assertEqual(out.depositos_filtro, (6, 8))
        self.assertIn("deposito_usr", cursor.execute.call_args.args[0])
        self.assertEqual(cursor.execute.call_args.args[1], [3])

    @patch("reports.services.executive_dashboard.territory.legacy_cursor")
    def test_stock_rechaza_deposito_ajeno(self, legacy):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(6,)]
        legacy.return_value.__enter__.return_value = cursor
        with self.assertRaises(TerritoryAccessDenied):
            constrain_filters_to_user(
                _user(), _filters(depositos_filtro=(9,)), area_key="inventario"
            )

    @patch("reports.services.executive_dashboard.territory.legacy_cursor")
    def test_ventas_interseca_pv_y_sucursal(self, legacy):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(1, 10), (2, 10), (3, 20)]
        legacy.return_value.__enter__.return_value = cursor
        out = constrain_filters_to_user(
            _user(), _filters(sucursales_filtro=(10,), puntos_venta=(2, 3)), area_key="ventas"
        )
        self.assertEqual(out.puntos_venta, (2,))
        self.assertEqual(out.sucursales_filtro, (10,))

    @patch("reports.services.executive_dashboard.territory.legacy_cursor")
    def test_preparacion_restringe_pv_como_ventas(self, legacy):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(1, 10), (2, 20)]
        legacy.return_value.__enter__.return_value = cursor
        out = constrain_filters_to_user(
            _user(), _filters(), area_key="preparacion_pedidos"
        )
        self.assertEqual(out.puntos_venta, (1, 2))
        self.assertEqual(out.sucursales_filtro, (10, 20))

    @patch("reports.services.executive_dashboard.territory.legacy_cursor")
    def test_sin_asignaciones_no_equivale_a_todos(self, legacy):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        legacy.return_value.__enter__.return_value = cursor
        with self.assertRaises(TerritoryAccessDenied):
            constrain_filters_to_user(_user(), _filters(), area_key="ventas")

    def test_area_sin_consultas_territoriales_se_cierra(self):
        with self.assertRaises(TerritoryAccessDenied):
            constrain_filters_to_user(_user(), _filters(), area_key="compras")

    def test_stock_sql_lleva_filtro_a_resumen_y_detalle(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (0, 0, 0)
        cursor.fetchall.return_value = []
        fetch_inventario_resumen(cursor, _filters(depositos_filtro=(6,)))
        self.assertTrue(cursor.execute.call_args_list)
        for call in cursor.execute.call_args_list:
            self.assertIn("dep.CodDeposito IN (%s)", call.args[0])
            self.assertIn(6, call.args[1])
        cursor.execute.reset_mock()
        list_existencias(cursor, _filters(depositos_filtro=(6,)))
        self.assertEqual(cursor.execute.call_count, 2)
        for call in cursor.execute.call_args_list:
            self.assertIn("dep.CodDeposito IN (%s)", call.args[0])
            self.assertIn(6, call.args[1])
