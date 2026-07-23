"""Tests unitarios del remediador PED BEST."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.best_migration.pedido_best_remediar import (
    _SQL_PEDIDOS_PENDIENTES,
    calc_cabecera_p2,
    calc_linea_p2,
    format_nro_comprobante_synap,
    remediar_pedidos_best,
)


class TestFormatNroComprobanteSynap(SimpleTestCase):
    def test_formato_pv1(self):
        self.assertEqual(
            format_nro_comprobante_synap(id_pv=1, nro_comp_busq=3),
            "0001-00000003",
        )

    def test_formato_pv2(self):
        self.assertEqual(
            format_nro_comprobante_synap(id_pv=2, nro_comp_busq=52),
            "0002-00000052",
        )


class TestCalcP2Iva(SimpleTestCase):
    def test_cabecera_bruto_121(self):
        tot = calc_cabecera_p2(Decimal("121.00"))
        self.assertEqual(tot["importe_venta"], Decimal("121.00"))
        self.assertEqual(tot["subtotal1"], Decimal("100.00"))
        self.assertEqual(tot["iva1"], Decimal("21.00"))
        self.assertEqual(tot["subtotal_gral"], Decimal("100.00"))
        self.assertEqual(tot["subtotal_desc"], Decimal("100.00"))

    def test_linea_bruto_unitario(self):
        ln = calc_linea_p2(Decimal("12.10"), Decimal("5"))
        self.assertEqual(ln["precio_bruto_u"], Decimal("12.10"))
        self.assertEqual(ln["precio_neto_u"], Decimal("10.00"))
        self.assertEqual(ln["precio_iva_u"], Decimal("2.10"))
        self.assertEqual(ln["precio_venta_u"], Decimal("10.00"))
        self.assertEqual(ln["precio_bruto_r"], Decimal("60.50"))
        self.assertEqual(ln["precio_neto_r"], Decimal("50.00"))
        self.assertEqual(ln["precio_iva_r"], Decimal("10.50"))


class TestRemediarPedidosBestDryRun(SimpleTestCase):
    def test_sql_seleccion_idempotente(self):
        self.assertIn("BEST-%", _SQL_PEDIDOS_PENDIENTES)
        self.assertIn("Cutover BEST", _SQL_PEDIDOS_PENDIENTES)
        self.assertIn("ORDER BY cp.CodigoMovimiento ASC", _SQL_PEDIDOS_PENDIENTES)

    @patch("mpr.best_migration.pedido_best_remediar.get_connection")
    @patch("mpr.best_migration.pedido_best_remediar.numero_a_letras", return_value="CIENTO VEINTIUN PESOS")
    def test_dry_run_no_commit(self, _letras, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_cur.fetchone.side_effect = [
            {"max_nro": 2},
            {"Nro": 53},
        ]
        mock_cur.fetchall.side_effect = [
            [
                {
                    "cod_mov": 100,
                    "nro_comprobante": "BEST-5001",
                    "id_cliente": 10,
                    "fecha": date(2026, 7, 10),
                    "detalle": "Cutover BEST orden 5001",
                    "importe_venta": Decimal("121.00"),
                    "cod_viajante_cliente": 7,
                }
            ],
            [{"id_stock": 1, "salida": Decimal("2"), "cantidad": Decimal("2"),
              "precio_bruto_u": Decimal("12.10"), "precio_venta_u": Decimal("12.10"),
              "alic_id": Decimal("1")}],
        ]

        result = remediar_pedidos_best("administranet1", dry_run=True, id_pv=1)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["revisados"], 1)
        self.assertEqual(result["remediados"], 1)
        self.assertEqual(result["mapeo_nro"]["BEST-5001"], "0001-00000003")
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

        update_calls = [
            c for c in mock_cur.execute.call_args_list
            if "UPDATE comp_ped" in str(c.args[0])
        ]
        self.assertEqual(len(update_calls), 0)

    @patch("mpr.best_migration.pedido_best_remediar.get_connection")
    def test_omitido_sin_prefijo_best(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_cur.fetchone.return_value = {"max_nro": 5}
        mock_cur.fetchall.return_value = [
            {
                "cod_mov": 200,
                "nro_comprobante": "0001-00000006",
                "id_cliente": 10,
                "fecha": date(2026, 7, 10),
                "detalle": "Cutover BEST orden 99",
                "importe_venta": Decimal("50"),
                "cod_viajante_cliente": 1,
            }
        ]

        result = remediar_pedidos_best("administranet1", dry_run=True)

        self.assertEqual(result["revisados"], 1)
        self.assertEqual(result["remediados"], 0)
        self.assertEqual(result["omitidos"], 1)
