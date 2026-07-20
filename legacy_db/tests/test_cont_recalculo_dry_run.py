"""Tests del dry-run de recálculo contable (Fase 2, solo lectura legacy)."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from contabilidad_audit.models import PREFIJOS_CUENTA_DEFAULT, PlanCorreccion, PoliticaAuditoriaContable
from contabilidad_audit.services.politicas import calcular_config_hash
from legacy_db.services.cont_recalculo_service import (
    PLAN_TTL_MIN,
    calcular_data_fingerprint,
    dry_run,
)


def _politica_base() -> dict:
    return {
        "tratamiento_anulados": "incluir_neutralizado",
        "politica_centavo": "diario_manda",
        "prefijos_cuenta": dict(PREFIJOS_CUENTA_DEFAULT),
        "ejercicios_cerrados": "no_tocar",
        "alcance_recompute": "ejercicio_seleccionado",
        "tolerancia_decimal": Decimal("0.005"),
    }


def _mock_conn_cursor():
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    conn.cursor.return_value = cursor
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    return conn, cursor


class ContRecalculoDryRunTestCase(TestCase):
    def setUp(self):
        PoliticaAuditoriaContable.objects.get_or_create(
            base_empresa=PoliticaAuditoriaContable.BASE_DEFAULT,
            defaults={
                "prefijos_cuenta": dict(PREFIJOS_CUENTA_DEFAULT),
                "tolerancia_decimal": Decimal("0.005"),
                "actualizado_por": "test",
            },
        )

    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    def test_dry_run_no_ejecuta_dml_legacy(self, mock_pool):
        conn, cursor = _mock_conn_cursor()
        pool = MagicMock()
        pool.get_connection.return_value = conn
        mock_pool.return_value = pool

        payload = dry_run(
            base_empresa="administranet89",
            alcance={"id_ejercicio": 1},
            politica=_politica_base(),
            usuario="tester",
        )

        for call in cursor.execute.call_args_list:
            sql = (call[0][0] if call[0] else "").strip().upper()
            self.assertFalse(sql.startswith("INSERT"), msg=sql)
            self.assertFalse(sql.startswith("UPDATE"), msg=sql)
            self.assertFalse(sql.startswith("DELETE"), msg=sql)
            self.assertFalse(sql.startswith("ALTER"), msg=sql)
            self.assertFalse(sql.startswith("CREATE"), msg=sql)

        self.assertEqual(PlanCorreccion.objects.count(), 1)
        self.assertIn("dry_run_id", payload)
        self.assertIn("data_fingerprint", payload)

    def test_data_fingerprint_estable(self):
        items = [
            {
                "tabla": "cont_ejercicio_saldo_cta",
                "clave": {"id_pc": 10, "id_ejercicio": 1},
                "valor_anterior": "100.00",
            },
            {
                "tabla": "cont_ejercicio_saldo_cta",
                "clave": {"id_pc": 20, "id_ejercicio": 1},
                "valor_anterior": "50.00",
            },
        ]
        fp1 = calcular_data_fingerprint(items)
        fp2 = calcular_data_fingerprint(list(reversed(items)))
        self.assertEqual(fp1, fp2)
        self.assertTrue(fp1.startswith("v1:"))

    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    def test_cambio_politica_cambia_config_hash(self, mock_pool):
        conn, _cursor = _mock_conn_cursor()
        pool = MagicMock()
        pool.get_connection.return_value = conn
        mock_pool.return_value = pool

        politica_a = _politica_base()
        payload_a = dry_run(
            "administranet89",
            {"id_ejercicio": 1},
            politica_a,
            usuario="tester",
        )

        politica_b = {**politica_a, "tolerancia_decimal": Decimal("0.0100")}
        payload_b = dry_run(
            "administranet89",
            {"id_ejercicio": 1},
            politica_b,
            usuario="tester",
        )

        self.assertNotEqual(payload_a["config_hash"], payload_b["config_hash"])
        self.assertEqual(payload_b["config_hash"], calcular_config_hash(politica_b))

    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    def test_dry_run_incluye_concepto_y_filas_saldo_en_plan(self, mock_pool):
        conn, cursor = _mock_conn_cursor()
        cursor.fetchall.side_effect = [
            [
                {
                    "codigo_movimiento": "7777",
                    "nro_asiento": 10,
                    "id_pc": 55,
                    "id_ejercicio": 1,
                    "concepto_contra": 4,
                    "concepto_esperado": 7,
                    "codigo_movimiento_original": "6666",
                }
            ],
            [],
            [],
            [],
            [],
            [],
        ]
        pool = MagicMock()
        pool.get_connection.return_value = conn
        mock_pool.return_value = pool

        with patch(
            "legacy_db.services.cont_recalculo_service._plan_propuestas_rei",
            return_value=[],
        ):
            payload = dry_run(
                base_empresa="administranet89",
                alcance={"id_ejercicio": 1},
                politica=_politica_base(),
                usuario="tester",
            )

        items = payload["plan"]["items"]
        checks = {item["check_id"] for item in items}
        self.assertIn("concepto_anulacion_incoherente", checks)
        concepto = next(i for i in items if i["check_id"] == "concepto_anulacion_incoherente")
        self.assertEqual(concepto["accion"], "update")
        self.assertEqual(concepto["campo"], "id_concepto_asiento")
        self.assertEqual(concepto["referencia"], "H05")
        self.assertIn("concepto_anulacion_incoherente", payload["impacto"]["checks_incluidos"])
        self.assertIn("cuentas_sin_fila_saldo", payload["impacto"]["checks_incluidos"])

    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    def test_expira_en_ttl_30_minutos(self, mock_pool):
        conn, _cursor = _mock_conn_cursor()
        pool = MagicMock()
        pool.get_connection.return_value = conn
        mock_pool.return_value = pool

        dry_run(
            "administranet89",
            {"id_ejercicio": 1},
            _politica_base(),
            usuario="tester",
        )

        plan = PlanCorreccion.objects.latest("creado_en")
        delta = plan.expira_en - plan.creado_en
        self.assertEqual(delta, timedelta(minutes=PLAN_TTL_MIN))
