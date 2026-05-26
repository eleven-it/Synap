"""
Detección de duplicados antes de aprobar expediente de compra.

Especificación: docs/compras/change_design.md §2.1–§2.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

from factura_compra_captura.models import ExpedienteFacturaCompra
from factura_compra_posting.legacy_posting_command_v1 import LegacyPostingCommandV1


class DuplicateCheckStatus(str, Enum):
    CLEAR = "clear"
    POSSIBLE_DUPLICATE_SYNAP = "possible_duplicate_synap"
    POSSIBLE_DUPLICATE_LEGACY = "possible_duplicate_legacy"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class DuplicateCheckResult:
    status: DuplicateCheckStatus
    reason_codes: tuple[str, ...]
    details: dict[str, Any]
    blocking: bool


def normalize_nro_comprobante_formateado(value: Any) -> str:
    """
    Normalización para clave de duplicado: trim, mayúsculas, espacios internos colapsados.
    """
    s = str(value or "").strip()
    s = " ".join(s.split())
    return s.upper()


def _posting_header_dict(expediente: ExpedienteFacturaCompra) -> dict[str, Any]:
    md = expediente.metadata or {}
    pv = md.get("posting_v1") or {}
    if not isinstance(pv, dict):
        return {}
    h = pv.get("header") or {}
    return h if isinstance(h, dict) else {}


def duplicate_key_from_expediente(expediente: ExpedienteFacturaCompra) -> tuple[Any, ...]:
    h = _posting_header_dict(expediente)
    tipo = str(h.get("tipo_factura") or "FA").strip().upper()
    nro = normalize_nro_comprobante_formateado(h.get("nro_comprobante_formateado"))
    prov = int(expediente.codigo_proveedor_legacy or 0)
    return (int(expediente.empresa_id), prov, tipo, nro)


def duplicate_key_from_cmd(cmd: LegacyPostingCommandV1) -> tuple[Any, ...]:
    tipo = str(cmd.header.tipo_factura or "FA").strip().upper()
    nro = normalize_nro_comprobante_formateado(cmd.header.nro_comprobante_formateado)
    prov = int(cmd.header.codigo_proveedor or 0)
    return (int(cmd.synap_empresa_id), prov, tipo, nro)


class DuplicateDetectionService:
    _ESTADOS_DUPLICADO = (
        ExpedienteFacturaCompra.Estado.APROBADO,
        ExpedienteFacturaCompra.Estado.APROBACION_SOLICITADA,
    )

    @staticmethod
    def check_for_approval(
        expediente: ExpedienteFacturaCompra,
        cmd: LegacyPostingCommandV1,
        *,
        exclude_expediente_id: UUID | None = None,
    ) -> DuplicateCheckResult:
        key_cmd = duplicate_key_from_cmd(cmd)
        excl = exclude_expediente_id if exclude_expediente_id is not None else expediente.id

        candidatos = ExpedienteFacturaCompra.objects.filter(
            empresa_id=expediente.empresa_id,
            estado__in=DuplicateDetectionService._ESTADOS_DUPLICADO,
        ).exclude(pk=excl)

        for otro in candidatos:
            if duplicate_key_from_expediente(otro) == key_cmd:
                return DuplicateCheckResult(
                    status=DuplicateCheckStatus.BLOCKED,
                    reason_codes=("duplicate_factura_synap",),
                    details={
                        "conflict_expediente_id": str(otro.id),
                        "key": {
                            "empresa_id": key_cmd[0],
                            "codigo_proveedor_legacy": key_cmd[1],
                            "tipo_factura": key_cmd[2],
                            "nro_comprobante_norm": key_cmd[3],
                        },
                    },
                    blocking=True,
                )

        return DuplicateCheckResult(
            status=DuplicateCheckStatus.CLEAR,
            reason_codes=(),
            details={"key": {"nro_comprobante_norm": key_cmd[3]}},
            blocking=False,
        )
