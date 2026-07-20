"""Tests de rollback_lote (REC-14, mocks)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from legacy_db.services.cont_recalculo_service import CorreccionContableError, rollback_lote


class ContRecalculoRollbackTestCase(TestCase):
    @override_settings(ENVIRONMENT="development")
    def test_rollback_bloqueado_fuera_de_produccion(self):
        with self.assertRaises(CorreccionContableError) as ctx:
            rollback_lote("test_empresa", "L20260718-001", "tester", tiene_permiso_corregir=True)
        self.assertIn("producción", str(ctx.exception).lower())

    @override_settings(ENVIRONMENT="production")
    def test_rollback_rechaza_sin_permiso(self):
        with self.assertRaises(CorreccionContableError) as ctx:
            rollback_lote("test_empresa", "L20260718-001", "tester", tiene_permiso_corregir=False)
        self.assertIn("permiso", str(ctx.exception).lower())

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    def test_rollback_restaura_backup_y_registra_log(self, mock_pool):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.side_effect = [
            {
                "lote_id": "L20260718-001",
                "estado": "aplicado",
                "backups_json": json.dumps(
                    {"cont_ejercicio_saldo_cta": "cont_ejercicio_saldo_cta_bkp_x"}
                ),
            },
            {"1": 1},
        ]
        mock_pool.return_value.get_connection.return_value = conn

        resultado = rollback_lote(
            "test_empresa",
            "L20260718-001",
            "tester",
            tiene_permiso_corregir=True,
        )

        self.assertTrue(resultado["ok"])
        sqls = [str(c[0][0]) for c in cur.execute.call_args_list if c[0]]
        self.assertTrue(any("DELETE FROM `cont_ejercicio_saldo_cta`" in s for s in sqls))
        self.assertTrue(
            any(
                "INSERT INTO `cont_ejercicio_saldo_cta` SELECT * FROM" in s
                for s in sqls
            )
        )
        self.assertTrue(any("estado='revertido'" in s for s in sqls))
        self.assertTrue(any("rollback_lote" in s for s in sqls))
        self.assertEqual(conn.commit.call_count, 1)
        self.assertEqual(conn.rollback.call_count, 0)

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    def test_rollback_backup_incompleto_aborta_sin_cambios(self, mock_pool):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        cur.fetchone.side_effect = [
            {
                "lote_id": "L20260718-002",
                "estado": "aplicado",
                "backups_json": json.dumps({"cont_asiento": "cont_asiento_bkp_y"}),
            },
            None,
        ]
        mock_pool.return_value.get_connection.return_value = conn

        with self.assertRaises(CorreccionContableError) as ctx:
            rollback_lote(
                "test_empresa",
                "L20260718-002",
                "tester",
                tiene_permiso_corregir=True,
            )
        self.assertIn("Backup incompleto", str(ctx.exception))
        self.assertEqual(conn.rollback.call_count, 1)
        self.assertEqual(conn.commit.call_count, 0)
