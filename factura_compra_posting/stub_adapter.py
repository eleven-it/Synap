"""
Adapter stub: no abre conexión MySQL ni importa drivers legacy.
"""

from __future__ import annotations

from typing import Any

from factura_compra_posting.contracts import LegacyPostingResult, PreflightResult


class FakeLegacyPostingAdapter:
    """Devuelve resultado sintético para Fase 1–3 (posting_contract §4)."""

    FAKE_CODMOV = 900_001
    FAKE_NRO = "FA-0001-00000001"

    def execute(self, cmd: Any) -> LegacyPostingResult:
        # Introspección opcional para tests (LegacyPostingCommandV1 u otro)
        _ = cmd
        return LegacyPostingResult(
            success=True,
            codigo_movimiento=self.FAKE_CODMOV,
            nro_comprobante=self.FAKE_NRO,
            nro_asiento_contable=None,
            warnings=("posting_simulado_stub",),
        )

    def preflight(self, cmd: Any) -> PreflightResult:
        _ = cmd
        return PreflightResult(ok=True)


class NoOpLegacyPostingAdapter:
    """Backend noop: no ejecuta posting."""

    def execute(self, cmd: Any) -> LegacyPostingResult:
        raise NotImplementedError(
            "Posting legacy desactivado (FACTURA_COMPRA_POSTING_BACKEND=noop)."
        )

    def preflight(self, cmd: Any) -> PreflightResult:
        return PreflightResult(ok=True)


def get_posting_adapter():
    from django.conf import settings

    backend = getattr(
        settings, "FACTURA_COMPRA_POSTING_BACKEND", "fake"
    )
    if backend == "legacy":
        raise RuntimeError(
            "Backend 'legacy' no está implementado en Fase 1 (solo fake|noop)."
        )
    if backend == "noop":
        return NoOpLegacyPostingAdapter()
    return FakeLegacyPostingAdapter()
