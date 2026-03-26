"""
Validación fiscal AFIP/ARCA antes de aprobar (alcance v1: CAE opcional).

Especificación: docs/compras/change_design.md §5.3, §4.5.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from django.conf import settings
from django.http import HttpRequest

from factura_compra_posting.legacy_posting_command_v1 import LegacyPostingCommandV1


class FiscalValidationStatus(str, Enum):
    SKIPPED_NO_CAE = "skipped_no_cae"
    SKIPPED_NON_AR = "skipped_non_ar"
    SKIPPED_NO_CONFIG = "skipped_no_config"
    VALID = "valid"
    INVALID = "invalid"
    ERROR_TRANSIENT = "error_transient"


@dataclass(frozen=True)
class FiscalValidationResult:
    status: FiscalValidationStatus
    reason_codes: tuple[str, ...]
    details: dict[str, Any]
    blocking: bool


def _posting_header_dict(expediente) -> dict[str, Any]:
    md = expediente.metadata or {}
    pv = md.get("posting_v1") or {}
    if not isinstance(pv, dict):
        return {}
    h = pv.get("header") or {}
    return h if isinstance(h, dict) else {}


def tipo_factura_desde_expediente_metadata(metadata: dict | None) -> str | None:
    """Letra fiscal guardada en posting_v1.header o sugerida en proveedor_synap."""
    md = metadata or {}
    pv = md.get("posting_v1") or {}
    if isinstance(pv, dict):
        h = pv.get("header") or {}
        if isinstance(h, dict):
            tf = str(h.get("tipo_factura") or "").strip().upper()
            if tf:
                return tf
    ps = md.get("proveedor_synap") or {}
    tf = str(ps.get("tipo_factura_sugerida") or "").strip().upper()
    return tf or None


def resolve_base_empresa_for_compras(
    expediente,
    request: HttpRequest | None = None,
) -> str | None:
    md = expediente.metadata or {}
    compras = md.get("compras")
    if isinstance(compras, dict):
        v = compras.get("base_empresa")
        if isinstance(v, str) and v.strip():
            return v.strip()
    mapping = getattr(settings, "FACTURA_COMPRA_BASE_EMPRESA_BY_EMPRESA_ID", None) or {}
    v = mapping.get(expediente.empresa_id)
    if isinstance(v, str) and v.strip():
        return v.strip()
    if request is not None:
        try:
            session_user = request.session.get("user") or {}
        except Exception:
            session_user = {}
        be = session_user.get("base_empresa")
        if isinstance(be, str) and be.strip():
            return be.strip()
    return None


def _cae_y_puntos_fiscales(expediente) -> tuple[str | None, int | None, int | None]:
    h = _posting_header_dict(expediente)
    cae_raw = h.get("cae")
    cae = str(cae_raw).strip() if cae_raw is not None else ""
    if not cae:
        return None, None, None
    try:
        pto = h.get("pto_vta_afip")
        pto_i = int(pto) if pto is not None else None
    except (TypeError, ValueError):
        pto_i = None
    try:
        nro = h.get("nro_cbte_afip")
        nro_i = int(nro) if nro is not None else None
    except (TypeError, ValueError):
        nro_i = None
    return cae, pto_i, nro_i


class FiscalInvoiceValidationService:
    @staticmethod
    def validate_for_approval(
        expediente,
        cmd: LegacyPostingCommandV1,
        *,
        base_empresa: str | None = None,
    ) -> FiscalValidationResult:
        cae_declarado, pto_vta, nro_cbte = _cae_y_puntos_fiscales(expediente)
        if not cae_declarado:
            return FiscalValidationResult(
                status=FiscalValidationStatus.SKIPPED_NO_CAE,
                reason_codes=(),
                details={},
                blocking=False,
            )

        tipo_cbte = str(cmd.header.tipo_factura or "FA").strip().upper()
        # FM no usa el mismo código WSFE que FA/FB/FC; evitar consulta con tipo mal mapeado (p. ej. FB).
        if tipo_cbte == "FM":
            return FiscalValidationResult(
                status=FiscalValidationStatus.SKIPPED_NON_AR,
                reason_codes=("fiscal_skip_tipo_fm",),
                details={
                    "detail": "Tipo FM: no se consulta CAE vía WSFE estándar (FA/FB/FC)."
                },
                blocking=False,
            )

        if pto_vta is None or nro_cbte is None:
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_afip_not_configured",),
                details={"detail": "CAE declarado sin pto_vta_afip o nro_cbte_afip."},
                blocking=True,
            )

        if not base_empresa:
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_afip_not_configured",),
                details={"detail": "Sin base_empresa para consultar AFIP."},
                blocking=True,
            )

        tipo = tipo_cbte
        if tipo not in ("FA", "FB", "FC"):
            tipo = "FA"

        from self_checkout.fe_sync import consultar_cae_comprobante

        cae_afip, _vto, err = consultar_cae_comprobante(
            base_empresa,
            pto_vta,
            tipo,
            nro_cbte,
        )

        if err:
            err_l = str(err).lower()
            if (
                "afip no configurado" in err_l
                or "pyafipws no instalado" in err_l
            ):
                return FiscalValidationResult(
                    status=FiscalValidationStatus.INVALID,
                    reason_codes=("fiscal_afip_not_configured",),
                    details={"afip_error": str(err)[:300]},
                    blocking=True,
                )
            es_transitorio = (
                "timeout" in err_l
                or "network" in err_l
                or "wsaa" in err_l
                or "wsfe" in err_l
                or "conexión" in err_l
                or "conexion" in err_l
                or "temporal" in err_l
            )
            if es_transitorio:
                return FiscalValidationResult(
                    status=FiscalValidationStatus.ERROR_TRANSIENT,
                    reason_codes=("fiscal_afip_unavailable",),
                    details={"afip_error": str(err)[:300]},
                    blocking=True,
                )
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_afip_invalid",),
                details={"afip_error": str(err)[:300]},
                blocking=True,
            )

        if not cae_afip:
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_afip_invalid",),
                details={"detail": "AFIP no devolvió CAE."},
                blocking=True,
            )

        if str(cae_afip).strip() != cae_declarado:
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_cae_mismatch",),
                details={},
                blocking=True,
            )

        return FiscalValidationResult(
            status=FiscalValidationStatus.VALID,
            reason_codes=(),
            details={"cae": cae_declarado[:20]},
            blocking=False,
        )
