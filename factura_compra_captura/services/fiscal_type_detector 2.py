"""
Detector de tipo fiscal (letra + código AFIP) para facturas de compra.

Mapeo CbteTipo → AdministraNET (FA/FB/FC/FM):
  docs/self_checkout/AFIP_FECAEDetRequest_CAMPOS.md (1→FA, 6→FB, 11→FC).
  51→FM alineado a heurísticos existentes (MiPyME).
"""

from __future__ import annotations

import re
from typing import Any

DOC_REF_AFIP_MAPPING = "docs/self_checkout/AFIP_FECAEDetRequest_CAMPOS.md"

MAP_CBTE_ADMINNET: dict[int, str] = {
    1: "FA",
    6: "FB",
    11: "FC",
    51: "FM",
}

LETTER_TO_ADMINNET = {"A": "FA", "B": "FB", "C": "FC", "M": "FM"}

_RE_FACTURA_LETRA = re.compile(
    r"\b(?:FACTURA|NOTA\s+DE\s+CREDITO|NOTA\s+DE\s+CRÉDITO|NOTA\s+DE\s+DEBITO|NOTA\s+DE\s+DÉBITO)\s+([ABCM])\b",
    re.IGNORECASE,
)
_RE_COD = re.compile(
    r"(?:\bCOD\.?\s*|\bCód\.?\s*|\bCódigo\s*)(\d{1,4})\b",
    re.IGNORECASE,
)
_RE_CBTE = re.compile(
    r"(?:Cbte\s*Tipo|Tipo\s+(?:de\s+)?comprobante|Tipo\s+Cmp)\s*:?\s*(\d{1,4})\b",
    re.IGNORECASE,
)


def normalizar_codigo_cbte_afip(raw: str | int | None) -> int | None:
    if raw is None:
        return None
    s = re.sub(r"\D", "", str(raw))
    if not s:
        return None
    v = int(s, 10)
    return v if v > 0 else None


def _compactar(texto: str) -> str:
    t = (texto or "").replace("\xa0", " ")
    return re.sub(r"[\s\n\r]+", " ", t).strip()


def _document_kind_desde_texto(texto: str) -> str:
    t = (texto or "").upper()
    if "NOTA DE CRED" in t or "NOTA DE CRÉD" in t:
        return "NOTA_CREDITO"
    if "NOTA DE DEB" in t or "NOTA DE DÉB" in t:
        return "NOTA_DEBITO"
    if re.search(r"\bFACTURA\b", texto or "", re.IGNORECASE):
        return "FACTURA"
    return "UNKNOWN"


def _tipo_desde_letra_sola_cerca_factura(texto: str) -> tuple[str, str] | None:
    lines = [ln.rstrip() for ln in (texto or "").split("\n")]
    for i, ln in enumerate(lines[:120]):
        if not re.search(r"\bFACTURA\b", ln, re.IGNORECASE):
            continue
        for j in range(max(0, i - 8), min(len(lines), i + 12)):
            s = lines[j].strip()
            m = re.fullmatch(r"([ABCM])", s, re.IGNORECASE)
            if m:
                ch = m.group(1).upper()
                hit = LETTER_TO_ADMINNET.get(ch)
                if hit:
                    return hit, lines[j][:200]
    return None


_RE_COD_RUIDO = re.compile(
    r"(?:COD|Cód|Código)\.?\s*\.?\s*(\d{1,4})\b",
    re.IGNORECASE,
)


def _extraer_codigos(texto: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for pat in (_RE_CBTE, _RE_COD, _RE_COD_RUIDO):
        for m in pat.finditer(texto):
            cod = normalizar_codigo_cbte_afip(m.group(1))
            if cod is None or cod not in MAP_CBTE_ADMINNET:
                continue
            out.append((cod, m.group(0)))
            return out
    return out


def _extraer_letra_factura(texto: str) -> tuple[str, str] | None:
    m = _RE_FACTURA_LETRA.search(texto)
    if not m:
        return None
    ch = m.group(1).upper()
    adm = LETTER_TO_ADMINNET.get(ch)
    if not adm:
        return None
    return adm, m.group(0)


def _ocr_factura_letra_pagina1(
    ocr_structured: dict[str, Any] | None,
) -> tuple[str, str, str] | None:
    """Devuelve (adminnet, letra, línea) o None."""
    if not ocr_structured or ocr_structured.get("error"):
        return None
    for pg in ocr_structured.get("pages") or []:
        if int(pg.get("page_num") or 1) != 1:
            continue
        for ln in pg.get("lines") or []:
            tx = (ln.get("text") or "").strip()
            if not tx:
                continue
            m = _RE_FACTURA_LETRA.search(tx)
            if m:
                ch = m.group(1).upper()
                adm = LETTER_TO_ADMINNET.get(ch)
                if adm:
                    return adm, ch, tx
    return None


def detectar_tipo_fiscal(
    texto: str,
    ocr_structured: dict[str, Any] | None = None,
    campos_heuristicos: dict[str, Any] | None = None,
) -> dict[str, Any]:
    texto = texto or ""
    ch = campos_heuristicos or {}

    out: dict[str, Any] = {
        "schema_version": 1,
        "adminnet_tipo_factura": None,
        "fiscal_letter": None,
        "afip_cbte_code": None,
        "afip_cbte_code_raw": None,
        "document_kind": _document_kind_desde_texto(texto),
        "confidence": 0.0,
        "source": "unknown",
        "consistency_status": "unknown",
        "evidence": {"raw_text": "", "page": None, "bbox": None},
        "adminnet_mapping": {
            "doc_ref": DOC_REF_AFIP_MAPPING,
            "tabla_cbte": {str(k): v for k, v in MAP_CBTE_ADMINNET.items()},
        },
    }

    if not texto.strip():
        return out

    compact = _compactar(texto)

    ocr_hit = _ocr_factura_letra_pagina1(ocr_structured)
    ocr_adm = ocr_hit[0] if ocr_hit else None
    ocr_letter = ocr_hit[1] if ocr_hit else None
    ocr_line = ocr_hit[2] if ocr_hit else None

    codigos = _extraer_codigos(texto) or _extraer_codigos(compact)
    code_num: int | None = None
    code_raw: str | None = None
    code_adm: str | None = None
    if codigos:
        code_num, code_raw = codigos[0]
        code_adm = MAP_CBTE_ADMINNET.get(code_num)
        out["afip_cbte_code"] = code_num
        out["afip_cbte_code_raw"] = (code_raw or "")[:64]

    letra_fact = _extraer_letra_factura(texto) or _extraer_letra_factura(compact)
    letra_aisl = _tipo_desde_letra_sola_cerca_factura(texto)

    letter_adm: str | None = None
    letter_raw: str | None = None
    fiscal_letter: str | None = None
    if ocr_adm:
        letter_adm = ocr_adm
        fiscal_letter = ocr_letter
        letter_raw = ocr_line or ""
    elif letra_fact:
        letter_adm, letter_raw = letra_fact[0], letra_fact[1]
        m = _RE_FACTURA_LETRA.search(texto) or _RE_FACTURA_LETRA.search(compact)
        if m:
            fiscal_letter = m.group(1).upper()
    elif letra_aisl:
        letter_adm, letter_raw = letra_aisl[0], letra_aisl[1]
        fiscal_letter = None
        for k, v in LETTER_TO_ADMINNET.items():
            if v == letter_adm:
                fiscal_letter = k
                break

    if fiscal_letter is None and letter_adm:
        for k, v in LETTER_TO_ADMINNET.items():
            if v == letter_adm:
                fiscal_letter = k
                break

    # Fusión
    if code_adm and letter_adm:
        out["fiscal_letter"] = fiscal_letter
        if code_adm == letter_adm:
            out["adminnet_tipo_factura"] = code_adm
            out["confidence"] = 0.96
            out["source"] = "merged"
            out["consistency_status"] = "consistent"
            out["evidence"]["raw_text"] = ((code_raw or "") + " | " + (letter_raw or ""))[:500]
            if ocr_line:
                out["source"] = "structured_ocr_line"
                out["evidence"]["page"] = 1
        else:
            out["adminnet_tipo_factura"] = code_adm
            out["confidence"] = 0.72
            out["source"] = "merged"
            out["consistency_status"] = "inconsistent"
            out["evidence"]["raw_text"] = (
                f"Conflicto letra({letter_adm}) vs código AFIP ({code_adm}); "
                f"se usa código según {DOC_REF_AFIP_MAPPING}"
            )[:500]
            out["fiscal_letter"] = fiscal_letter
    elif code_adm:
        out["adminnet_tipo_factura"] = code_adm
        out["confidence"] = 0.9
        out["source"] = "afip_code_text"
        out["consistency_status"] = "consistent"
        out["evidence"]["raw_text"] = (code_raw or "")[:500]
        for k, v in LETTER_TO_ADMINNET.items():
            if v == code_adm:
                out["fiscal_letter"] = k
                break
    elif letter_adm:
        out["adminnet_tipo_factura"] = letter_adm
        out["fiscal_letter"] = fiscal_letter
        out["confidence"] = 0.88 if ocr_line else 0.85
        out["source"] = "structured_ocr_line" if ocr_line else (
            "factura_letra_text" if letra_fact else "isolated_letter_near_factura"
        )
        out["consistency_status"] = "consistent"
        out["evidence"]["raw_text"] = (letter_raw or "")[:500]
        if ocr_line:
            out["evidence"]["page"] = 1

    # Heurístico legado (cabecera parseada)
    if out["adminnet_tipo_factura"] is None:
        tf = (ch.get("tipo_factura") or "").strip().upper()
        if tf in ("FA", "FB", "FC", "FM"):
            out["adminnet_tipo_factura"] = tf
            out["confidence"] = 0.52
            out["source"] = "heuristic_campos"
            out["consistency_status"] = "unknown"
            out["evidence"]["raw_text"] = f"tipo_factura={tf}"
            for k, v in LETTER_TO_ADMINNET.items():
                if v == tf:
                    out["fiscal_letter"] = k
                    break

    out["adminnet_mapping"]["adminnet_tipo_factura"] = out.get("adminnet_tipo_factura")

    return out
