"""Tests mínimos del comando revertir_partes_fecha (sin DB real)."""
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from mpr.management.commands.revertir_partes_fecha import (
    CONFIRMAR_RESET,
    MSG_CONFIRMAR_REQUERIDO,
    MSG_PRODUCCION_BLOQUEADA,
    _es_movimiento_parte_del_dia,
    parse_fecha_arg,
    parse_fechas_args,
)


class TestParseFechaArg(SimpleTestCase):
    def test_iso(self):
        self.assertEqual(parse_fecha_arg("2026-07-22"), "2026-07-22")

    def test_dd_mm_yyyy(self):
        self.assertEqual(parse_fecha_arg("22/07/2026"), "2026-07-22")

    def test_invalida(self):
        with self.assertRaises(CommandError):
            parse_fecha_arg("   ")


class TestParseFechasArgs(SimpleTestCase):
    def test_multi_y_csv(self):
        self.assertEqual(
            parse_fechas_args(["22/07/2026", "23/07/2026,24/07/2026"]),
            ["2026-07-22", "2026-07-23", "2026-07-24"],
        )

    def test_dedup(self):
        self.assertEqual(
            parse_fechas_args(["22/07/2026", "2026-07-22"]),
            ["2026-07-22"],
        )

    def test_vacio(self):
        with self.assertRaises(CommandError):
            parse_fechas_args([])


class TestEsMovimientoParteDelDia(SimpleTestCase):
    def test_uuid_legado(self):
        uid = "38e41d41-58bc-4674-9b45-02fd2f39d52a"
        self.assertTrue(
            _es_movimiento_parte_del_dia(
                f"OPP-parte {uid} desde MPR",
                "2026-08-24",
                "2026-08-24",
                [uid],
            )
        )

    def test_texto_nuevo_mismo_dia(self):
        self.assertTrue(
            _es_movimiento_parte_del_dia(
                "Parte de producción · 24/08/2026 · turno Tarde · OPT 181",
                "2026-08-24",
                "2026-08-24",
                [],
            )
        )

    def test_texto_compacto_mismo_dia(self):
        self.assertTrue(
            _es_movimiento_parte_del_dia(
                "Parte · turno Tarde · OPT 181 · Juan Pérez",
                "2026-08-24",
                "2026-08-24",
                [],
            )
        )

    def test_texto_nuevo_otro_dia(self):
        self.assertFalse(
            _es_movimiento_parte_del_dia(
                "Parte de producción · 24/08/2026 · turno Tarde",
                "2026-08-23",
                "2026-08-24",
                [],
            )
        )


class TestRevertirPartesFechaCommand(SimpleTestCase):
    def test_apply_sin_confirmar(self):
        with self.assertRaisesMessage(CommandError, MSG_CONFIRMAR_REQUERIDO):
            call_command(
                "revertir_partes_fecha",
                "--fecha=22/07/2026",
                "--base-empresa=administranet1",
                "--apply",
                stdout=StringIO(),
            )

    def test_apply_produccion_bloqueada(self):
        with self.assertRaisesMessage(CommandError, MSG_PRODUCCION_BLOQUEADA):
            call_command(
                "revertir_partes_fecha",
                "--fecha=22/07/2026",
                "--base-empresa=administranet",
                "--apply",
                f"--confirmar={CONFIRMAR_RESET}",
                stdout=StringIO(),
            )
