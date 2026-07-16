# Tests integración migración JSON → org (REQ-JER-03): backfill idempotente.

import json
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from ecom.services.jerarquia_comercial import backfill_carteras_desde_config


def _mock_pool_with_claves(claves_rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = claves_rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    pool = MagicMock()
    pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
    pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
    return pool, conn, cursor


class TestBackfillCarterasDesdeConfig(SimpleTestCase):
    @patch("ecom.services.jerarquia_comercial.vincular_supervisor_vendedor")
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_backfill_desde_json_fixture(self, mock_pool_fn, mock_vincular):
        mock_vincular.return_value = (True, "OK")
        pool, conn, _ = _mock_pool_with_claves(
            [
                {
                    "key_permiso": "ecom_vendedores_a_cargo_10",
                    "valor_permiso": json.dumps([20, 21, 10]),
                },
            ]
        )
        mock_pool_fn.return_value = pool

        result = backfill_carteras_desde_config("emp1")

        self.assertTrue(result["ok"])
        self.assertEqual(result["supervisores"], 1)
        self.assertEqual(result["vinculos_sv"], 2)
        mock_vincular.assert_any_call("emp1", 10, 20)
        mock_vincular.assert_any_call("emp1", 10, 21)
        conn.commit.assert_called_once()

    @patch("ecom.services.jerarquia_comercial.vincular_supervisor_vendedor")
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_dry_run_sin_escritura(self, mock_pool_fn, mock_vincular):
        pool, conn, _ = _mock_pool_with_claves(
            [{"key_permiso": "ecom_vendedores_a_cargo_5", "valor_permiso": "[30]"}]
        )
        mock_pool_fn.return_value = pool

        result = backfill_carteras_desde_config("emp1", dry_run=True)

        self.assertTrue(result["ok"])
        self.assertEqual(result["vinculos_sv"], 1)
        mock_vincular.assert_not_called()
        conn.commit.assert_called_once()

    @patch("ecom.services.jerarquia_comercial.vincular_supervisor_vendedor")
    @patch("ecom.services.jerarquia_comercial.get_mysql_pool")
    def test_idempotente_vinculo_existente(self, mock_pool_fn, mock_vincular):
        mock_vincular.return_value = (False, "Ya existe vínculo activo.")
        pool, _, _ = _mock_pool_with_claves(
            [{"key_permiso": "ecom_vendedores_a_cargo_10", "valor_permiso": "[20]"}]
        )
        mock_pool_fn.return_value = pool

        result = backfill_carteras_desde_config("emp1")

        self.assertTrue(result["ok"])
        self.assertEqual(result["vinculos_sv"], 0)


class TestComandoMigrarCarteras(SimpleTestCase):
    @patch("ecom.management.commands.migrar_carteras_a_jerarquia.backfill_carteras_desde_config")
    def test_comando_ok(self, mock_backfill):
        mock_backfill.return_value = {
            "ok": True,
            "supervisores": 2,
            "vinculos_sv": 5,
        }
        out = StringIO()
        call_command("migrar_carteras_a_jerarquia", "administranet1", stdout=out)
        self.assertIn("vínculos SV=5", out.getvalue())
        mock_backfill.assert_called_once_with("administranet1", dry_run=False)

    @patch("ecom.management.commands.migrar_carteras_a_jerarquia.backfill_carteras_desde_config")
    def test_comando_falla_si_backfill_error(self, mock_backfill):
        mock_backfill.return_value = {"ok": False, "error": "Sin conexión"}
        with self.assertRaises(CommandError):
            call_command("migrar_carteras_a_jerarquia", "administranet1")
