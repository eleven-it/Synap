"""Tests unitarios de checks con cursor MySQL mockeado."""
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from django.test import SimpleTestCase
from django.utils import timezone

from contabilidad_audit.services.checks.asientos import (
    asiento_balanceado,
    codigo_movimiento_huerfano,
    imputacion_a_no_imputable,
    nro_asiento_duplicado,
)
from contabilidad_audit.services.checks.cierres import (
    cierre_resultado_no_cero,
    reparto_cc_incompleto,
)
from contabilidad_audit.services.checks.compras_pagos import (
    asiento_compra_pago_desbalanceado_saldo_null,
    comprobante_compra_pago_sin_asiento,
    integridad_anulacion_compra_pago,
)
from contabilidad_audit.services.checks.ventas_cobranza import (
    comprobante_venta_cobranza_sin_asiento,
)
from contabilidad_audit.services.checks.conceptos import (
    concepto_anulacion_incoherente,
    concepto_no_normal,
)
from contabilidad_audit.services.checks.periodos import fecha_fuera_de_periodo, periodos_solapados
from contabilidad_audit.services.checks.saldos import (
    cuentas_sin_fila_saldo,
    saldo_ejercicio_vs_diario,
    saldo_periodo_vs_diario,
)
from contabilidad_audit.services.checks._sql import clasificar_delta
from contabilidad_audit.services.resultados import CorridaContexto


def _contexto(cursor):
    return CorridaContexto(
        cursor=cursor,
        corrida_id=str(uuid4()),
        config_hash="v1:test",
        fecha_corrida=timezone.now(),
    )


def _politica(**kwargs):
    base = {
        "tratamiento_anulados": "excluir",
        "politica_centavo": "diario_manda",
        "tolerancia_decimal": Decimal("0.005"),
        "prefijos_cuenta": {"resultado": ["4"], "activo": ["1"], "pasivo": ["2"], "pn": ["3"]},
    }
    base.update(kwargs)
    return base


class ChecksTestCase(SimpleTestCase):
    def test_asiento_balanceado_detecta_desbalance(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(1001, Decimal("100"), Decimal("98"), 5)]
        ctx = _contexto(cursor)
        result = asiento_balanceado(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.total_diferencias, 1)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H09")

    def test_asiento_balanceado_conservar_compensacion_centavo(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(1001, Decimal("100"), Decimal("99.99"), 5)]
        ctx = _contexto(cursor)
        result = asiento_balanceado(
            "empresa",
            {"id_ejercicio": 1},
            _politica(politica_centavo="conservar_compensacion"),
            ctx,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.total_diferencias, 0)
        self.assertIn("compensaciones_centavo", result.resumen)

    def test_saldo_ejercicio_vs_diario_delta(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [(10, 1, "110000", "Deudor", Decimal("500"))],
            [(10, Decimal("480"))],
        ]
        ctx = _contexto(cursor)
        result = saldo_ejercicio_vs_diario(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].delta, Decimal("20"))

    def test_concepto_anulacion_incoherente(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(500, 3, 4, 8)]
        ctx = _contexto(cursor)
        result = concepto_anulacion_incoherente(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H05")

    def test_comprobante_sin_asiento(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (Decimal("123"), "FA", "0001-00001234", 1, Decimal("1500"), "2024-01-15")
        ]
        ctx = _contexto(cursor)
        result = comprobante_compra_pago_sin_asiento(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H51")
        sql = cursor.execute.call_args[0][0]
        self.assertIn("cont_ejercicio", sql)
        self.assertEqual(cursor.execute.call_args[0][1], [1])

    def test_comprobante_sin_asiento_filtra_periodo(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        ctx = _contexto(cursor)
        result = comprobante_compra_pago_sin_asiento(
            "empresa",
            {"id_ejercicio": 2, "id_periodo": 84},
            _politica(),
            ctx,
        )
        self.assertTrue(result.ok)
        sql = cursor.execute.call_args[0][0]
        self.assertIn("cont_periodo", sql)
        self.assertEqual(cursor.execute.call_args[0][1], [2, 84])

    def test_comprobante_venta_cobranza_sin_asiento_factura(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (
                Decimal("999"),
                "FB",
                "0001-00005555",
                1,
                2,
                Decimal("2500"),
                Decimal("0"),
                "2025-06-10",
            )
        ]
        ctx = _contexto(cursor)
        result = comprobante_venta_cobranza_sin_asiento(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H54")
        self.assertEqual(result.diferencias[0].detalle["TipoComprobante"], "FB")
        self.assertIn("cont_ejercicio", cursor.execute.call_args[0][0])
        self.assertEqual(cursor.execute.call_args[0][1], [1])

    def test_comprobante_venta_cobranza_sin_asiento_rec(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (
                Decimal("888"),
                "REC",
                "0001-00009999",
                1,
                2,
                Decimal("0"),
                Decimal("1800"),
                "2025-07-01",
            )
        ]
        ctx = _contexto(cursor)
        result = comprobante_venta_cobranza_sin_asiento(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H55")
        self.assertEqual(result.diferencias[0].detalle["Importe"], "1800")

    def test_asiento_compra_pago_desbalanceado(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(Decimal("200"), Decimal("100"), Decimal("90"), 0)]
        ctx = _contexto(cursor)
        result = asiento_compra_pago_desbalanceado_saldo_null(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H53")
        sql = cursor.execute.call_args[0][0]
        self.assertIn("cont_ejercicio", sql)
        self.assertEqual(cursor.execute.call_args[0][1], [1])

    def test_regla_centavo_clasificar_delta(self):
        politica = _politica(politica_centavo="conservar_compensacion")
        reportar, tipo = clasificar_delta(Decimal("0.008"), politica)
        self.assertFalse(reportar)
        self.assertEqual(tipo, "compensacion_centavo")
        reportar2, _ = clasificar_delta(Decimal("0.02"), politica)
        self.assertTrue(reportar2)


class ChecksSinCoberturaTestCase(SimpleTestCase):
    def test_saldo_periodo_vs_diario_detecta_delta(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [(10, 1, 2, "110000", "Deudor", Decimal("500"))],
            [(10, 2, Decimal("480"))],
        ]
        ctx = _contexto(cursor)
        result = saldo_periodo_vs_diario(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H03")
        self.assertEqual(result.diferencias[0].delta, Decimal("20"))

    def test_saldo_periodo_vs_diario_sin_diferencias(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [[], []]
        ctx = _contexto(cursor)
        result = saldo_periodo_vs_diario(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.total_diferencias, 0)

    def test_cuentas_sin_fila_saldo_falta_ejercicio(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [(10, "110000", 2)],
            [],
            [(10, 2)],
        ]
        ctx = _contexto(cursor)
        result = cuentas_sin_fila_saldo(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H34")

    def test_cuentas_sin_fila_saldo_falta_periodo(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [(10, "110000", 2)],
            [(10,)],
            [],
        ]
        ctx = _contexto(cursor)
        result = cuentas_sin_fila_saldo(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H17")

    def test_cuentas_sin_fila_saldo_ok(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [
            [(10, "110000", 2)],
            [(10,)],
            [(10, 2)],
        ]
        ctx = _contexto(cursor)
        result = cuentas_sin_fila_saldo(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertTrue(result.ok)

    def test_imputacion_a_no_imputable(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(5001, 99, "100000", 12)]
        ctx = _contexto(cursor)
        result = imputacion_a_no_imputable(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H15")

    def test_imputacion_a_no_imputable_ok(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        ctx = _contexto(cursor)
        result = imputacion_a_no_imputable(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertTrue(result.ok)

    def test_nro_asiento_duplicado(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(42, 2, "5001,5002")]
        ctx = _contexto(cursor)
        result = nro_asiento_duplicado(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H06")
        self.assertEqual(result.diferencias[0].nro_asiento, 42)

    def test_codigo_movimiento_huerfano(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(9999,)]
        ctx = _contexto(cursor)
        result = codigo_movimiento_huerfano(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H08")
        sql = cursor.execute.call_args[0][0]
        self.assertIn("cont_ejercicio", sql)
        self.assertEqual(cursor.execute.call_args[0][1], [1])

    def test_fecha_fuera_de_periodo(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("5001", 10, "2024-03-15", 1, "2024-01-01", "2024-01-31"),
        ]
        ctx = _contexto(cursor)
        result = fecha_fuera_de_periodo(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H13")

    def test_fecha_fuera_de_periodo_ok(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("5001", 10, "2024-01-15", 1, "2024-01-01", "2024-01-31"),
        ]
        ctx = _contexto(cursor)
        result = fecha_fuera_de_periodo(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertTrue(result.ok)

    def test_periodos_solapados(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (1, 2, "2024-01-01", "2024-02-15", "2024-02-01", "2024-03-31"),
        ]
        ctx = _contexto(cursor)
        result = periodos_solapados(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H28")
        self.assertEqual(result.diferencias[0].id_periodo, 1)

    def test_cierre_resultado_no_cero(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(10, "410000", Decimal("150.50"))]
        ctx = _contexto(cursor)
        result = cierre_resultado_no_cero(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H11")

    def test_cierre_resultado_dentro_tolerancia(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(10, "410000", Decimal("0.001"))]
        ctx = _contexto(cursor)
        result = cierre_resultado_no_cero(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertTrue(result.ok)

    def test_reparto_cc_incompleto(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            ("5001", 10, Decimal("100"), Decimal("0"), Decimal("80")),
        ]
        ctx = _contexto(cursor)
        result = reparto_cc_incompleto(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H43")
        self.assertEqual(result.diferencias[0].delta, Decimal("20"))

    def test_concepto_no_normal(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(5, "Anulación", "Especial", "Normal")]
        ctx = _contexto(cursor)
        result = concepto_no_normal(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H37")

    def test_integridad_anulacion_compra_pago_faltantes(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(Decimal("100"), "FA", "0001-00001234")]
        cursor.fetchone.side_effect = [
            (0,),  # sin marcador
            (0, 2),  # pendientes=0, total=2
            (Decimal("100"), Decimal("100"), Decimal("100")),  # orig_tot
            None,  # sin contra
        ]
        ctx = _contexto(cursor)
        result = integridad_anulacion_compra_pago(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.diferencias[0].referencia_hallazgo, "H53")
        self.assertEqual(result.diferencias[0].id_ejercicio, 1)
        self.assertIn("falta_marcador_cuentaproveedor_cm0", result.diferencias[0].detalle["problemas"])
        self.assertIn("falta_contra_asiento", result.diferencias[0].detalle["problemas"])
        self.assertNotIn("asiento_original_no_anulado", result.diferencias[0].detalle["problemas"])
        sql = cursor.execute.call_args_list[0][0][0]
        self.assertIn("cont_ejercicio", sql)
        self.assertEqual(cursor.execute.call_args_list[0][0][1], [1])

    def test_integridad_anulacion_compra_pago_ok(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        ctx = _contexto(cursor)
        result = integridad_anulacion_compra_pago(
            "empresa",
            {"id_ejercicio": 1},
            _politica(),
            ctx,
        )
        self.assertTrue(result.ok)
