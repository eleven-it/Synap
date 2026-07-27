"""Tests de rollback_lote (reversión deshabilitada)."""
from __future__ import annotations

from django.test import TestCase, override_settings

from legacy_db.services.cont_recalculo_service import CorreccionContableError, rollback_lote


class ContRecalculoRollbackTestCase(TestCase):
    @override_settings(ENVIRONMENT="development")
    def test_rollback_rechaza_sin_permiso(self):
        with self.assertRaises(CorreccionContableError) as ctx:
            rollback_lote("test_empresa", "L20260718-001", "tester", tiene_permiso_corregir=False)
        self.assertIn("permiso", str(ctx.exception).lower())

    @override_settings(ENVIRONMENT="development")
    def test_rollback_deshabilitado_con_permiso(self):
        with self.assertRaises(CorreccionContableError) as ctx:
            rollback_lote(
                "test_empresa",
                "L20260718-001",
                "tester",
                tiene_permiso_corregir=True,
            )
        self.assertIn("reversión de lotes ya no está disponible", str(ctx.exception).lower())
        self.assertIn("backup", str(ctx.exception).lower())
