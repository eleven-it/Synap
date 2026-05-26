"""
Contexto de revisión UI derivado de document_engine_v1 (Stage 7).

Solo lectura; no altera posting ni OCR.
"""

from __future__ import annotations

from typing import Any


def _evidencia_preview(evidencia: dict[str, Any] | None, max_len: int = 200) -> str:
    if not evidencia:
        return ""
    raw = evidencia.get("raw_text")
    if raw is None:
        return ""
    return str(raw)[:max_len]


def _campo_header_ui(campo: str, wrap: dict[str, Any]) -> dict[str, Any]:
    ev = wrap.get("evidencia") if isinstance(wrap.get("evidencia"), dict) else {}
    return {
        "campo": campo,
        "valor": wrap.get("valor"),
        "confidence": wrap.get("confidence"),
        "banda": wrap.get("banda"),
        "source": wrap.get("source"),
        "evidencia_preview": _evidencia_preview(ev),
    }


def _linea_item_ui(idx: int, item: dict[str, Any]) -> dict[str, Any]:
    campos_in = item.get("campos") or {}
    campos_out: dict[str, Any] = {}
    for ck, cv in campos_in.items():
        if not isinstance(cv, dict):
            continue
        ev = cv.get("evidencia") if isinstance(cv.get("evidencia"), dict) else {}
        campos_out[ck] = {
            "valor": cv.get("valor"),
            "confidence": cv.get("confidence"),
            "banda": cv.get("banda"),
            "source": cv.get("source"),
            "evidencia_preview": _evidencia_preview(ev),
        }
    return {
        "item_index": idx,
        "source_item": item.get("source"),
        "campos": campos_out,
    }


def build_revision_engine_context_for_ui(
    document_engine_v1: dict[str, Any] | None,
    *,
    analyst_feedback_persisted: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Subconjunto estable para la pantalla de revisión (cabecera/líneas con evidencia, métricas).
    """
    if not document_engine_v1:
        return None
    de = document_engine_v1
    parsed = de.get("parsed") or {}
    header = parsed.get("header") or {}
    items = list(parsed.get("line_items") or [])

    header_campos: list[dict[str, Any]] = []
    for key, wrap in header.items():
        if key in ("header_quality",) or not isinstance(wrap, dict):
            continue
        header_campos.append(_campo_header_ui(key, wrap))

    line_items_ui = [_linea_item_ui(i, it) for i, it in enumerate(items) if isinstance(it, dict)]

    af = analyst_feedback_persisted
    if not isinstance(af, dict) or not af:
        af = de.get("analyst_feedback")

    tp = (de.get("document_engine_metrics") or {}).get("template_performance") or {}

    return {
        "schema_version": 1,
        "engine_version": de.get("version"),
        "fiscal_type_detection": de.get("fiscal_type_detection"),
        "workflow_facing_summary": de.get("workflow_facing_summary"),
        "workflow_signals": de.get("workflow_signals"),
        "document_score": de.get("document_score"),
        "validation_summary": de.get("validation_summary"),
        "document_engine_metrics": de.get("document_engine_metrics"),
        "template_performance": {
            "matched": bool(tp.get("matched")),
            "template_id": tp.get("template_id"),
            "header_fields_extracted_count": tp.get("header_fields_extracted_count"),
            "line_supplement_count": tp.get("line_supplement_count"),
        },
        "header_campos": header_campos,
        "line_items_ui": line_items_ui,
        "analyst_feedback": af if isinstance(af, dict) else None,
    }
