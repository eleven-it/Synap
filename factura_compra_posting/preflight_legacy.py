"""
Preflight duplicados / período fiscal (UT-PRE-*). Sin cursor MySQL real en tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from factura_compra_posting.contracts import PreflightResult


@dataclass
class PreflightLegacyPostingService:
    """
    `query_duplicate_count` devuelve número de filas duplicado (0 = ok).
    `query_period_open` True = período abierto.
    """

    query_duplicate_count: Callable[[], int]
    query_period_open: Callable[[], bool]
    duplicate_includes_fm: bool = False

    def run(self, *, tipo_factura: str, nro_busqueda: str) -> PreflightResult:
        if not self.query_period_open():
            return PreflightResult(
                ok=False,
                code="FISCAL_PERIOD_CLOSED",
                message="Período fiscal cerrado.",
            )
        n = self.query_duplicate_count()
        if n > 0:
            if tipo_factura == "FM" and not self.duplicate_includes_fm:
                return PreflightResult(ok=True)
            return PreflightResult(
                ok=False,
                code="DUPLICATE_INVOICE",
                message="Posible comprobante duplicado.",
            )
        return PreflightResult(ok=True)
