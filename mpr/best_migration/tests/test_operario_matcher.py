"""Tests del matcher de tejedores BEST → sue_abm_empleado."""

from django.test import SimpleTestCase

from mpr.best_migration.operario_matcher import match_operarios, normalizar_codigo_tejedor


class OperarioMatcherTests(SimpleTestCase):
    def test_normalizar_codigo(self):
        self.assertEqual(normalizar_codigo_tejedor(" f "), "F")
        self.assertEqual(normalizar_codigo_tejedor("ab-1"), "AB1")

    def test_match_codigo_exacto_en_token(self):
        best = [{"codigo": "F", "movimientos_n": 10}]
        admin = [
            {"id": 1, "label": "Franco Pérez"},
            {"id": 2, "label": "F"},
        ]
        rows = match_operarios(best_rows=best, admin_empleados=admin)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].admin_id_operario, 2)
        self.assertEqual(rows[0].status, "INFERIDO")
        self.assertEqual(rows[0].score, 100)

    def test_sin_candidato(self):
        best = [{"codigo": "Z"}]
        admin = [{"id": 1, "label": "Ana"}]
        rows = match_operarios(best_rows=best, admin_empleados=admin)
        self.assertEqual(rows[0].status, "SIN_CANDIDATO")
        self.assertIsNone(rows[0].admin_id_operario)
