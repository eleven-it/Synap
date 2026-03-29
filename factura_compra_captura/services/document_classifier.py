"""
Clasificador ligero de documento (factura probable vs desconocido).

Solo heurísticas por palabras clave y densidad de texto; sin ML.
"""

from __future__ import annotations

import re
from typing import Any

# Pesos por categoría (suma usada para normalizar score)
_KEYWORDS_FACTURA: tuple[tuple[str, float], ...] = (
    (r"\bfactura\b", 1.2),
    (r"\bcomprobante\b", 1.0),
    (r"\bcae\b", 1.3),
    (r"\bafip\b", 0.9),
    (r"\bcuit\b", 1.0),
    (r"\biva\b", 0.5),
    (r"\bimporte\s+total\b", 1.0),
    (r"\btotal\b", 0.4),
    (r"\bpunto\s+de\s+venta\b", 0.9),
    (r"\bpto\.?\s*venta\b", 0.8),
    (r"\bn[°º]?\s*comprobante\b", 0.9),
    (r"\bnota\s+de\s+cr[eé]dito\b", 0.8),
    (r"\bnota\s+de\s+d[eé]bito\b", 0.8),
)

_RE_CUIT = re.compile(r"\b\d{2}-\d{8}-\d{1}\b")
_RE_CUIT_11 = re.compile(r"\b\d{11}\b")
_RE_PV_NRO = re.compile(r"\b\d{4}\s*[-–]\s*\d{8}\b")


def _texto_desde_estructurado(ocr_structured: dict[str, Any] | None) -> str:
    if not ocr_structured or not isinstance(ocr_structured, dict):
        return ""
    if ocr_structured.get("error"):
        return ""
    partes: list[str] = []
    for w in ocr_structured.get("palabras_muestra") or []:
        t = (w.get("text") or "").strip()
        if t:
            partes.append(t)
    for pg in ocr_structured.get("pages") or []:
        for ln in pg.get("lines") or []:
            t = (ln.get("text") or "").strip()
            if t:
                partes.append(t)
    return " ".join(partes)


def clasificar_documento(
    texto_plano: str,
    ocr_structured: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Devuelve ``tipo_documento`` ∈ {``invoice_probable``, ``unknown``} y ``confidence`` 0..1.
    """
    t = (texto_plano or "").strip()
    t_low = t.lower()
    extra = _texto_desde_estructurado(ocr_structured)
    comb = f"{t_low} {extra.lower()}".strip()

    score_kw = 0.0
    hits = 0
    for pattern, peso in _KEYWORDS_FACTURA:
        if re.search(pattern, comb, re.IGNORECASE):
            score_kw += peso
            hits += 1

    if _RE_CUIT.search(comb) or _RE_CUIT_11.search(comb):
        score_kw += 1.2
        hits += 1
    if _RE_PV_NRO.search(comb):
        score_kw += 1.0
        hits += 1

    # Densidad: longitud útil y cantidad de líneas
    n_chars = len(re.sub(r"\s+", "", t))
    lineas = [ln for ln in t.splitlines() if ln.strip()]
    n_lineas = len(lineas)
    densidad = min(1.0, (n_chars / 3500.0) * 0.5 + min(n_lineas, 40) / 40.0 * 0.5)

    n_chars_extra = len(re.sub(r"\s+", "", extra))
    n_chars_eff = max(n_chars, n_chars_extra)

    # Penalizar texto casi vacío (salvo contenido en OCR estructurado)
    if n_chars_eff < 40:
        densidad *= 0.35

    # Combinar (score_kw acotado ~0..8 → normalizar)
    score_norm = min(1.0, score_kw / 5.5)
    if hits >= 5:
        score_norm *= 0.92

    confidence = min(1.0, 0.25 + 0.45 * score_norm + 0.35 * densidad)

    if score_kw >= 2.0 and (n_chars_eff >= 30 or n_chars_extra >= 10):
        tipo = "invoice_probable"
    elif score_kw >= 1.2 and (n_chars_eff >= 80 or n_lineas >= 6):
        tipo = "invoice_probable"
    elif score_norm >= 0.38 and densidad >= 0.25:
        tipo = "invoice_probable"
    else:
        tipo = "unknown"
        confidence = min(confidence, 0.55)

    return {
        "tipo_documento": tipo,
        "confidence": round(confidence, 4),
        "detalle": {
            "keyword_score": round(score_kw, 3),
            "keyword_hits": hits,
            "densidad": round(densidad, 4),
            "caracteres_texto": n_chars,
            "lineas": n_lineas,
        },
    }
