# -*- coding: utf-8 -*-
"""Tests unitarios del parser/resumen de auditoría pipeline MPR (sin MySQL)."""
from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import MagicMock

from mpr.auditoria_pipeline import (
    auditar_rango,
    iter_fechas,
    _ser,
)


class IterFechasTests(TestCase):
    def test_rango_inclusive(self):
        dias = iter_fechas(date(2026, 7, 22), date(2026, 7, 24))
        self.assertEqual(
            [d.isoformat() for d in dias],
            ["2026-07-22", "2026-07-23", "2026-07-24"],
        )

    def test_ser_decimal(self):
        self.assertEqual(_ser(Decimal("12.5")), 12.5)


class AuditarRangoMockCursorTests(TestCase):
    """Cursor mock mínimo: cada execute/fetch responde vacío coherente."""

    def test_rango_vacio_sin_error(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "host": "h",
            "port": 30804,
            "db": "administranet1",
            "ahora": date(2026, 8, 4),
            "n_partes": 0,
            "n_aprobados": 0,
            "n_otros": 0,
            "n_lineas": 0,
            "qty": 0,
            "n_arts": 0,
            "n_ops": 0,
            "n_turnos": 0,
            "n_opp": 0,
            "n_activos": 0,
            "n_anulados": 0,
            "n_lineas_cuerpo": 0,
            "qty_cuerpo": 0,
            "n_mov": 0,
            "n": 0,
            "qty_extra": 0,
            "usuarios": 0,
            "arts": 0,
            "ops": 0,
            "cc_n": 0,
            "sin_ms": 0,
            "fecha_diff": 0,
            "tipo_raro": 0,
            "ms_anulado": 0,
            "n_lotes": 0,
            "n_borrador": 0,
            "items": 0,
            "exitosos": 0,
            "fallidos": 0,
            "packs": 0,
            "n_packs": 0,
            "qty_abs": 0,
            "n_opa": 0,
        }
        cursor.fetchall.return_value = []
        out = auditar_rango(
            cursor, "administranet1", date(2026, 7, 22), date(2026, 7, 22)
        )
        self.assertEqual(out["base_empresa"], "administranet1")
        self.assertEqual(out["resumen"]["dias"], 1)
        self.assertEqual(out["dias"][0]["severidad"], "ok")
