"""Tests unitarios del backfill CDA para PED BEST."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mpr.best_migration.pedido_cda_backfill import (
    _SQL_PRIMER_DOMICILIO,
    backfill_cda_pedidos_best,
)


def _pedido_row(
    *,
    cod_mov: int = 1001,
    nro: str = "BEST-100",
    id_cliente: int = 50,
    cda_id_domicilio: int | None = None,
    tiene_cda: int = 0,
) -> dict:
    return {
        "cod_mov": cod_mov,
        "nro_comprobante": nro,
        "id_cliente": id_cliente,
        "fecha": date(2026, 7, 10),
        "fecha_entrega": date(2026, 7, 20),
        "id_deposito_despacho": 3,
        "cda_id_domicilio": cda_id_domicilio,
        "tiene_cda": tiene_cda,
    }


class PedidoCdaBackfillTest(SimpleTestCase):
    def test_query_domicilio_ordena_por_id_asc(self):
        self.assertIn("ORDER BY id_cliente_domicilio ASC", _SQL_PRIMER_DOMICILIO)

    @patch("mpr.best_migration.pedido_cda_backfill.get_connection")
    def test_dry_run_cuenta_insert_y_ya_ok(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_cur.fetchall.return_value = [
            _pedido_row(cod_mov=1, nro="BEST-1", cda_id_domicilio=99),
            _pedido_row(cod_mov=2, nro="BEST-2"),
            _pedido_row(cod_mov=3, nro="BEST-3", id_cliente=77),
        ]
        mock_cur.fetchone.side_effect = [
            {"id_cliente_domicilio": 10},
            {"id_cliente_domicilio": 20},
        ]

        result = backfill_cda_pedidos_best("administranet1", dry_run=True)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["pedidos_revisados"], 3)
        self.assertEqual(result["ya_ok"], 1)
        self.assertEqual(result["insertados"], 2)
        self.assertEqual(result["actualizados"], 0)
        self.assertEqual(result["omitidos_sin_domicilio"], 0)
        self.assertEqual(len(result["detalle_escritos"]), 2)
        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()

        domicilio_calls = [
            call.args[0]
            for call in mock_cur.execute.call_args_list
            if "FROM cliente_domicilio" in str(call.args[0])
        ]
        self.assertEqual(len(domicilio_calls), 2)
        self.assertIn("ORDER BY id_cliente_domicilio ASC", domicilio_calls[0])

    @patch("mpr.best_migration.pedido_cda_backfill.get_connection")
    def test_dry_run_omite_sin_domicilio(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_cur.fetchall.return_value = [
            _pedido_row(cod_mov=5, nro="BEST-5", id_cliente=88),
        ]
        mock_cur.fetchone.return_value = None

        result = backfill_cda_pedidos_best("administranet1", dry_run=True)

        self.assertEqual(result["omitidos_sin_domicilio"], 1)
        self.assertEqual(result["insertados"], 0)
        self.assertEqual(len(result["detalle_omitidos"]), 1)
        self.assertEqual(result["detalle_omitidos"][0]["nro_comprobante"], "BEST-5")

    @patch("mpr.best_migration.pedido_cda_backfill.get_connection")
    def test_confirmar_insert_params_orden_correcto(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_cur.fetchall.return_value = [
            _pedido_row(cod_mov=1176, nro="BEST-300042608", id_cliente=1024),
        ]
        mock_cur.fetchone.return_value = {"id_cliente_domicilio": 1314}

        result = backfill_cda_pedidos_best("administranet", dry_run=False)

        self.assertEqual(result["insertados"], 1)
        insert_calls = [
            call
            for call in mock_cur.execute.call_args_list
            if "INSERT INTO cliente_datos_adicionales" in str(call.args[0])
        ]
        self.assertEqual(len(insert_calls), 1)
        # fecha, dep, id_cliente, CodigoMovimiento, id_domicilio
        params = insert_calls[0].args[1]
        self.assertEqual(params[1:], (3, 1024, 1176, 1314))
        self.assertEqual(str(params[0]), "2026-07-20")
        mock_conn.commit.assert_called_once()
