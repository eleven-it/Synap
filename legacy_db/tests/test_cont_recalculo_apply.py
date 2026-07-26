"""Tests del apply transaccional de recálculo contable (Fase 3, mocks)."""
from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from contabilidad_audit.models import AprobacionREI, PREFIJOS_CUENTA_DEFAULT, PlanCorreccion
from contabilidad_audit.services.politicas import calcular_config_hash
from legacy_db.services.cont_recalculo_service import (
    CorreccionContableError,
    apply,
    calcular_data_fingerprint,
    rollback_lote,
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


def _item_saldo(id_pc: int, id_ej: int, anterior: str, nuevo: str) -> dict:
    return {
        "tabla": "cont_ejercicio_saldo_cta",
        "clave": {"id_pc": id_pc, "id_ejercicio": id_ej},
        "accion": "update",
        "valor_anterior": anterior,
        "valor_nuevo": nuevo,
        "delta": str(Decimal(nuevo) - Decimal(anterior)),
        "check_id": "saldo_ejercicio_vs_diario",
        "excluido": False,
    }


def _item_fila_saldo_insert(id_pc: int, id_ej: int, nuevo: str) -> dict:
    return {
        "tabla": "cont_ejercicio_saldo_cta",
        "clave": {"id_pc": id_pc, "id_ejercicio": id_ej},
        "accion": "insert",
        "valor_anterior": None,
        "valor_nuevo": nuevo,
        "delta": nuevo,
        "check_id": "cuentas_sin_fila_saldo",
        "referencia": "H10",
        "excluido": False,
    }


def _item_concepto_anul(codmov: str, nro: int, id_pc: int, anterior: int, nuevo: int) -> dict:
    return {
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento": codmov, "nro_asiento": nro, "id_pc": id_pc},
        "accion": "update",
        "campo": "id_concepto_asiento",
        "valor_anterior": str(anterior),
        "valor_nuevo": str(nuevo),
        "delta": str(nuevo - anterior),
        "check_id": "concepto_anulacion_incoherente",
        "referencia": "H05",
        "excluido": False,
    }


def _item_asiento(
    codmov: str,
    id_pc: int,
    id_ej: int,
    *,
    check_id: str = "comprobante_compra_pago_sin_asiento",
    concepto: int = 3,
    desc_concepto: str = "Compra",
) -> dict:
    return {
        "tabla": "cont_asiento",
        "clave": {"codigo_movimiento": codmov, "id_pc": id_pc, "nro_asiento": 100},
        "accion": "insert",
        "valor_anterior": None,
        "valor_nuevo": {
            "nro_asiento": 100,
            "fecha_asiento": "2024-01-15",
            "id_ejercicio": id_ej,
            "id_periodo": None,
            "codigo_movimiento": codmov,
            "debe_asiento": "100.00",
            "haber_asiento": "0.00",
            "id_pc": id_pc,
            "desc_renglon_asiento": "REGEN test",
            "desc_concepto_asiento": desc_concepto,
            "id_concepto_asiento": concepto,
            "desc_asiento": f"{desc_concepto} test",
        },
        "check_id": check_id,
        "excluido": False,
    }


def _crear_plan(items: list[dict], base_empresa: str = "test_empresa") -> PlanCorreccion:
    politica = _politica_base()
    fp = calcular_data_fingerprint(items)
    from django.utils import timezone

    ahora = timezone.now()
    return PlanCorreccion.objects.create(
        base_empresa=base_empresa,
        alcance={"id_ejercicio": 1},
        config_hash=calcular_config_hash(politica),
        data_fingerprint=fp,
        plan={
            "items": items,
            "backups_propuestos": {
                "cont_ejercicio_saldo_cta": "cont_ejercicio_saldo_cta_bkp_test",
            },
        },
        estado="propuesto",
        creado_por="tester",
        creado_en=ahora,
        expira_en=ahora + timedelta(minutes=30),
    )


class ContRecalculoApplyTestCase(TestCase):
    @override_settings(ENVIRONMENT="development")
    def test_apply_rechaza_sin_permiso_en_development(self):
        plan = _crear_plan([_item_saldo(10, 1, "100.00", "110.00")])
        with self.assertRaises(CorreccionContableError) as ctx:
            apply(
                plan.base_empresa,
                str(plan.dry_run_id),
                "tester",
                tiene_permiso_corregir=False,
            )
        self.assertIn("permiso", str(ctx.exception).lower())

    @override_settings(ENVIRONMENT="development")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    @patch("legacy_db.services.cont_recalculo_service.resolver_politica")
    def test_apply_rechaza_concurrencia_por_fingerprint(self, mock_politica, mock_pool):
        mock_politica.return_value = _politica_base()
        items = [_item_saldo(10, 1, "100.00", "110.00")]
        plan = _crear_plan(items)

        conn = MagicMock()
        dict_cursor = MagicMock()
        dict_cursor.fetchone.side_effect = [{"saldo_ejercicio_cta": "999.00"}]
        conn.cursor.side_effect = lambda *a, **k: dict_cursor
        pool = MagicMock()
        pool.get_connection.return_value.__enter__ = MagicMock(return_value=conn)
        pool.get_connection.return_value.__exit__ = MagicMock(return_value=False)
        mock_pool.return_value = pool

        with self.assertRaises(CorreccionContableError) as ctx:
            apply(
                plan.base_empresa,
                str(plan.dry_run_id),
                "tester",
                tiene_permiso_corregir=True,
            )
        self.assertIn("Concurrencia", str(ctx.exception))
        plan.refresh_from_db()
        self.assertEqual(plan.estado, "invalidado")

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    @patch("legacy_db.services.cont_recalculo_service.resolver_politica")
    def test_apply_log_lote_y_detalle_en_misma_transaccion(self, mock_politica, mock_pool):
        mock_politica.return_value = _politica_base()
        items = [_item_saldo(10, 1, "100.00", "110.00")]
        plan = _crear_plan(items)

        conn_ro = MagicMock()
        dict_ro = MagicMock()
        dict_ro.fetchone.return_value = {"saldo_ejercicio_cta": "100.00"}
        conn_ro.cursor.return_value = dict_ro
        conn_ro.__enter__ = MagicMock(return_value=conn_ro)
        conn_ro.__exit__ = MagicMock(return_value=False)

        conn_tx = MagicMock()
        cur_tx = MagicMock()
        dict_tx = MagicMock()

        import MySQLdb.cursors as mysql_cursors

        def _cursor(*args, **kwargs):
            if args and args[0] is mysql_cursors.DictCursor:
                return dict_tx
            return cur_tx

        conn_tx.cursor.side_effect = _cursor

        conn_tx_cm = MagicMock()
        conn_tx_cm.__enter__ = MagicMock(return_value=conn_tx)
        conn_tx_cm.__exit__ = MagicMock(return_value=False)

        pool = MagicMock()
        pool.get_connection.side_effect = [conn_ro, conn_tx_cm, conn_tx_cm]
        mock_pool.return_value = pool

        with patch(
            "legacy_db.services.cont_recalculo_service._RepoLectura.saldo_pc",
            return_value="Deudor",
        ):
            with patch(
                "legacy_db.services.cont_recalculo_service._crear_backups",
                return_value={"cont_ejercicio_saldo_cta": "cont_ejercicio_saldo_cta_bkp_x"},
            ):
                with patch(
                    "legacy_db.services.cont_recalculo_service._calcular_fingerprint_desde_legacy",
                    return_value=plan.data_fingerprint,
                ):
                    with patch(
                        "legacy_db.services.cont_recalculo_service._insertar_log_detalle"
                    ) as mock_log:
                        resultado = apply(
                            plan.base_empresa,
                            str(plan.dry_run_id),
                            "tester",
                            tiene_permiso_corregir=True,
                        )

        self.assertTrue(resultado["ok"])
        sqls = [str(c[0][0]) for c in cur_tx.execute.call_args_list if c[0]]
        self.assertTrue(any("cont_audit_correccion_lote" in s for s in sqls))
        mock_log.assert_called()
        self.assertEqual(conn_tx.commit.call_count, 1)
        plan.refresh_from_db()
        self.assertEqual(plan.estado, "aplicado")

    @override_settings(ENVIRONMENT="production")
    def test_reconstruccion_saldos_fingerprint_estable_sin_cambios(self):
        items = [_item_saldo(10, 1, "100.00", "100.00")]
        fp1 = calcular_data_fingerprint(items)
        fp2 = calcular_data_fingerprint(list(reversed(items)))
        self.assertEqual(fp1, fp2)
        self.assertTrue(fp1.startswith("v1:"))

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    @patch("legacy_db.services.cont_recalculo_service.resolver_politica")
    def test_regeneracion_no_duplica_si_asiento_existe(self, mock_politica, mock_pool):
        mock_politica.return_value = _politica_base()
        items = [_item_asiento("12345", 50, 1)]
        plan = _crear_plan(items)

        conn_ro = MagicMock()
        dict_ro = MagicMock()
        dict_ro.fetchone.side_effect = [{"saldo_ejercicio_cta": None}, {"1": 1}]
        conn_ro.cursor.return_value = dict_ro
        conn_ro.__enter__ = MagicMock(return_value=conn_ro)
        conn_ro.__exit__ = MagicMock(return_value=False)

        conn_tx = MagicMock()
        cur_tx = MagicMock()
        dict_tx = MagicMock()
        dict_tx.fetchone.side_effect = [
            None,
            {"1": 1},
        ]
        conn_tx.cursor.side_effect = lambda *a, **k: dict_tx if a and a[0] else cur_tx

        pool = MagicMock()
        call_n = {"v": 0}

        def _get_conn(base):
            call_n["v"] += 1
            ctx = MagicMock()
            ctx.__enter__.return_value = conn_ro if call_n["v"] == 1 else conn_tx
            ctx.__exit__.return_value = False
            return ctx

        pool.get_connection.side_effect = _get_conn
        mock_pool.return_value = pool

        with patch(
            "legacy_db.services.cont_recalculo_service._crear_backups",
            return_value={"cont_asiento": "cont_asiento_bkp_x"},
        ):
            with patch(
                "legacy_db.services.cont_recalculo_service._asiento_ya_existe",
                return_value=True,
            ):
                with patch(
                    "legacy_db.services.cont_recalculo_service._calcular_fingerprint_desde_legacy",
                    return_value=plan.data_fingerprint,
                ):
                    resultado = apply(
                        plan.base_empresa,
                        str(plan.dry_run_id),
                        "tester",
                        tiene_permiso_corregir=True,
                    )

        insert_asiento = [
            c for c in cur_tx.execute.call_args_list
            if c[0] and "INSERT INTO cont_asiento" in str(c[0][0])
        ]
        self.assertEqual(len(insert_asiento), 0)
        self.assertTrue(resultado["ok"])

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    @patch("legacy_db.services.cont_recalculo_service.resolver_politica")
    def test_regeneracion_venta_no_duplica_si_asiento_existe(self, mock_politica, mock_pool):
        mock_politica.return_value = _politica_base()
        items = [
            _item_asiento(
                "58305",
                60,
                1,
                check_id="comprobante_venta_cobranza_sin_asiento",
                concepto=1,
                desc_concepto="Venta",
            )
        ]
        plan = _crear_plan(items)

        conn_ro = MagicMock()
        dict_ro = MagicMock()
        dict_ro.fetchone.side_effect = [{"saldo_ejercicio_cta": None}, {"1": 1}]
        conn_ro.cursor.return_value = dict_ro
        conn_ro.__enter__ = MagicMock(return_value=conn_ro)
        conn_ro.__exit__ = MagicMock(return_value=False)

        conn_tx = MagicMock()
        cur_tx = MagicMock()
        dict_tx = MagicMock()
        dict_tx.fetchone.side_effect = [None, {"1": 1}]
        conn_tx.cursor.side_effect = lambda *a, **k: dict_tx if a and a[0] else cur_tx

        pool = MagicMock()
        call_n = {"v": 0}

        def _get_conn(base):
            call_n["v"] += 1
            ctx = MagicMock()
            ctx.__enter__.return_value = conn_ro if call_n["v"] == 1 else conn_tx
            ctx.__exit__.return_value = False
            return ctx

        pool.get_connection.side_effect = _get_conn
        mock_pool.return_value = pool

        with patch(
            "legacy_db.services.cont_recalculo_service._crear_backups",
            return_value={"cont_asiento": "cont_asiento_bkp_x"},
        ):
            with patch(
                "legacy_db.services.cont_recalculo_service._asiento_ya_existe",
                return_value=True,
            ):
                with patch(
                    "legacy_db.services.cont_recalculo_service._calcular_fingerprint_desde_legacy",
                    return_value=plan.data_fingerprint,
                ):
                    resultado = apply(
                        plan.base_empresa,
                        str(plan.dry_run_id),
                        "tester",
                        tiene_permiso_corregir=True,
                    )

        insert_asiento = [
            c for c in cur_tx.execute.call_args_list
            if c[0] and "INSERT INTO cont_asiento" in str(c[0][0])
        ]
        self.assertEqual(len(insert_asiento), 0)
        self.assertTrue(resultado["ok"])

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    @patch("legacy_db.services.cont_recalculo_service.resolver_politica")
    def test_apply_modo_rei_sin_aprobados_rechaza(self, mock_politica, mock_pool):
        mock_politica.return_value = _politica_base()
        plan = _crear_plan([])
        with self.assertRaises(CorreccionContableError) as ctx:
            apply(
                plan.base_empresa,
                str(plan.dry_run_id),
                "tester",
                tiene_permiso_corregir=True,
                modo="rei",
            )
        self.assertIn("aprobados", str(ctx.exception).lower())

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    @patch("legacy_db.services.cont_recalculo_service.resolver_politica")
    def test_apply_modo_rei_no_computable_rechaza(self, mock_politica, mock_pool):
        mock_politica.return_value = _politica_base()
        plan = _crear_plan([])
        plan.plan = {
            **plan.plan,
            "propuestas_rei": [
                {
                    "id_pc": 115,
                    "cod_pc": "210000",
                    "id_ejercicio": 1,
                    "rei_teorico": None,
                    "rei_actual": "0.00",
                    "delta": None,
                    "excluido": True,
                    "motivo_exclusion": "falta índice de cierre para 31/03/2026",
                    "codigos_movimiento_rei": [],
                    "referencia": "H02",
                }
            ],
        }
        plan.save(update_fields=["plan"])
        AprobacionREI.objects.create(
            dry_run_id=plan.dry_run_id,
            id_pc=115,
            id_ejercicio=1,
            rei_teorico=Decimal("0"),
            rei_actual=Decimal("0"),
            estado="aprobado",
        )
        with self.assertRaises(CorreccionContableError) as ctx:
            apply(
                plan.base_empresa,
                str(plan.dry_run_id),
                "tester",
                tiene_permiso_corregir=True,
                modo="rei",
            )
        self.assertIn("no computable", str(ctx.exception).lower())

    @override_settings(ENVIRONMENT="production")
    @patch("legacy_db.services.cont_recalculo_service.get_mysql_pool")
    @patch("legacy_db.services.cont_recalculo_service.resolver_politica")
    def test_apply_orden_rec07_concepto_insert_recompute(self, mock_politica, mock_pool):
        """REC-07: paso 2 UPDATE concepto → paso 3 INSERT fila → paso 4 UPDATE saldo."""
        mock_politica.return_value = _politica_base()
        items = [
            _item_saldo(10, 1, "100.00", "110.00"),
            _item_fila_saldo_insert(20, 1, "50.00"),
            _item_concepto_anul("8888", 5, 30, 4, 7),
        ]
        plan = _crear_plan(items)

        conn_ro = MagicMock()
        dict_ro = MagicMock()
        dict_ro.fetchone.return_value = {"saldo_ejercicio_cta": "100.00"}
        conn_ro.cursor.return_value = dict_ro
        conn_ro.__enter__ = MagicMock(return_value=conn_ro)
        conn_ro.__exit__ = MagicMock(return_value=False)

        conn_tx = MagicMock()
        cur_tx = MagicMock()
        dict_tx = MagicMock()

        import MySQLdb.cursors as mysql_cursors

        def _cursor(*args, **kwargs):
            if args and args[0] is mysql_cursors.DictCursor:
                return dict_tx
            return cur_tx

        conn_tx.cursor.side_effect = _cursor

        conn_tx_cm = MagicMock()
        conn_tx_cm.__enter__ = MagicMock(return_value=conn_tx)
        conn_tx_cm.__exit__ = MagicMock(return_value=False)

        pool = MagicMock()
        pool.get_connection.side_effect = [conn_ro, conn_tx_cm, conn_tx_cm]
        mock_pool.return_value = pool

        orden_aplicacion: list[str] = []

        def _concepto(*args, **kwargs):
            orden_aplicacion.append("concepto")
            return None

        def _saldo(*args, **kwargs):
            item = args[1]
            if item.get("accion") == "insert":
                orden_aplicacion.append("insert_saldo")
            else:
                orden_aplicacion.append("update_saldo")
            return None

        with patch(
            "legacy_db.services.cont_recalculo_service._RepoLectura.saldo_pc",
            return_value="Deudor",
        ):
            with patch(
                "legacy_db.services.cont_recalculo_service._crear_backups",
                return_value={
                    "cont_asiento": "cont_asiento_bkp_x",
                    "cont_ejercicio_saldo_cta": "cont_ejercicio_saldo_cta_bkp_x",
                },
            ):
                with patch(
                    "legacy_db.services.cont_recalculo_service._calcular_fingerprint_desde_legacy",
                    return_value=plan.data_fingerprint,
                ):
                    with patch(
                        "legacy_db.services.cont_recalculo_service._fila_saldo_existe",
                        return_value=False,
                    ):
                        with patch(
                            "legacy_db.services.cont_recalculo_service._aplicar_item_concepto",
                            side_effect=_concepto,
                        ):
                            with patch(
                                "legacy_db.services.cont_recalculo_service._aplicar_item_saldo",
                                side_effect=_saldo,
                            ):
                                with patch(
                                    "legacy_db.services.cont_recalculo_service._insertar_log_detalle"
                                ):
                                    apply(
                                        plan.base_empresa,
                                        str(plan.dry_run_id),
                                        "tester",
                                        tiene_permiso_corregir=True,
                                    )

        self.assertEqual(
            orden_aplicacion,
            ["concepto", "insert_saldo", "update_saldo"],
        )
