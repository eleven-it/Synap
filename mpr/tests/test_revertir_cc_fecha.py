"""Tests del comando revertir_cc_fecha (sin DB real: cursor simulado)."""
from contextlib import contextmanager
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from mpr.management.commands.revertir_cc_fecha import (
    CONFIRMAR_RESET,
    MSG_CONFIRMAR_REQUERIDO,
    MSG_PRODUCCION_BLOQUEADA,
    movimiento_es_transicion_mpr,
    parse_fecha_arg,
    parse_fechas_args,
)

MOD = "mpr.management.commands.revertir_cc_fecha"
TABLAS = {
    "mpr_transicion_lote": "mpr_transicion_lote",
    "movimiento_stock": "movimiento_stock",
    "stock": "stock",
    "stock_deposito": "stock_deposito",
    "articulo": "articulo",
}


def _mov(cm, *, tipo="OPP", detalle="Transición MPR Produccion->SemiElaborado art.7", anulado="No"):
    return {
        "codigo_movimiento": cm,
        "tipo_mov": tipo,
        "motivo_movimiento": "Parte producción",
        "detalle": detalle,
        "anulado": anulado,
    }


class FakeCursor:
    """Cursor dict que responde por fragmento de SQL y registra escrituras."""

    def __init__(self, *, cc_rows, movs, stock_rows, saldos, otras_fechas=0, stock_tiene_anulado=True):
        self.cc_rows = cc_rows
        self.movs = movs
        self.stock_rows = stock_rows
        self.saldos = saldos  # {(art, dep): Decimal}
        self.otras_fechas = otras_fechas
        self.stock_tiene_anulado = stock_tiene_anulado
        self.executed = []
        self.rowcount = 1
        self._res = None
        self.cc_borrado = False

    def execute(self, sql, params=None):
        s = " ".join(sql.split())
        self.executed.append((s, list(params or [])))
        self._res = None
        if s.startswith("SELECT id_mpr_transicion_lote"):
            self._res = [] if self.cc_borrado else list(self.cc_rows)
        elif s.startswith("SELECT codigo_movimiento, tipo_mov"):
            self._res = [self.movs[c] for c in params if c in self.movs]
        elif s.startswith("SHOW COLUMNS"):
            self._res = [{"Field": "anulado"}] if self.stock_tiene_anulado else []
        elif s.startswith("SELECT CodigoMovimiento, IDArt"):
            self._res = [r for r in self.stock_rows if r["CodigoMovimiento"] in params]
        elif s.startswith("SELECT COUNT(*) AS n FROM `mpr_transicion_lote` WHERE codigo_movimiento"):
            self._res = [{"n": self.otras_fechas}]
        elif s.startswith("SELECT COUNT(*) AS n FROM `mpr_transicion_lote` WHERE fecha_produccion"):
            self._res = [{"n": 0 if self.cc_borrado else len(self.cc_rows)}]
        elif "FROM `stock_deposito`" in s and s.startswith("SELECT"):
            art, dep = params
            if (art, dep) in self.saldos:
                self._res = [{"id_stock_deposito": art * 100 + dep, "saldo": self.saldos[(art, dep)]}]
            else:
                self._res = []
        elif s.startswith("DELETE FROM `mpr_transicion_lote`"):
            self.cc_borrado = True
            self.rowcount = len(self.cc_rows)
        else:
            self.rowcount = 1

    def fetchone(self):
        return self._res[0] if self._res else None

    def fetchall(self):
        return list(self._res or [])

    def escrituras(self):
        return [
            (s, p)
            for s, p in self.executed
            if s.startswith(("UPDATE", "DELETE", "INSERT"))
        ]


def _cc(id_, cm, art=7, cant="10"):
    return {
        "id_mpr_transicion_lote": id_,
        "id_articulo": art,
        "tipo_origen": "Produccion",
        "tipo_destino": "SemiElaborado",
        "cantidad": Decimal(cant),
        "id_mpr_turno": 1,
        "id_operario": 3,
        "codigo_movimiento": cm,
    }


def _stock(cm, art, dep, entrada, salida, anulado="No"):
    return {
        "CodigoMovimiento": cm,
        "IDArt": art,
        "CodDeposito": dep,
        "Entrada": Decimal(entrada),
        "Salida": Decimal(salida),
        "anulado": anulado,
    }


def _correr(cursor, *args):
    @contextmanager
    def fake_mysql_cursor(base, dict_cursor=False):
        yield cursor

    out = StringIO()
    with mock.patch(f"{MOD}.mysql_cursor", fake_mysql_cursor), mock.patch(
        f"{MOD}._nombre_tabla", lambda cur, nombre: TABLAS.get(nombre)
    ):
        call_command(
            "revertir_cc_fecha",
            "--base-empresa=administranet1",
            "--fecha=22/07/2026",
            *args,
            stdout=out,
        )
    return out.getvalue()


class TestParseFechas(SimpleTestCase):
    def test_dd_mm_yyyy_e_iso(self):
        self.assertEqual(parse_fecha_arg("22/07/2026"), "2026-07-22")
        self.assertEqual(parse_fecha_arg("2026-07-22"), "2026-07-22")

    def test_multi_csv_dedup(self):
        self.assertEqual(
            parse_fechas_args(["22/07/2026", "23/07/2026,2026-07-22"]),
            ["2026-07-22", "2026-07-23"],
        )

    def test_invalida_y_vacia(self):
        with self.assertRaises(CommandError):
            parse_fecha_arg("no-es-fecha")
        with self.assertRaises(CommandError):
            parse_fechas_args([])


class TestMovimientoEsTransicion(SimpleTestCase):
    def test_transicion_valida(self):
        self.assertTrue(movimiento_es_transicion_mpr(_mov(1)))

    def test_tipo_distinto(self):
        self.assertFalse(movimiento_es_transicion_mpr(_mov(1, tipo="OPA")))

    def test_detalle_de_parte(self):
        self.assertFalse(movimiento_es_transicion_mpr(_mov(1, detalle="Parte de producción · x")))


class TestGuardas(SimpleTestCase):
    def test_apply_sin_confirmar(self):
        with self.assertRaisesMessage(CommandError, MSG_CONFIRMAR_REQUERIDO):
            call_command(
                "revertir_cc_fecha",
                "--fecha=22/07/2026",
                "--base-empresa=administranet1",
                "--apply",
                stdout=StringIO(),
            )

    def test_apply_produccion_bloqueada(self):
        with self.assertRaisesMessage(CommandError, MSG_PRODUCCION_BLOQUEADA):
            call_command(
                "revertir_cc_fecha",
                "--fecha=22/07/2026",
                "--base-empresa=administranet",
                "--apply",
                f"--confirmar={CONFIRMAR_RESET}",
                stdout=StringIO(),
            )

    def test_base_requerida(self):
        with self.assertRaises(CommandError):
            call_command("revertir_cc_fecha", "--fecha=22/07/2026", stdout=StringIO())


class TestDryRun(SimpleTestCase):
    def test_dry_run_no_escribe_y_avisa_negativo(self):
        cur = FakeCursor(
            cc_rows=[_cc(1, 500)],
            movs={500: _mov(500)},
            stock_rows=[_stock(500, 7, 1, "0", "10"), _stock(500, 7, 2, "10", "0")],
            saldos={(7, 1): Decimal("100"), (7, 2): Decimal("4")},
        )
        out = _correr(cur)
        self.assertEqual(cur.escrituras(), [])
        self.assertIn("DRY-RUN", out)
        self.assertIn("NEGATIVO", out)  # dep 2: 4 - 10 = -6
        self.assertIn("110", out)  # dep 1: 100 + 10


class TestApply(SimpleTestCase):
    def test_apply_revierte_stock_anula_y_borra_cc(self):
        cur = FakeCursor(
            cc_rows=[_cc(1, 500), _cc(2, None, cant="3")],
            movs={500: _mov(500)},
            stock_rows=[_stock(500, 7, 1, "0", "10"), _stock(500, 7, 2, "10", "0")],
            saldos={(7, 1): Decimal("100"), (7, 2): Decimal("40")},
        )
        out = _correr(cur, "--apply", f"--confirmar={CONFIRMAR_RESET}")
        w = cur.escrituras()
        updates_sd = {tuple(p): s for s, p in w if s.startswith("UPDATE `stock_deposito`")}
        # Salida del depósito 1 se devuelve (+10); Entrada al depósito 2 se descuenta (-10).
        self.assertIn((Decimal("110"), 701), updates_sd)
        self.assertIn((Decimal("30"), 702), updates_sd)
        self.assertEqual(len(updates_sd), 2)
        self.assertTrue(
            any(s.startswith("UPDATE `stock` SET anulado = 'Si'") and p == [500] for s, p in w)
        )
        self.assertTrue(
            any(s.startswith("UPDATE `movimiento_stock` SET anulado = 'Si'") and p == [500] for s, p in w)
        )
        self.assertIn(("DELETE FROM `mpr_transicion_lote` WHERE fecha_produccion = %s", ["2026-07-22"]), w)
        # No toca contadores ni histórico ni partes.
        sqls = " ".join(s for s, _ in w)
        for prohibido in ("codmov", "talonarios", "mpr_parte", "mpr_cc_borrador", "lista_produccion_historico"):
            self.assertNotIn(prohibido, sqls)
        self.assertIn("filas CC sin código: 1", out)

    def test_apply_idempotente_omite_ya_anulados(self):
        cur = FakeCursor(
            cc_rows=[_cc(1, 500)],
            movs={500: _mov(500, anulado="Si")},
            stock_rows=[_stock(500, 7, 1, "0", "10")],
            saldos={(7, 1): Decimal("100")},
        )
        _correr(cur, "--apply", f"--confirmar={CONFIRMAR_RESET}")
        w = cur.escrituras()
        self.assertFalse(any("stock_deposito" in s for s, _ in w))
        self.assertFalse(any(s.startswith("UPDATE `stock`") for s, _ in w))
        self.assertTrue(any(s.startswith("DELETE FROM `mpr_transicion_lote`") for s, _ in w))

    def test_apply_tipo_inesperado_aborta_sin_escribir(self):
        cur = FakeCursor(
            cc_rows=[_cc(1, 500)],
            movs={500: _mov(500, tipo="OPA", detalle="Armado pack")},
            stock_rows=[_stock(500, 7, 1, "0", "10")],
            saldos={(7, 1): Decimal("100")},
        )
        with self.assertRaisesMessage(CommandError, "no es una transición MPR"):
            _correr(cur, "--apply", f"--confirmar={CONFIRMAR_RESET}")
        self.assertEqual(cur.escrituras(), [])

    def test_apply_movimiento_inexistente_aborta(self):
        cur = FakeCursor(
            cc_rows=[_cc(1, 500)],
            movs={},
            stock_rows=[],
            saldos={},
        )
        with self.assertRaisesMessage(CommandError, "sin fila en movimiento_stock"):
            _correr(cur, "--apply", f"--confirmar={CONFIRMAR_RESET}")
        self.assertEqual(cur.escrituras(), [])

    def test_apply_codigo_compartido_con_otra_fecha_aborta(self):
        cur = FakeCursor(
            cc_rows=[_cc(1, 500)],
            movs={500: _mov(500)},
            stock_rows=[_stock(500, 7, 1, "0", "10")],
            saldos={(7, 1): Decimal("100")},
            otras_fechas=1,
        )
        with self.assertRaisesMessage(CommandError, "comparten"):
            _correr(cur, "--apply", f"--confirmar={CONFIRMAR_RESET}")
        self.assertEqual(cur.escrituras(), [])

    def test_apply_sin_cc_no_hace_nada(self):
        cur = FakeCursor(cc_rows=[], movs={}, stock_rows=[], saldos={})
        out = _correr(cur, "--apply", f"--confirmar={CONFIRMAR_RESET}")
        self.assertEqual(cur.escrituras(), [])
        self.assertIn("nada que revertir", out)
