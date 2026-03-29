"""
Adapter de grabación: orden de transacción y fases P1–P9 sin SQL real.
Cumple test gate UT-ADP antes de cablear sentencias legacy (Fase 4).
"""

from __future__ import annotations

from typing import Callable, Optional

from factura_compra_posting.contracts import LegacyPostingFailure, LegacyPostingResult
from factura_compra_posting.fake_legacy_connection import FakeLegacyConnection
from factura_compra_posting.legacy_posting_command_v1 import LegacyPostingCommandV1


class RecordingLegacyMysqlAdapter:
    """
    Ejecuta secuencia lógica BEGIN → bloqueo codmov → P1..P9 → COMMIT.
    `sql_codmov_lock` debe contener subcadena reconocible por tests (p. ej. FOR UPDATE).
    """

    def __init__(
        self,
        conn: FakeLegacyConnection,
        *,
        sql_codmov_lock: str = "SELECT codigo FROM codmov WHERE codigo = %s FOR UPDATE",
        fail_after_phase: Optional[str] = None,
    ) -> None:
        self._conn = conn
        self._sql_codmov_lock = sql_codmov_lock
        self._fail_after_phase = fail_after_phase

    def execute(self, cmd: LegacyPostingCommandV1) -> LegacyPostingResult | LegacyPostingFailure:
        phases = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9")
        try:
            self._conn.begin()
            self._conn.execute(self._sql_codmov_lock, (1,))
            for ph in phases:
                self._conn.execute(f"-- PHASE={ph}", ())
                if self._fail_after_phase and ph == self._fail_after_phase:
                    raise RuntimeError(f"fallo_simulado_{ph}")
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            return LegacyPostingFailure(
                success=False,
                code="ADAPTER_ERROR",
                message=str(e),
                detail={"fase": self._fail_after_phase or ""},
                rollback_performed=True,
            )
        return LegacyPostingResult(
            success=True,
            codigo_movimiento=1,
            nro_comprobante=cmd.header.nro_comprobante_formateado,
            nro_asiento_contable=None,
            warnings=("recording_adapter",),
        )


def run_recording_posting(
    cmd: LegacyPostingCommandV1,
    *,
    conn_factory: Callable[[], FakeLegacyConnection] = FakeLegacyConnection,
    fail_after_phase: Optional[str] = None,
) -> tuple[FakeLegacyConnection, LegacyPostingResult | LegacyPostingFailure]:
    conn = conn_factory()
    adapter = RecordingLegacyMysqlAdapter(conn, fail_after_phase=fail_after_phase)
    out = adapter.execute(cmd)
    return conn, out
