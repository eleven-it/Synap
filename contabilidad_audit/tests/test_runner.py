"""Tests de corrida sin DML en MySQL legacy."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from contabilidad_audit.models import PREFIJOS_CUENTA_DEFAULT, CorridaAuditoria, PoliticaAuditoriaContable
from contabilidad_audit.services.registry import CHECKS
from contabilidad_audit.services.runner import ejecutar_corrida


class RunnerTestCase(TestCase):
    def setUp(self):
        PoliticaAuditoriaContable.objects.get_or_create(
            base_empresa=PoliticaAuditoriaContable.BASE_DEFAULT,
            defaults={
                "prefijos_cuenta": dict(PREFIJOS_CUENTA_DEFAULT),
                "tolerancia_decimal": Decimal("0.005"),
                "actualizado_por": "test",
            },
        )

    @patch("contabilidad_audit.services.runner.get_mysql_pool")
    def test_corrida_sin_dml_legacy(self, mock_pool):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        conn.cursor.return_value = cursor
        conn.__enter__ = MagicMock(return_value=conn)
        conn.__exit__ = MagicMock(return_value=False)
        mock_pool.return_value.get_connection.return_value = conn

        stub_checks = {}
        for check_id, fn in CHECKS.items():
            def _make_stub(cid, titulo, severidad):
                def stub(base_empresa, filtros, politica, contexto):
                    from contabilidad_audit.services.resultados import construir_audit_result

                    return construir_audit_result(
                        check_id=cid,
                        titulo=titulo,
                        severidad=severidad,
                        ok=True,
                        total_evaluado=0,
                        diferencias=[],
                        resumen={},
                        contexto=contexto,
                    )

                stub.check_id = cid
                stub.titulo = titulo
                stub.severidad = severidad
                return stub

            stub_checks[check_id] = _make_stub(check_id, fn.titulo, fn.severidad)

        with patch.dict(CHECKS, stub_checks, clear=True):
            payload = ejecutar_corrida(
                "administranet89",
                {"id_ejercicio": 1},
                check_ids=["asiento_balanceado"],
                usuario="tester",
            )

        for call in cursor.execute.call_args_list:
            sql = (call[0][0] if call[0] else "").strip().upper()
            self.assertFalse(sql.startswith("INSERT"))
            self.assertFalse(sql.startswith("UPDATE"))
            self.assertFalse(sql.startswith("DELETE"))
            self.assertFalse(sql.startswith("ALTER"))

        self.assertEqual(CorridaAuditoria.objects.count(), 1)
        self.assertIn("checks", payload)
        self.assertEqual(len(payload["checks"]), 1)
