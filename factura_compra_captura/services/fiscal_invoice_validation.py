"""
Validación fiscal AFIP/ARCA antes de aprobar y verificación informativa en captura.

Especificación: docs/compras/change_design.md §5.3, §4.5.

En captura/revisión se persiste el resultado en ``metadata.compras.fiscal_afip_verificacion_captura``
sin bloquear el guardado: el usuario ve si el CAE coincide con AFIP cuando hay datos suficientes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
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


def infer_pto_vta_y_nro_cbte_desde_formateado(nro_formateado: str) -> tuple[int | None, int | None]:
    """
    Intenta obtener punto de venta y número de comprobante AFIP desde textos tipo
    ``FA-0001-00000100`` o ``0001-00000100`` (guiones o barras).
    """
    s = str(nro_formateado or "").strip().upper()
    if not s:
        return None, None
    s = s.replace("/", "-")
    parts = [p.strip() for p in s.split("-") if p.strip()]
    if len(parts) >= 3:
        try:
            return int(parts[1]), int(parts[2])
        except (TypeError, ValueError):
            pass
    if len(parts) == 2:
        try:
            return int(parts[0]), int(parts[1])
        except (TypeError, ValueError):
            pass
    return None, None


def _cae_desde_ocr_ultimo_documento(expediente) -> str:
    """
    CAE extraído por plantilla OCR (``template_application.header_fields.cae_numero``).
    """
    from factura_compra_captura.models import DocumentoFuente

    doc = (
        expediente.documentos_fuente.filter(
            estado_procesamiento=DocumentoFuente.EstadoProcesamiento.COMPLETADO,
        )
        .order_by("-creado_en")
        .first()
    )
    if not doc:
        return ""
    raw = (doc.resultado_ocr or {}).get("raw") or {}
    de = raw.get("document_engine_v1") or {}
    if not isinstance(de, dict):
        return ""
    ta = de.get("template_application") or {}
    if isinstance(ta, dict):
        hf = ta.get("header_fields") or {}
        if isinstance(hf, dict):
            cae = str(hf.get("cae_numero") or "").strip()
            if cae:
                return cae
    texto = str((doc.resultado_ocr or {}).get("texto_completo") or "")
    if texto:
        cm = re.search(r"CAE\s*N[°º]?\s*:?\s*(\d{10,20})", texto, re.IGNORECASE)
        if cm:
            return cm.group(1).strip()
    return ""


def resolver_cae_pto_nro_para_afip(expediente) -> tuple[str | None, int | None, int | None]:
    """
    CAE y ubicación del comprobante: cabecera de posting, CAE de OCR si falta,
    PV/número explícitos o inferidos desde ``nro_comprobante_formateado``.
    """
    h = _posting_header_dict(expediente)
    cae_raw = h.get("cae")
    cae = str(cae_raw).strip() if cae_raw is not None else ""
    if not cae:
        cae = _cae_desde_ocr_ultimo_documento(expediente)
    if not cae:
        return None, None, None
    try:
        pto = h.get("pto_vta_afip")
        pto_i = int(pto) if pto is not None and str(pto).strip() != "" else None
    except (TypeError, ValueError):
        pto_i = None
    try:
        nro = h.get("nro_cbte_afip")
        nro_i = int(nro) if nro is not None and str(nro).strip() != "" else None
    except (TypeError, ValueError):
        nro_i = None
    if pto_i is None or nro_i is None:
        inf_pv, inf_nro = infer_pto_vta_y_nro_cbte_desde_formateado(
            str(h.get("nro_comprobante_formateado") or "").strip()
        )
        if pto_i is None:
            pto_i = inf_pv
        if nro_i is None:
            nro_i = inf_nro
    return cae, pto_i, nro_i


def mensaje_verificacion_fiscal_captura_es(result: FiscalValidationResult) -> str:
    """Texto breve en español para UI y metadata de captura."""
    st = result.status
    if st == FiscalValidationStatus.VALID:
        return (
            "Los datos fiscales coinciden con AFIP: el CAE devuelto por WSFE "
            "es el mismo que el declarado para el punto de venta y número de comprobante."
        )
    if st == FiscalValidationStatus.SKIPPED_NO_CAE:
        return (
            "No hay CAE en la cabecera guardada ni detectado por OCR con plantilla: "
            "no se consultó AFIP (comprobantes sin FE o datos incompletos)."
        )
    if st == FiscalValidationStatus.SKIPPED_NON_AR:
        d = result.details.get("detail") or "Tipo de comprobante no consultable vía WSFE estándar."
        return str(d)
    if st == FiscalValidationStatus.ERROR_TRANSIENT:
        return (
            "AFIP no respondió o hubo un error transitorio de red al consultar el CAE. "
            "Podés guardar igual; en aprobación se volverá a intentar según modo estricto."
        )
    if st == FiscalValidationStatus.INVALID:
        if "fiscal_cae_mismatch" in result.reason_codes:
            return (
                "El CAE capturado no coincide con el autorizado en AFIP para ese "
                "punto de venta y número (o el comprobante no existe)."
            )
        if "fiscal_afip_not_configured" in result.reason_codes:
            return (
                "No se pudo consultar AFIP: falta base empresa / certificados FE, "
                "o faltan punto de venta y número de comprobante junto con el CAE."
            )
        msg = result.details.get("detail") or result.details.get("afip_error")
        if msg:
            return f"Verificación AFIP no superada: {str(msg)[:400]}"
        return "Verificación AFIP no superada."
    return "Estado fiscal desconocido."


class FiscalInvoiceValidationService:
    @staticmethod
    def validate_for_approval(
        expediente,
        cmd: LegacyPostingCommandV1,
        *,
        base_empresa: str | None = None,
    ) -> FiscalValidationResult:
        return FiscalInvoiceValidationService._validar_cae_afip(
            expediente,
            cmd,
            base_empresa=base_empresa,
            modo_captura=False,
        )

    @staticmethod
    def validate_for_captura(
        expediente,
        cmd: LegacyPostingCommandV1,
        *,
        base_empresa: str | None = None,
    ) -> FiscalValidationResult:
        """
        Misma lógica que aprobación pero **nunca** bloquea el guardado del borrador.
        Sirve para informar veracidad del CAE respecto de AFIP durante la captura.
        """
        r = FiscalInvoiceValidationService._validar_cae_afip(
            expediente,
            cmd,
            base_empresa=base_empresa,
            modo_captura=True,
        )
        return replace(r, blocking=False)

    @staticmethod
    def _validar_cae_afip(
        expediente,
        cmd: LegacyPostingCommandV1,
        *,
        base_empresa: str | None,
        modo_captura: bool,
    ) -> FiscalValidationResult:
        cae_declarado, pto_vta, nro_cbte = resolver_cae_pto_nro_para_afip(expediente)
        if not cae_declarado:
            return FiscalValidationResult(
                status=FiscalValidationStatus.SKIPPED_NO_CAE,
                reason_codes=(),
                details={},
                blocking=False,
            )

        tipo_cbte = str(cmd.header.tipo_factura or "FA").strip().upper()
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
                details={
                    "detail": (
                        "CAE presente pero sin punto de venta y número AFIP "
                        "(indicá pto_vta_afip y nro_cbte_afip o un comprobante formateado tipo FA-0001-00000100)."
                    )
                },
                blocking=not modo_captura,
            )

        if not base_empresa:
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_afip_not_configured",),
                details={"detail": "Sin base_empresa para consultar AFIP."},
                blocking=not modo_captura,
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
                    blocking=not modo_captura,
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
                    blocking=not modo_captura,
                )
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_afip_invalid",),
                details={"afip_error": str(err)[:300]},
                blocking=not modo_captura,
            )

        if not cae_afip:
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_afip_invalid",),
                details={"detail": "AFIP no devolvió CAE."},
                blocking=not modo_captura,
            )

        if str(cae_afip).strip() != cae_declarado:
            return FiscalValidationResult(
                status=FiscalValidationStatus.INVALID,
                reason_codes=("fiscal_cae_mismatch",),
                details={},
                blocking=not modo_captura,
            )

        return FiscalValidationResult(
            status=FiscalValidationStatus.VALID,
            reason_codes=(),
            details={"cae": cae_declarado[:20]},
            blocking=False,
        )
