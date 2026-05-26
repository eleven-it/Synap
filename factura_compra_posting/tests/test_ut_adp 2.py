"""UT-ADP-* — orden de transacción sin MySQL (posting_tests.md §4)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from factura_compra_posting.legacy_posting_command_v1 import (
    LegacyPostingCommandV1,
    PostingContextV1,
    PostingHeaderV1,
    StockLineCommandV1,
)
from factura_compra_posting.recording_mysql_adapter import run_recording_posting


def _cmd():
    return LegacyPostingCommandV1(
        idempotency_key="t:1",
        expediente_id=uuid4(),
        synap_empresa_id=1,
        context=PostingContextV1(
            id_usuario_legacy=1,
            id_vendedor_usuario=1,
            cod_sucursal=1,
            fecha_servidor=date.today(),
        ),
        header=PostingHeaderV1(
            codigo_proveedor=1,
            fecha_comprobante=date.today(),
            importe_total=Decimal("10"),
            nro_comprobante_formateado="FA-1-1",
            tipo_factura="FA",
            tipo_factura_cabecera="Factura",
            origen="MANUAL",
            id_cond_compra=1,
            cond_compra_dias="0",
        ),
        lines=(StockLineCommandV1(orden=1, id_art=1, cantidad=Decimal("1")),),
    )


class RecordingAdapterTests(SimpleTestCase):
    def test_ut_adp_01_begin_primero(self):
        conn, out = run_recording_posting(_cmd())
        self.assertTrue(getattr(out, "success", False))
        self.assertEqual(conn.log[0], "BEGIN")

    def test_ut_adp_02_codmov_lock_antes_de_fases(self):
        conn, out = run_recording_posting(_cmd())
        self.assertTrue(out.success)
        self.assertTrue(any("FOR UPDATE" in e for e in conn.log))
        lock_i = next(i for i, e in enumerate(conn.log) if "FOR UPDATE" in e)
        p1_i = next(i for i, e in enumerate(conn.log) if "PHASE=P1" in e)
        self.assertLess(lock_i, p1_i)

    def test_ut_adp_03_commit_al_final(self):
        conn, out = run_recording_posting(_cmd())
        self.assertTrue(out.success)
        self.assertEqual(conn.log[-1], "COMMIT")

    def test_ut_adp_04_rollback_si_error_en_p3(self):
        conn, out = run_recording_posting(_cmd(), fail_after_phase="P3")
        self.assertFalse(out.success)  # type: ignore[union-attr]
        self.assertIn("ROLLBACK", conn.log)
        self.assertNotIn("COMMIT", conn.log)
