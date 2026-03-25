"""
Ítems de línea enriquecidos (Stage 3): OCR estructurado + fallback al heurístico legacy.

No modifica ``lineas_sugeridas``; solo produce vistas adicionales para ``document_engine_v1``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from factura_compra_captura.services.confidence_catalog import (
    CONF_LINE_ITEM_HEURISTIC_FALLBACK,
    CONF_LINE_ITEM_STRUCTURED,
    LINE_ITEMS_QUALITY_SCHEMA_VERSION,
    banda_desde_valor,
)
from factura_compra_captura.services.evidence_schema import evidencia_estandar

# Alineado a ``heuristic_pdf.parsear_texto_factura`` (ítems)
_RE_LINEA_ITEM = re.compile(
    r"^(.{4,100}?)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)(?:\s+(\d+(?:[.,]\d+)?))?\s*$"
)
_RE_LINEA_ITEM_UNIDADES = re.compile(
    r"^(.{4,120}?)\s+(\d+(?:[.,]\d+)?)\s+unidades\s+(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_RE_NRO_COMP = re.compile(
    r"(?:(?:(?:comp(?:robante)?|factura|n[°º]|nro\.?|número|num\.?)\s*[:\s]*)?"
    r"\b(\d{4})\s*[-–]\s*(\d{8})\b"
    r"|"
    r"\b(\d{4})\s+(\d{8})\b)",
    re.IGNORECASE,
)
_RE_CUIT = re.compile(r"\b(\d{2})-(\d{8})-(\d{1})\b")

_SKIP_LINE_PREFIXES_ITEM = (
    "código",
    "codigo",
    "descripción",
    "descripcion",
    "cantidad",
    "cant.",
    "p.unit",
    "precio",
    "importe",
    "subtotal",
    "iva",
    "bonif",
    "%",
    "factura",
    "original",
    "duplicado",
    "página",
    "pagina",
    "cae",
    "afip",
    "fecha de emisión",
    "fecha de emision",
    "vencimiento",
    "código producto",
)


def _monto_a_texto_plano(s: str) -> str:
    s = (s or "").strip().replace(" ", "")
    if not s:
        return ""
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        partes = s.split(",")
        if len(partes[-1]) in (1, 2):
            s = ",".join(partes[:-1]).replace(".", "") + "." + partes[-1]
        else:
            s = s.replace(",", ".")
    return s


def _linea_debe_omitirse(linea: str) -> bool:
    low = linea.lower().strip()
    if len(low) < 12:
        return True
    if any(low.startswith(p) for p in _SKIP_LINE_PREFIXES_ITEM):
        return True
    if _RE_NRO_COMP.search(linea) or _RE_CUIT.search(linea):
        return True
    return False


def _campo_item(
    valor: str,
    confidence: float,
    *,
    page: int | None,
    raw_text: str,
) -> dict[str, Any]:
    conf = round(min(1.0, max(0.0, confidence)), 4)
    return {
        "valor": valor,
        "confidence": conf,
        "banda": banda_desde_valor(conf),
        "evidencia": evidencia_estandar(page=page, bbox=None, raw_text=raw_text),
    }


def _parse_una_linea_texto(linea: str) -> dict[str, str] | None:
    linea = linea.strip()
    if _linea_debe_omitirse(linea):
        return None
    imu = _RE_LINEA_ITEM_UNIDADES.match(linea)
    if imu:
        desc = imu.group(1).strip()
        if len(desc) >= 3 and "código producto" not in desc.lower():
            return {
                "descripcion": desc[:500],
                "cantidad": _monto_a_texto_plano(imu.group(2)) or "1",
                "precio_unitario": _monto_a_texto_plano(imu.group(3)) or "0",
            }
    im = _RE_LINEA_ITEM.match(linea)
    if not im:
        return None
    desc = im.group(1).strip()
    if len(desc) < 3:
        return None
    nums = [im.group(2), im.group(3), im.group(4)]
    nums = [n for n in nums if n]
    if len(nums) < 2:
        return None
    return {
        "descripcion": desc[:500],
        "cantidad": _monto_a_texto_plano(nums[0]) or "1",
        "precio_unitario": _monto_a_texto_plano(nums[1] if len(nums) >= 2 else "0") or "0",
    }


def _extraer_desde_lineas_ocr(
    ocr_structured: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not ocr_structured or ocr_structured.get("error"):
        return []
    out: list[dict[str, Any]] = []
    for pg in ocr_structured.get("pages") or []:
        pnum = int(pg.get("page_num") or 1)
        for ln in pg.get("lines") or []:
            tx = (ln.get("text") or "").strip()
            parsed = _parse_una_linea_texto(tx)
            if not parsed:
                continue
            out.append(
                {
                    "item_index": len(out),
                    "source": "structured",
                    "campos": {
                        "descripcion": _campo_item(
                            parsed["descripcion"],
                            CONF_LINE_ITEM_STRUCTURED,
                            page=pnum,
                            raw_text=tx,
                        ),
                        "cantidad": _campo_item(
                            parsed["cantidad"],
                            CONF_LINE_ITEM_STRUCTURED,
                            page=pnum,
                            raw_text=tx,
                        ),
                        "precio_unitario": _campo_item(
                            parsed["precio_unitario"],
                            CONF_LINE_ITEM_STRUCTURED,
                            page=pnum,
                            raw_text=tx,
                        ),
                    },
                }
            )
    return out


def _envolver_lineas_heuristicas(
    lineas_sugeridas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, ln in enumerate(lineas_sugeridas or []):
        desc = str(ln.get("descripcion") or "")[:500]
        cant = str(ln.get("cantidad") or "1")
        precio = str(ln.get("precio_unitario") or "0")
        raw = f"{desc} {cant} {precio}".strip()
        ev_base = {"page": None, "raw_text": raw[:800]}
        out.append(
            {
                "item_index": i,
                "source": "heuristic_fallback",
                "campos": {
                    "descripcion": _campo_item(
                        desc,
                        CONF_LINE_ITEM_HEURISTIC_FALLBACK,
                        page=None,
                        raw_text=raw,
                    ),
                    "cantidad": _campo_item(
                        cant,
                        CONF_LINE_ITEM_HEURISTIC_FALLBACK,
                        page=None,
                        raw_text=raw,
                    ),
                    "precio_unitario": _campo_item(
                        precio,
                        CONF_LINE_ITEM_HEURISTIC_FALLBACK,
                        page=None,
                        raw_text=raw,
                    ),
                },
            }
        )
    return out


def _detect_tabular_layout(
    ocr_structured: dict[str, Any] | None,
    structured_count: int,
) -> bool:
    if structured_count >= 2:
        return True
    if not ocr_structured or ocr_structured.get("error"):
        return False
    words = ocr_structured.get("palabras_muestra") or []
    if len(words) < 9:
        return False
    rows: dict[int, list[Any]] = defaultdict(list)
    for w in words:
        top = int(w.get("top", 0)) // 8 * 8
        rows[top].append(w)
    filas_gruesas = sum(1 for _t, ws in rows.items() if len(ws) >= 3)
    return filas_gruesas >= 2


def _promedio_confianza_item(item: dict[str, Any]) -> float:
    campos = item.get("campos") or {}
    vals: list[float] = []
    for k in ("descripcion", "cantidad", "precio_unitario"):
        c = campos.get(k) or {}
        if isinstance(c, dict) and c.get("confidence") is not None:
            vals.append(float(c["confidence"]))
    return sum(vals) / len(vals) if vals else 0.0


def parsear_line_items_documento(
    texto_plano: str,
    ocr_structured: dict[str, Any] | None,
    lineas_sugeridas: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Devuelve ``items`` (lista enriquecida) y ``quality`` (métricas Stage 3).
    """
    _ = texto_plano  # reservado para extensiones (p. ej. cruce con texto plano)
    structured = _extraer_desde_lineas_ocr(ocr_structured)
    heuristic_count = len(lineas_sugeridas or [])

    if structured:
        items = structured
        fallback_used = False
        source = "structured"
    else:
        items = _envolver_lineas_heuristicas(lineas_sugeridas)
        fallback_used = True
        source = "heuristic_fallback"

    confs = [_promedio_confianza_item(it) for it in items]
    avg_conf = sum(confs) / len(confs) if confs else 0.0

    tabular = _detect_tabular_layout(ocr_structured, len(structured))

    menos_items = (
        bool(structured)
        and heuristic_count > len(structured)
        and len(structured) > 0
    )

    quality: dict[str, Any] = {
        "schema_version": LINE_ITEMS_QUALITY_SCHEMA_VERSION,
        "item_count": len(items),
        "avg_line_confidence": round(avg_conf, 4),
        "source": source,
        "fallback_used": fallback_used,
        "tabular_layout_detected": tabular,
        "heuristic_line_count": heuristic_count,
        "menos_items_que_heuristic": menos_items,
    }

    return {"items": items, "quality": quality}
