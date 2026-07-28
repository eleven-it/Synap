"""Tests mínimos del comando revertir_partes_fecha (sin DB real)."""
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from mpr.management.commands.revertir_partes_fecha import (
    MSG_APPLY_DESHABILITADO,
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


class TestRevertirPartesFechaCommand(SimpleTestCase):
    def test_apply_bloqueado(self):
        with self.assertRaisesMessage(CommandError, MSG_APPLY_DESHABILITADO):
            call_command(
                "revertir_partes_fecha",
                "--fecha=22/07/2026",
                "--apply",
                stdout=StringIO(),
            )
