"""
Aplicación de reglas de plantilla sobre texto (Stage 5).

No muta ``parsed.header`` ni ``parsed.line_items``; produce ``template_application``.
"""

from __future__ import annotations

import re
from typing import Any

from factura_compra_captura.services.supplier_template_registry import SUPPLIER_TEMPLATES


def _lineas_item_desde_patron_linea_a_linea(
    texto: str, pattern: str
) -> list[dict[str, Any]]:
    """Aplica el patrón línea a línea (equivalente al parser de ítems genérico)."""
    out: list[dict[str, Any]] = []
    for line in (texto or "").splitlines():
        line = line.strip()
        if len(line) < 12:
            continue
        m = re.match(pattern, line)
        if not m:
            continue
        g = m.groups()
        desc = (g[0] or "").strip()
        if len(desc) < 3:
            continue
        nums = [g[1], g[2], g[3] if len(g) > 3 and g[3] else None]
        nums = [n for n in nums if n]
        if len(nums) < 2:
            continue
        out.append(
            {
                "descripcion": desc[:500],
                "cantidad": str(nums[0]).strip(),
                "precio_unitario": str(nums[1]).strip(),
                "source": "template_rule",
            }
        )
    return out


def build_template_application(
    texto: str,
    document_engine_v1: dict[str, Any],
    match: dict[str, Any],
) -> dict[str, Any]:
    """
    Construye vista enriquecida por plantilla. Si no hay match, devuelve bloque genérico inactivo.
    """
    tid = (match or {}).get("template_id")
    if not tid or tid == "generic":
        return {
            "schema_version": 1,
            "template_id": None,
            "active": False,
            "header_fields": {},
            "line_items_supplement": [],
            "notes": "Sin plantilla específica; usar solo motor genérico en parsed.*",
        }

    rules = SUPPLIER_TEMPLATES.get(tid) or {}
    header_fields: dict[str, str] = {}
    if rules.get("cae_regex"):
        cm = re.search(rules["cae_regex"], texto or "", re.IGNORECASE)
        if cm:
            header_fields["cae_numero"] = cm.group(1).strip()[:32]

    supplement: list[dict[str, Any]] = []
    rx = rules.get("extra_item_line_regex")
    if rx:
        candidatos = _lineas_item_desde_patron_linea_a_linea(texto or "", rx)
        parsed = (document_engine_v1.get("parsed") or {}).get("line_items") or []
        n_gen = len(parsed)
        if len(candidatos) > n_gen:
            supplement = candidatos[n_gen:]

    return {
        "schema_version": 1,
        "template_id": tid,
        "active": True,
        "matched_by": match.get("matched_by"),
        "header_fields": header_fields,
        "line_items_supplement": supplement,
        "notes": "Campos suplementarios; no sustituyen parsed.header / parsed.line_items.",
    }


def build_workflow_signals(document_engine_v1: dict[str, Any]) -> dict[str, Any]:
    """Señales no bloqueantes para revisión / UI."""
    vs = document_engine_v1.get("validation_summary") or {}
    stm = document_engine_v1.get("supplier_template_match") or {}
    return {
        "schema_version": 1,
        "supplier_template_id": stm.get("template_id"),
        "template_matched": stm.get("template_id") is not None,
        "suggested_review": bool(vs.get("has_warnings") or vs.get("has_errors")),
        "blocking_issues": False,
    }


def default_analyst_feedback() -> dict[str, Any]:
    """Estructura para correcciones de analista (persistencia externa / API futura)."""
    return {
        "schema_version": 1,
        "corrections": [],
    }


def append_analyst_correction(
    feedback: dict[str, Any] | None,
    *,
    campo: str,
    valor_anterior: str | None,
    valor_nuevo: str | None,
) -> dict[str, Any]:
    """Añade una corrección sin mutar estructuras ajenas al esquema Stage 5."""
    base = feedback if isinstance(feedback, dict) else default_analyst_feedback()
    if int(base.get("schema_version") or 0) != 1:
        base = default_analyst_feedback()
    lista = base.setdefault("corrections", [])
    lista.append(
        {
            "campo": (campo or "")[:200],
            "valor_anterior": valor_anterior,
            "valor_nuevo": valor_nuevo,
        }
    )
    return base
