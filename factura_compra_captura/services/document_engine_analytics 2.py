"""
Métricas, analítica y observabilidad sobre document_engine_v1 (Stage 6).

Solo lectura / derivación; no muta parsed.* ni template_application.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def aggregate_correction_analytics(
    analyst_feedback: dict[str, Any] | None,
) -> dict[str, Any]:
    """Conteos por campo desde analyst_feedback.corrections."""
    fb = analyst_feedback if isinstance(analyst_feedback, dict) else {}
    correcciones = list(fb.get("corrections") or [])
    campos = [str(c.get("campo") or "").strip() for c in correcciones if isinstance(c, dict)]
    campos = [c for c in campos if c]
    cnt = Counter(campos)
    by_field = dict(sorted(cnt.items()))
    return {
        "schema_version": 1,
        "corrections_total": len(correcciones),
        "by_field": by_field,
        "fields_distinct": len(by_field),
    }


def build_document_engine_metrics(document_engine_v1: dict[str, Any]) -> dict[str, Any]:
    """Modelo de métricas derivadas (clasificación, calidad, validación, plantilla, líneas)."""
    clas = document_engine_v1.get("classification") or {}
    vs = document_engine_v1.get("validation_summary") or {}
    stm = document_engine_v1.get("supplier_template_match") or {}
    ta = document_engine_v1.get("template_application") or {}
    parsed = document_engine_v1.get("parsed") or {}
    items = list(parsed.get("line_items") or [])
    liq = document_engine_v1.get("line_items_quality") or {}

    tid = stm.get("template_id")
    matched = tid is not None and str(tid).strip() != ""
    hf = ta.get("header_fields") if ta.get("active") else {}
    if not isinstance(hf, dict):
        hf = {}
    supp = ta.get("line_items_supplement") or []
    if not isinstance(supp, list):
        supp = []

    return {
        "schema_version": 1,
        "classification": {
            "tipo_documento": clas.get("tipo_documento"),
            "confidence": float(clas.get("confidence") or 0.0),
        },
        "quality": {
            "document_score": float(document_engine_v1.get("document_score") or 0.0),
        },
        "validations": {
            "has_errors": bool(vs.get("has_errors")),
            "has_warnings": bool(vs.get("has_warnings")),
            "counts": dict(vs.get("counts") or {}),
            "health_score": float(vs.get("health_score") or 0.0),
        },
        "template_performance": {
            "matched": matched,
            "template_id": tid,
            "match_confidence": float(stm.get("confidence") or 0.0),
            "header_fields_extracted_count": len([k for k, v in hf.items() if v]),
            "line_supplement_count": len(supp),
        },
        "line_items": {
            "parsed_count": len(items),
            "item_count_quality": int(liq.get("item_count") or len(items)),
        },
    }


def build_workflow_facing_summary(document_engine_v1: dict[str, Any]) -> dict[str, Any]:
    """Vista resumida para bandejas / UI; no bloquea flujos."""
    ws = document_engine_v1.get("workflow_signals") or {}
    stm = document_engine_v1.get("supplier_template_match") or {}
    review = bool(ws.get("suggested_review"))
    tid = stm.get("template_id")
    ver = int(document_engine_v1.get("version") or 0)

    if review:
        headline = "Revisión sugerida: hay advertencias o errores en validaciones internas."
    else:
        headline = "Documento procesado; sin alertas graves en el motor de validación."

    digest = f"v{ver}|tmpl:{tid or 'none'}|review:{1 if review else 0}"

    return {
        "schema_version": 1,
        "headline": headline[:500],
        "review_recommended": review,
        "template_id": tid,
        "metrics_digest": digest[:200],
    }


def build_observability_context(document_engine_v1: dict[str, Any]) -> dict[str, Any]:
    """Campos string para logging estructurado (extra=) o agregadores."""
    m = document_engine_v1.get("document_engine_metrics") or {}
    tp = m.get("template_performance") or {}
    clas = m.get("classification") or {}
    val = m.get("validations") or {}
    q = m.get("quality") if isinstance(m.get("quality"), dict) else {}
    ver = int(document_engine_v1.get("version") or 0)
    doc_score = q.get("document_score")
    if doc_score is None:
        doc_score = document_engine_v1.get("document_score")
    log_fields = {
        "fc_ocr_engine": "document_engine_v1",
        "fc_ocr_stage_version": str(ver),
        "fc_ocr_classification": str(clas.get("tipo_documento") or ""),
        "fc_ocr_class_confidence": str(
            clas.get("confidence") if clas.get("confidence") is not None else ""
        ),
        "fc_ocr_doc_score": str(doc_score if doc_score is not None else ""),
        "fc_ocr_template_id": str(tp.get("template_id") or ""),
        "fc_ocr_template_matched": str(bool(tp.get("matched"))).lower(),
        "fc_ocr_validation_has_errors": str(bool(val.get("has_errors"))).lower(),
        "fc_ocr_validation_has_warnings": str(bool(val.get("has_warnings"))).lower(),
    }

    return {
        "schema_version": 1,
        "engine": "document_engine_v1",
        "stage_version": ver,
        "log_fields": log_fields,
    }


def build_analytics_snapshot(document_engine_v1: dict[str, Any]) -> dict[str, Any]:
    """
    Snapshot estable para persistencia opcional (JSON) sin copiar texto OCR ni parsed completo.
    """
    ws = document_engine_v1.get("workflow_signals") or {}
    return {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "document_engine_version": int(document_engine_v1.get("version") or 0),
        "document_engine_metrics": document_engine_v1.get("document_engine_metrics"),
        "correction_analytics": document_engine_v1.get("correction_analytics"),
        "workflow_facing_summary": document_engine_v1.get("workflow_facing_summary"),
        "workflow_signals_digest": {
            "template_matched": bool(ws.get("template_matched")),
            "suggested_review": bool(ws.get("suggested_review")),
        },
    }
