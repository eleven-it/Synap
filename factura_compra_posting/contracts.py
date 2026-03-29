"""
Contrato mínimo alineado a docs/compras/posting_contract.md (§4).
Fase 1: solo resultados y marcador de comando; sin validación completa LegacyPostingCommand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Protocol


@dataclass(frozen=True)
class LegacyPostingResult:
    success: Literal[True]
    codigo_movimiento: int
    nro_comprobante: str
    nro_asiento_contable: Optional[int]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class LegacyPostingFailure:
    success: Literal[False]
    code: str
    message: str
    detail: dict[str, str | int | None]
    rollback_performed: bool


@dataclass(frozen=True)
class PreflightResult:
    ok: bool
    code: Optional[str] = None
    message: Optional[str] = None


class LegacyPostingAdapter(Protocol):
    """Fachada posting; implementación real en Fase 4."""

    def execute(self, cmd: Any) -> LegacyPostingResult: ...

    def preflight(self, cmd: Any) -> PreflightResult: ...
