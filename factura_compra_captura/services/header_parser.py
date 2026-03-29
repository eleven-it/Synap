"""
Cabecera de factura con confianza y evidencia (Stage 2).

Usa OCR estructurado si existe; si no, heurísticas sobre texto plano alineadas al parser legacy.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from factura_compra_captura.services.confidence_catalog import (
    CONF_HEURISTIC_FECHA,
    CONF_HEURISTIC_PROVEEDOR,
    CONF_HEURISTIC_PV_NRO,
    CONF_HEURISTIC_TIPO,
    CONF_HEURISTIC_TOTAL,
    CONF_RAW_COD_AFIP,
    CONF_RAW_COMP_PV,
    CONF_RAW_FECHA,
    CONF_RAW_PV_NRO,
    CONF_RAW_TIPO,
    CONF_RAW_TOTAL,
    CONF_STRUCTURED_LINEA,
    CONF_STRUCTURED_TIPO_LINEA,
    CONF_STRUCTURED_TOKEN,
    CONF_STRUCTURED_TOTAL_LINEA,
    CONF_WEAK_CUIT_RAW,
    CONF_WEAK_CUIT_STRUCTURED,
    banda_desde_valor,
)
from factura_compra_captura.services.evidence_schema import evidencia_estandar
from factura_compra_captura.services.fiscal_type_detector import detectar_tipo_fiscal

SourceTipo = Literal["structured", "heuristic", "raw"]

_RE_CUIT = re.compile(r"\b(\d{2})-(\d{8})-(\d{1})\b")
_RE_CUIT_11 = re.compile(r"CUIT\s*:?\s*(\d{11})\b", re.IGNORECASE)
_RE_NRO_COMP = re.compile(
    r"(?:(?:(?:comp(?:robante)?|factura|n[°º]|nro\.?|número|num\.?)\s*[:\s]*)?"
    r"\b(\d{4})\s*[-–]\s*(\d{8})\b"
    r"|"
    r"\b(\d{4})\s+(\d{8})\b)",
    re.IGNORECASE,
)
_RE_COMP_NRO_PV = re.compile(
    r"Comp\.?\s*Nro:?\s*(\d{4,5})\s+(\d{8})\b",
    re.IGNORECASE,
)
_RE_FECHA = re.compile(
    r"(?:"
    r"(?:fecha\s*(?:de\s*)?(?:emisión|emision|factura|comp(?:robante)?)|"
    r"fecha\s*[:\s]+|"
    r"emisi[oó]n\s*[:\s]+)"
    r")?\s*"
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b",
    re.IGNORECASE,
)
_RE_FECHA_SUELTA = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_RE_TOTAL = re.compile(
    r"(?:total(?:\s+a\s+pagar)?|importe\s+total|total\s+factura)\s*[:\s]*"
    r"(?:\$|ARS|USD)?\s*"
    r"([\d]{1,3}(?:\.\d{3})*(?:,\d{1,4})|\d{1,4},\d{1,4})",
    re.IGNORECASE,
)
_RE_FACTURA_LETRA = re.compile(
    r"\b(?:FACTURA|NOTA\s+DE\s+CREDITO|NOTA\s+DE\s+CRÉDITO)\s+([ABCM])\b",
    re.IGNORECASE,
)
_RE_COD_ARCA = re.compile(
    r"(?:\bCOD\.?\s*|\bCód\.?\s*)(\d{1,3})\b",
    re.IGNORECASE,
)
_MAP_CBTE = {1: "FA", 6: "FB", 11: "FC", 51: "FM"}


def _normalizar_fecha(d: str, m: str, y: str) -> str:
    yi = int(y)
    if yi < 100:
        yi += 2000
    return f"{int(d):02d}/{int(m):02d}/{yi}"


def _campo_vacio() -> dict[str, Any]:
    return {
        "valor": None,
        "confidence": 0.0,
        "banda": "baja",
        "source": "raw",
        "evidencia": evidencia_estandar(),
    }


def _campo(
    valor: str | None,
    confidence: float,
    source: SourceTipo,
    *,
    page: int | None = None,
    bbox: dict[str, int] | None = None,
    raw_text: str = "",
) -> dict[str, Any]:
    conf = round(min(1.0, max(0.0, confidence)), 4)
    return {
        "valor": valor,
        "confidence": conf,
        "banda": banda_desde_valor(conf),
        "source": source,
        "evidencia": evidencia_estandar(page=page, bbox=bbox, raw_text=raw_text),
    }


def _iter_tokens_estructurados(
    ocr_structured: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not ocr_structured or ocr_structured.get("error"):
        return []
    out: list[dict[str, Any]] = []
    for w in ocr_structured.get("palabras_muestra") or []:
        page = w.get("page")
        if page is None:
            page = 1
        out.append(
            {
                "text": w.get("text") or "",
                "page": int(page) if page is not None else 1,
                "bbox": {
                    "left": int(w.get("left", 0)),
                    "top": int(w.get("top", 0)),
                    "width": int(w.get("width", 0)),
                    "height": int(w.get("height", 0)),
                },
            }
        )
    return out


def _buscar_regex_en_tokens(
    tokens: list[dict[str, Any]],
    pattern: re.Pattern[str],
) -> tuple[re.Match[str], dict[str, Any]] | None:
    for tok in tokens:
        m = pattern.search(tok["text"])
        if m:
            return m, tok
    return None


def _buscar_pattern_en_lineas_ocr(
    ocr_structured: dict[str, Any] | None,
    pattern: re.Pattern[str],
) -> tuple[re.Match[str], int, str] | None:
    """Busca en texto de líneas ya agrupadas (mejor para fechas/totales multipalabra)."""
    if not ocr_structured or ocr_structured.get("error"):
        return None
    for pg in ocr_structured.get("pages") or []:
        pnum = int(pg.get("page_num") or 1)
        for ln in pg.get("lines") or []:
            tx = (ln.get("text") or "").strip()
            if not tx:
                continue
            m = pattern.search(tx)
            if m:
                return m, pnum, tx
    return None


def _split_pv_numero(nro: str | None) -> tuple[str | None, str | None]:
    if not nro:
        return None, None
    s = nro.strip()
    if "-" in s:
        a, _, b = s.partition("-")
        if a.isdigit() and b.replace(" ", "").isdigit():
            return a.strip(), b.replace(" ", "").strip()[:20]
    m = _RE_COMP_NRO_PV.search(s)
    if m:
        return m.group(1), m.group(2)
    return None, None


def parsear_cabecera_documento(
    texto_plano: str,
    ocr_structured: dict[str, Any] | None,
    campos_heuristicos: dict[str, Any],
) -> dict[str, Any]:
    """
    Devuelve seis claves con modelo ``valor`` / ``confidence`` / ``source`` / ``evidencia``.
    """
    texto = texto_plano or ""
    cab = campos_heuristicos or {}
    tokens = _iter_tokens_estructurados(ocr_structured)

    proveedor = _campo_vacio()
    tipo_f = _campo_vacio()
    pv = _campo_vacio()
    nro = _campo_vacio()
    fecha = _campo_vacio()
    total = _campo_vacio()

    # --- Proveedor (prioridad structured: etiqueta en tokens contiguos difícil; usar cab) ---
    if cab.get("proveedor_texto"):
        proveedor = _campo(
            str(cab["proveedor_texto"])[:300],
            CONF_HEURISTIC_PROVEEDOR,
            "heuristic",
            raw_text=str(cab["proveedor_texto"])[:400],
        )

    # --- Tipo factura: detector fiscal (prioridad) > línea OCR > heurística cab > texto > COD AFIP ---
    det = detectar_tipo_fiscal(texto, ocr_structured, cab)
    det_tipo = det.get("adminnet_tipo_factura")
    det_conf = float(det.get("confidence") or 0)
    if det_tipo and det_conf >= 0.45:
        det_src = det.get("source") or ""
        ev_txt = str((det.get("evidence") or {}).get("raw_text") or "")[:400]
        if det_src == "structured_ocr_line":
            src_tipo: SourceTipo = "structured"
        elif det_src == "afip_code_text":
            src_tipo = "raw"
        else:
            src_tipo = "heuristic"
        tipo_f = _campo(
            det_tipo,
            min(1.0, max(0.5, det_conf)),
            src_tipo,
            raw_text=ev_txt,
        )
    line_tipo = _buscar_pattern_en_lineas_ocr(ocr_structured, _RE_FACTURA_LETRA)
    if not tipo_f["valor"] and line_tipo:
        mlt, pnum_lt, tx_lt = line_tipo
        letra = mlt.group(1).upper()
        mapeo = {"A": "FA", "B": "FB", "C": "FC", "M": "FM"}
        if letra in mapeo:
            tipo_f = _campo(
                mapeo[letra], CONF_STRUCTURED_TIPO_LINEA, "structured", page=pnum_lt, raw_text=tx_lt
            )
    tf_heur = cab.get("tipo_factura")
    if not tipo_f["valor"] and tf_heur:
        tipo_f = _campo(str(tf_heur), CONF_HEURISTIC_TIPO, "heuristic", raw_text=f"tipo_factura={tf_heur}")
    m_line = _RE_FACTURA_LETRA.search(texto)
    if not tipo_f["valor"] and m_line:
        letra = m_line.group(1).upper()
        mapeo = {"A": "FA", "B": "FB", "C": "FC", "M": "FM"}
        if letra in mapeo:
            val = mapeo[letra]
            tok_m = _buscar_regex_en_tokens(tokens, _RE_FACTURA_LETRA)
            if tok_m:
                tipo_f = _campo(
                    val,
                    CONF_STRUCTURED_TOKEN,
                    "structured",
                    page=tok_m[1]["page"],
                    bbox=tok_m[1]["bbox"],
                    raw_text=tok_m[1]["text"],
                )
            else:
                tipo_f = _campo(val, CONF_RAW_TIPO, "raw", raw_text=m_line.group(0))

    if not tipo_f["valor"]:
        for m in _RE_COD_ARCA.finditer(texto):
            try:
                cod = int(m.group(1))
            except ValueError:
                continue
            if cod in _MAP_CBTE:
                tipo_f = _campo(_MAP_CBTE[cod], CONF_RAW_COD_AFIP, "raw", raw_text=m.group(0))
                break

    # --- Punto de venta y número (un solo string comprobante → dos campos) ---
    nro_txt = cab.get("nro_comprobante_texto")
    pv_s, num_s = _split_pv_numero(nro_txt)
    if pv_s:
        pv = _campo(pv_s, CONF_HEURISTIC_PV_NRO, "heuristic", raw_text=str(nro_txt or ""))
    if num_s:
        nro = _campo(num_s, CONF_HEURISTIC_PV_NRO, "heuristic", raw_text=str(nro_txt or ""))

    m_tok = _buscar_regex_en_tokens(tokens, _RE_NRO_COMP)
    if m_tok:
        m, tok = m_tok
        g = m.groups()
        if g[0] and g[1]:
            pv = _campo(
                g[0],
                CONF_STRUCTURED_TOKEN,
                "structured",
                page=tok["page"],
                bbox=tok["bbox"],
                raw_text=tok["text"],
            )
            nro = _campo(
                g[1],
                CONF_STRUCTURED_TOKEN,
                "structured",
                page=tok["page"],
                bbox=tok["bbox"],
                raw_text=tok["text"],
            )
        elif g[2] and g[3]:
            pv = _campo(
                g[2],
                CONF_STRUCTURED_TOKEN,
                "structured",
                page=tok["page"],
                bbox=tok["bbox"],
                raw_text=tok["text"],
            )
            nro = _campo(
                g[3],
                CONF_STRUCTURED_TOKEN,
                "structured",
                page=tok["page"],
                bbox=tok["bbox"],
                raw_text=tok["text"],
            )
    elif not pv_s:
        m2 = _RE_NRO_COMP.search(texto)
        if m2:
            g = m2.groups()
            if g[0] and g[1]:
                pv = _campo(g[0], CONF_RAW_PV_NRO, "raw", raw_text=m2.group(0))
                nro = _campo(g[1], CONF_RAW_PV_NRO, "raw", raw_text=m2.group(0))
            elif g[2] and g[3]:
                pv = _campo(g[2], CONF_RAW_PV_NRO, "raw", raw_text=m2.group(0))
                nro = _campo(g[3], CONF_RAW_PV_NRO, "raw", raw_text=m2.group(0))

    m_pv = _RE_COMP_NRO_PV.search(texto)
    if m_pv and (pv["valor"] is None or nro["valor"] is None):
        if pv["valor"] is None:
            pv = _campo(m_pv.group(1), CONF_RAW_COMP_PV, "raw", raw_text=m_pv.group(0))
        if nro["valor"] is None:
            nro = _campo(m_pv.group(2), CONF_RAW_COMP_PV, "raw", raw_text=m_pv.group(0))

    # --- Fecha (líneas OCR primero; luego cab; luego texto plano) ---
    line_fecha = _buscar_pattern_en_lineas_ocr(ocr_structured, _RE_FECHA)
    if not line_fecha:
        line_fecha = _buscar_pattern_en_lineas_ocr(ocr_structured, _RE_FECHA_SUELTA)
    if line_fecha:
        m_l, pnum, tx = line_fecha
        val = _normalizar_fecha(m_l.group(1), m_l.group(2), m_l.group(3))
        fecha = _campo(val, CONF_STRUCTURED_LINEA, "structured", page=pnum, raw_text=tx)
    elif cab.get("fecha_comprobante_texto"):
        fecha = _campo(
            str(cab["fecha_comprobante_texto"]),
            CONF_HEURISTIC_FECHA,
            "heuristic",
            raw_text=str(cab["fecha_comprobante_texto"]),
        )
    else:
        fm = _RE_FECHA.search(texto)
        if not fm:
            fm = _RE_FECHA_SUELTA.search(texto)
        if fm:
            val = _normalizar_fecha(fm.group(1), fm.group(2), fm.group(3))
            fecha = _campo(val, CONF_RAW_FECHA, "raw", raw_text=fm.group(0))

    # --- Total ---
    line_tot = _buscar_pattern_en_lineas_ocr(ocr_structured, _RE_TOTAL)
    if line_tot:
        m_t, pnum_t, tx_t = line_tot
        total = _campo(
            m_t.group(1),
            CONF_STRUCTURED_TOTAL_LINEA,
            "structured",
            page=pnum_t,
            raw_text=tx_t,
        )
    elif cab.get("importe_total_texto"):
        total = _campo(
            str(cab["importe_total_texto"]),
            CONF_HEURISTIC_TOTAL,
            "heuristic",
            raw_text=str(cab["importe_total_texto"]),
        )
    else:
        tm = _RE_TOTAL.search(texto)
        if tm:
            total = _campo(tm.group(1), CONF_RAW_TOTAL, "raw", raw_text=tm.group(0))

    # CUIT en evidencia para proveedor si sigue vacío
    if proveedor["valor"] is None:
        m_c = _RE_CUIT.search(texto)
        if not m_c:
            m_c = _RE_CUIT_11.search(texto)
        if m_c:
            tok_c = _buscar_regex_en_tokens(tokens, _RE_CUIT)
            if tok_c:
                proveedor = _campo(
                    f"CUIT {m_c.group(0)}",
                    CONF_WEAK_CUIT_STRUCTURED,
                    "structured",
                    page=tok_c[1]["page"],
                    bbox=tok_c[1]["bbox"],
                    raw_text=tok_c[1]["text"],
                )
            else:
                proveedor = _campo(
                    f"CUIT {m_c.group(0)}",
                    CONF_WEAK_CUIT_RAW,
                    "raw",
                    raw_text=m_c.group(0),
                )

    return {
        "proveedor": proveedor,
        "tipo_factura": tipo_f,
        "punto_venta": pv,
        "numero": nro,
        "fecha": fecha,
        "total": total,
    }
