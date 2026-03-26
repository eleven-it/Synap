"""
Extracción de texto PDF, OCR Tesseract en imágenes y heurísticas (facturas ES/AR).

- PDF: capa de texto con pypdf.
- JPEG/PNG: Tesseract en servidor (PWA / cámara móvil), luego mismas regex.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# MIME admitidos en settings para imagen → Tesseract
MIME_IMAGEN_OCR = frozenset({"image/jpeg", "image/png"})

# Debe coincidir con el comportamiento histórico de extraer_texto_imagen_tesseract
_TESSERACT_OCR_CONFIG = "--oem 1 --psm 3"


class TesseractNotAvailableError(Exception):
    """Falta el binario tesseract en PATH o ruta configurada."""


# ---------------------------------------------------------------------------
# Texto PDF
# ---------------------------------------------------------------------------


def extraer_texto_pdf(ruta_archivo: str) -> str:
    """Lee todas las páginas y concatena texto. Cadena vacía si no hay capa de texto."""
    from pypdf import PdfReader

    reader = PdfReader(ruta_archivo)
    partes: list[str] = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            partes.append(t)
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# OCR imagen (Tesseract)
# ---------------------------------------------------------------------------


def _cargar_pil_ocr(ruta_archivo: str):
    """Abre imagen, RGB y escala bordes (misma lógica histórica para OCR)."""
    from PIL import Image, UnidentifiedImageError

    try:
        img = Image.open(ruta_archivo)
    except UnidentifiedImageError as e:
        raise ValueError("OCR_IMAGEN_NO_VALIDA") from e
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    w, h = img.size
    m = max(w, h)
    if m > 0 and m < 1400:
        scale = 1400 / m
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS  # type: ignore[attr-defined]
        img = img.resize((int(w * scale), int(h * scale)), resample)
    elif m > 4200:
        scale = 4200 / m
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS  # type: ignore[attr-defined]
        img = img.resize((int(w * scale), int(h * scale)), resample)
    return img


def _tesseract_string_from_pil(
    img,
    *,
    lang: str = "spa+eng",
    tesseract_cmd: str | None = None,
) -> str:
    # Robustez: algunos pipelines pueden entregar np.ndarray/bytes-like.
    # pytesseract acepta PIL.Image.Image; normalizamos antes de invocar OCR.
    from PIL import Image
    import pytesseract

    if not isinstance(img, Image.Image):
        try:
            import numpy as np

            if isinstance(img, np.ndarray):
                img = Image.fromarray(img)
            else:
                img = Image.open(img)
        except Exception as e:
            raise ValueError(f"OCR_IMAGEN_NO_VALIDA:{type(img).__name__}") from e

    prev_cmd = pytesseract.pytesseract.tesseract_cmd
    try:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        try:
            # Algunas fotos móviles llegan como MPO/MPF y pytesseract rechaza
            # directamente el objeto PIL. Normalizamos a PNG temporal.
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            import os
            import tempfile

            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ) as tmp:
                    tmp_path = tmp.name
                img.save(tmp_path, format="PNG")
                return (
                    pytesseract.image_to_string(
                        tmp_path, lang=lang, config=_TESSERACT_OCR_CONFIG
                    )
                    or ""
                ).strip()
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
        except pytesseract.TesseractNotFoundError as e:
            raise TesseractNotAvailableError(
                "No se encontró el ejecutable Tesseract. En Docker ya está instalado; "
                "en local: instalar tesseract-ocr y paquetes spa/eng, o definir "
                "FACTURA_COMPRA_OCR_TESSERACT_CMD."
            ) from e
    finally:
        pytesseract.pytesseract.tesseract_cmd = prev_cmd


def extraer_texto_imagen_tesseract(
    ruta_archivo: str,
    *,
    lang: str = "spa+eng",
    tesseract_cmd: str | None = None,
) -> str:
    """Texto plano — mismo comportamiento que antes (escala + Tesseract)."""
    img = _cargar_pil_ocr(ruta_archivo)
    return _tesseract_string_from_pil(img, lang=lang, tesseract_cmd=tesseract_cmd)


def _procesar_imagen_ocr_por_modo(
    ruta_archivo: str,
    *,
    lang: str,
    tesseract_cmd: str | None,
    engine_mode: str,
) -> tuple[str, dict[str, Any] | None]:
    """
    ``legacy``: idéntico a ``extraer_texto_imagen_tesseract`` (sin metadata v1).

    ``preprocess_only`` / ``structured_ocr``: preprocesado OpenCV opcional + mismo parser;
    datos estructurados solo en ``structured_ocr``.
    """
    mode = (engine_mode or "legacy").strip().lower()
    if mode not in ("legacy", "preprocess_only", "structured_ocr"):
        mode = "legacy"

    if mode == "legacy":
        return extraer_texto_imagen_tesseract(
            ruta_archivo, lang=lang, tesseract_cmd=tesseract_cmd
        ), None

    from factura_compra_captura.ocr.image_preprocess import preprocesar_imagen_factura
    from factura_compra_captura.ocr.tesseract_structured import (
        construir_ocr_structured_desde_imagen,
    )

    img = _cargar_pil_ocr(ruta_archivo)
    img_ocr, pre_meta = preprocesar_imagen_factura(img)

    texto = _tesseract_string_from_pil(
        img_ocr, lang=lang, tesseract_cmd=tesseract_cmd
    )

    de_v1: dict[str, Any] = {
        "version": 1,
        "engine_mode": mode,
        "preprocess": pre_meta,
        "ocr_structured": None,
    }
    if mode == "structured_ocr":
        try:
            de_v1["ocr_structured"] = construir_ocr_structured_desde_imagen(
                img_ocr,
                lang=lang,
                tesseract_cmd=tesseract_cmd,
                config=_TESSERACT_OCR_CONFIG,
            )
        except Exception as e:
            logger.warning(
                "OCR estructurado (TSV) falló; se conserva texto plano del OCR. error=%s",
                str(e)[:400],
            )
            de_v1["ocr_structured"] = {"error": str(e)[:500], "fuente": "tesseract_tsv"}

    return texto, de_v1


def _enriquecer_raw_document_engine_stage2(
    raw: dict[str, Any],
    texto: str,
    campos_cabecera: dict[str, Any],
    lineas_sugeridas: list[dict[str, Any]],
    *,
    ocr_structured: dict[str, Any] | None,
    document_engine_v1_base: dict[str, Any] | None,
    engine_mode: str | None,
) -> None:
    """
    Añade Stage 2/2.5 (cabecera, calidad), Stage 3 (ítems), Stage 4 (validaciones),
    Stage 5 (plantillas) y Stage 6 (métricas / observabilidad) a ``document_engine_v1``.
    No modifica ``campos_cabecera`` ni ``lineas_sugeridas`` del resultado principal.
    """
    from factura_compra_captura.services.document_classifier import clasificar_documento
    from factura_compra_captura.services.document_header_quality import (
        construir_paquete_calidad_cabecera,
    )
    from factura_compra_captura.services.header_parser import parsear_cabecera_documento
    from factura_compra_captura.services.line_items_parser import parsear_line_items_documento
    from factura_compra_captura.services.document_validation_engine import (
        ejecutar_validaciones_documento,
    )

    classification = clasificar_documento(texto, ocr_structured)
    from factura_compra_captura.services.fiscal_type_detector import detectar_tipo_fiscal

    header = parsear_cabecera_documento(texto, ocr_structured, campos_cabecera)
    calidad = construir_paquete_calidad_cabecera(
        classification, header, campos_cabecera
    )
    line_pkg = parsear_line_items_documento(
        texto, ocr_structured, lineas_sugeridas
    )
    de: dict[str, Any] = dict(document_engine_v1_base) if document_engine_v1_base else {}
    if not document_engine_v1_base and engine_mode:
        de["engine_mode"] = engine_mode
    de["version"] = max(int(de.get("version") or 1), 4)
    de["classification"] = classification
    de["fiscal_type_detection"] = detectar_tipo_fiscal(
        texto, ocr_structured, campos_cabecera
    )
    de["document_score"] = calidad["document_score"]
    de["parsed"] = {
        "header": header,
        "header_quality": {
            "campos_criticos": calidad["campos_criticos"],
            "consistencia_legacy": calidad["consistencia_legacy"],
            "componentes_document_score": calidad["componentes_document_score"],
            "pesos_document_score": calidad["pesos_document_score"],
        },
        "line_items": line_pkg["items"],
    }
    de["line_items_quality"] = line_pkg["quality"]
    val_pkg = ejecutar_validaciones_documento(de)
    de["validations"] = val_pkg["validations"]
    de["validation_summary"] = val_pkg["validation_summary"]

    # Stage 5: plantillas por proveedor (aditivo), señales de flujo y feedback de analista
    from factura_compra_captura.services.supplier_template_matcher import (
        match_supplier_template,
    )
    from factura_compra_captura.services.supplier_template_engine import (
        build_template_application,
        build_workflow_signals,
        default_analyst_feedback,
    )

    stm = match_supplier_template(campos_cabecera, header)
    de["supplier_template_match"] = stm
    de["template_application"] = build_template_application(texto, de, stm)
    de["workflow_signals"] = build_workflow_signals(de)
    de["analyst_feedback"] = default_analyst_feedback()

    # Stage 6: métricas, analítica de correcciones, observabilidad y snapshot (aditivo)
    from factura_compra_captura.services.document_engine_analytics import (
        aggregate_correction_analytics,
        build_analytics_snapshot,
        build_document_engine_metrics,
        build_observability_context,
        build_workflow_facing_summary,
    )

    de["correction_analytics"] = aggregate_correction_analytics(de.get("analyst_feedback"))
    de["document_engine_metrics"] = build_document_engine_metrics(de)
    de["version"] = max(int(de.get("version") or 1), 7)
    de["workflow_facing_summary"] = build_workflow_facing_summary(de)
    de["observability"] = build_observability_context(de)
    de["analytics_snapshot"] = build_analytics_snapshot(de)
    raw["document_engine_v1"] = de


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------

_RE_NRO_COMP = re.compile(
    r"(?:(?:(?:comp(?:robante)?|factura|n[°º]|nro\.?|número|num\.?)\s*[:\s]*)?"
    r"\b(\d{4})\s*[-–]\s*(\d{8})\b"
    r"|"
    r"\b(\d{4})\s+(\d{8})\b)",
    re.IGNORECASE,
)
# AFIP común: "Comp. Nro:00004 00000037" (sin espacio tras ":", PV 4–5 dígitos)
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
_RE_FECHA_YMD_SUELTA = re.compile(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b")

_RE_CUIT = re.compile(r"\b(\d{2})-(\d{8})-(\d{1})\b")
# CUIT sin guiones junto a etiqueta (p. ej. "CUIT: 30719081076")
_RE_CUIT_11_ETIQUETA = re.compile(r"CUIT\s*:?\s*(\d{11})\b", re.IGNORECASE)

# Solo importes con coma decimal (evita capturar "315" como prefijo de "3154720,97" tras "Importe Total: $")
_RE_TOTAL = re.compile(
    r"(?:total(?:\s+a\s+pagar)?|importe\s+total|total\s+factura)\s*[:\s]*"
    r"(?:\$|ARS|USD)?\s*"
    r"([\d]{1,3}(?:\.\d{3})*(?:,\d{1,4})|\d{1,4},\d{1,4})",
    re.IGNORECASE,
)
# Variante común: "TOTAL" y el importe en la misma línea con espacios
_RE_TOTAL_SUELTO = re.compile(
    r"\btotal\b\s+\$?\s*([\d]{1,3}(?:\.\d{3})*(?:,\d{1,4})?|\d+(?:[.,]\d{1,4})?)\s*$",
    re.IGNORECASE,
)

# Solo al inicio de línea: evita que "Emisión" dentro de "Fecha de Emisión" dispare el match.
# Requiere ":" después de la etiqueta para no confundir "PROVEEDOR EJEMPLO S.R.L." (razón en línea)
# con una etiqueta "Proveedor" + valor.
_RE_PROV_LABEL = re.compile(
    r"(?im)^\s*(?:"
    r"raz[oó]n\s+social|proveedor|vendedor|emisor|emisi[oó]n"
    r")\s*:\s*(.+)$",
)

# Línea tipo detalle: descripción + cant + p.unit + (sub)total (números al final)
_RE_LINEA_ITEM = re.compile(
    r"^(.{4,100}?)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)(?:\s+(\d+(?:[.,]\d+)?))?\s*$"
)
# Variante: "... 1,00 unidades 3154720,97 ..."
_RE_LINEA_ITEM_UNIDADES = re.compile(
    r"^(.{4,120}?)\s+(\d+(?:[.,]\d+)?)\s+unidades\s+(\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
# Montos AR: 3.154.720,97 o 3154720,97 (sin miles con punto)
_RE_MONTO_AR = re.compile(
    r"\b(\d{1,3}(?:\.\d{3})*,\d{2}|\d{4,},\d{2})\b"
)

# Factura A/B/C/M o equivalente (NC/ND con letra)
_RE_FACTURA_LETRA = re.compile(
    r"\b(?:FACTURA|NOTA\s+DE\s+CREDITO|NOTA\s+DE\s+CRÉDITO|NOTA\s+DE\s+DEBITO|NOTA\s+DE\s+DÉBITO)\s+([ABCM])\b",
    re.IGNORECASE,
)
# Código tipo comprobante AFIP (1=A, 6=B, 11=C, 51=M en ventas; mismos códigos en recepción)
_RE_CODIGO_TIPO_CBTE = re.compile(
    r"(?:tipo\s+de\s+comprobante|tipo\s+cmp)\s*[:\s]+\s*(\d{1,3})\b",
    re.IGNORECASE,
)
# ARCA / factura electrónica: "COD. 011" (011 → 11 = Factura C) debajo de la letra en caja
_RE_COD_ARCA = re.compile(
    r"(?:\bCOD\.?\s*|\bCód\.?\s*)(\d{1,3})\b",
    re.IGNORECASE,
)
_MAP_CBTE_AFIP_A_LETRA = {1: "FA", 6: "FB", 11: "FC", 51: "FM"}

_RE_RAZON_SOCIAL_LABEL = re.compile(
    r"^\s*(?:raz[oó]n\s+social)\s*:\s*(.*)$",
    re.IGNORECASE,
)
# Líneas que no son el nombre del emisor (p. ej. entre etiqueta y razón)
_SKIP_LINEAS_TRAS_RAZON_LABEL = frozenset(
    {"original", "duplicado", "triplicado", "copia", "copia cliente"}
)


def _descartar_como_razon_social(linea: str) -> bool:
    """Evita usar etiquetas de factura AFIP (fecha, totales, etc.) como razón social."""
    ln = (linea or "").strip()
    if len(ln) < 4:
        return True
    low = ln.lower()
    prefijos = (
        "fecha de emisión",
        "fecha de emision",
        "fecha:",
        "fecha ",
        "vencimiento",
        "cae:",
        "cae ",
        "tipo de comprobante",
        "tipo factura",
        "punto de venta",
        "pto. venta",
        "pto venta",
        "nº comprobante",
        "n° comprobante",
        "comp. nro",
        "nro comprobante",
        "condición de venta",
        "condicion de venta",
        "iva ",
        "subtotal",
        "importe total",
        "total:",
        "total ",
        "total\t",
        "neto gravado",
        "discriminación",
        "discriminacion",
        "teléfono",
        "telefono",
        "domicilio",
        "ingresos brutos",
        "inicio de actividades",
        "página",
        "pagina",
        "original",
        "duplicado",
        "cod.",
        "cód.",
    )
    if any(low.startswith(p) for p in prefijos):
        return True
    # Línea que es solo una fecha
    compact = low.replace(" ", "")
    if _RE_FECHA_SUELTA.fullmatch(compact):
        return True
    # Basura OCR: demasiada puntuación/símbolos y pocos caracteres alfabéticos.
    alpha = sum(1 for c in ln if c.isalpha())
    extra = sum(1 for c in ln if c in "|\\/_=~`^[]{}<>")
    if alpha < 4:
        return True
    if extra >= 3 and extra > (len(ln) * 0.12):
        return True
    tokens = [t for t in re.split(r"\s+", ln) if t]
    if tokens:
        max_tok = max(len(t) for t in tokens)
        short = sum(1 for t in tokens if len(t) <= 2)
        if max_tok < 4:
            return True
        if short >= 4 and short >= int(len(tokens) * 0.6):
            return True
    return False


_SKIP_LINE_PREFIXES = (
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
)


def _normalizar_fecha(d: str, m: str, y: str) -> str:
    yi = int(y)
    if yi < 100:
        yi += 2000
    di = int(d)
    mi = int(m)
    if mi < 1 or mi > 12 or di < 1 or di > 31:
        return ""
    if yi < 2000 or yi > 2100:
        return ""
    return f"{di:02d}/{mi:02d}/{yi}"


def _ocr_digits(s: str) -> str:
    """Normaliza confusiones típicas OCR en campos numéricos."""
    return (
        (s or "")
        .replace("O", "0")
        .replace("o", "0")
        .replace("I", "1")
        .replace("l", "1")
        .replace("Z", "2")
        .replace("z", "2")
        .replace("S", "5")
    )


def _monto_a_texto_plano(s: str) -> str:
    """Devuelve string usable en input decimal (punto como separador)."""
    s = (s or "").strip().replace(" ", "")
    if not s:
        return ""
    s = s.replace("'", ".")
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


def _nro_comprobante_desde_match(m: re.Match[str]) -> str | None:
    g = m.groups()
    if g[0] and g[1]:
        return f"{g[0]}-{g[1]}"
    if g[2] and g[3]:
        return f"{g[2]}-{g[3]}"
    return None


def _cuit_format_11(s: str) -> str:
    if len(s) != 11 or not s.isdigit():
        return s
    return f"{s[:2]}-{s[2:10]}-{s[10]}"


def _fecha_emision_despues_de_periodo(texto: str) -> tuple[str, str, str] | None:
    """
    Tras una línea de período con tres fechas (desde/hasta/vto), la siguiente fecha suelta
    suele ser la fecha de emisión (no el inicio del período facturado).
    """
    lines = [ln.rstrip() for ln in texto.split("\n")]
    triple = re.compile(r"\d{1,2}/\d{1,2}/\d{4}")
    solo = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$")
    for i, ln in enumerate(lines[:120]):
        if len(triple.findall(ln)) >= 3:
            for j in range(i + 1, min(i + 10, len(lines))):
                sm = solo.match(lines[j].strip())
                if sm:
                    return sm.group(1), sm.group(2), sm.group(3)
            return None
    return None


def _importe_total_desde_montos_ar(texto: str) -> str | None:
    """Si 'Importe Total' no trae el importe en la misma línea (pypdf), busca montos AR en el bloque."""
    low = texto.lower()
    idx = low.find("importe total")
    if idx < 0:
        idx = low.find("subtotal")
    segment = texto[idx : idx + 1500] if idx >= 0 else texto[:4000]
    best_f = 0.0
    best_val = None
    for m in _RE_MONTO_AR.finditer(segment):
        val = _monto_a_texto_plano(m.group(1))
        if not val:
            continue
        try:
            f = float(val)
        except ValueError:
            continue
        if f > best_f and f >= 50:
            best_f = f
            best_val = val
    return best_val


def _compactar_espacios_pdf(texto: str) -> str:
    """Une saltos y espacios raros (pypdf a veces parte 'COD.' y '011' o 'Factura' y 'C')."""
    t = (texto or "").replace("\xa0", " ")
    return re.sub(r"[\s\n\r]+", " ", t).strip()


def _dedupe_lineas_misma_factura(lineas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    PDF con varias hojas (ORIGINAL / DUPLICADO / TRIPLICADO) repite el mismo ítem: una sola línea.
    Clave: descripción normalizada + cantidad + precio unitario (como texto plano).
    """
    if len(lineas) <= 1:
        return lineas
    vistos: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for ln in lineas:
        desc = " ".join((ln.get("descripcion") or "").lower().split())[:400]
        c_raw = str(ln.get("cantidad") or "").strip().replace(",", ".")
        p_raw = str(ln.get("precio_unitario") or "").strip().replace(",", ".")
        c = _monto_a_texto_plano(c_raw) if c_raw else "0"
        p = _monto_a_texto_plano(p_raw) if p_raw else "0"
        clave = (desc, c or "0", p or "0")
        if clave in vistos:
            continue
        vistos.add(clave)
        out.append(ln)
    return out


def _tipo_desde_letra_sola_cerca_factura(texto: str) -> str | None:
    """
    Layout ARCA: letra A/B/C en línea propia cerca de la palabra FACTURA (sin 'Factura C' en una línea).
    """
    lines = [ln.rstrip() for ln in texto.split("\n")]
    for i, ln in enumerate(lines[:100]):
        if not re.search(r"\bFACTURA\b", ln, re.IGNORECASE):
            continue
        for j in range(max(0, i - 6), min(len(lines), i + 10)):
            s = lines[j].strip()
            if re.fullmatch(r"([ABC])", s):
                return {"A": "FA", "B": "FB", "C": "FC"}.get(s)
    return None


def _tipo_factura_desde_texto(texto: str) -> str | None:
    """Mapea letra AFIP o código numérico a FA/FB/FC/FM (AdministraNET)."""
    compact = _compactar_espacios_pdf(texto)
    # Primero texto multilínea, luego compacto (une "Factura" + "C", "COD" + "011")
    for fuente in (texto, compact):
        m = _RE_FACTURA_LETRA.search(fuente)
        if m:
            letra = m.group(1).upper()
            hit = {"A": "FA", "B": "FB", "C": "FC", "M": "FM"}.get(letra)
            if hit:
                return hit
    # COD. 011 / Cód. 006 (ARCA): en compact suele matchear mejor
    for fuente in (compact, texto):
        for m2 in _RE_COD_ARCA.finditer(fuente):
            try:
                cod = int(m2.group(1))
            except ValueError:
                continue
            if cod in _MAP_CBTE_AFIP_A_LETRA:
                return _MAP_CBTE_AFIP_A_LETRA[cod]
    for fuente in (compact, texto):
        for m2 in _RE_CODIGO_TIPO_CBTE.finditer(fuente):
            try:
                cod = int(m2.group(1))
            except ValueError:
                continue
            if cod in _MAP_CBTE_AFIP_A_LETRA:
                return _MAP_CBTE_AFIP_A_LETRA[cod]
    return _tipo_desde_letra_sola_cerca_factura(texto)


def _razon_social_emisor_afip(texto: str) -> str | None:
    """
    Razón social del emisor: etiqueta 'Razón Social:' con valor en la misma línea
    o en la siguiente (layout AFIP frecuente en PDF). Ignora el bloque receptor
    (p. ej. línea con 'Apellido y Nombre / Razón Social').
    """
    lines = [ln.rstrip() for ln in texto.split("\n")]
    for i, ln in enumerate(lines):
        if re.search(r"apellido\s+y\s+nombre", ln, re.IGNORECASE):
            continue
        m = _RE_RAZON_SOCIAL_LABEL.match(ln)
        if not m:
            continue
        val = (m.group(1) or "").strip()
        if len(val) > 3 and not _descartar_como_razon_social(val):
            return val[:200]
        for j in range(i + 1, min(i + 8, len(lines))):
            cand = lines[j].strip()
            if not cand:
                continue
            if re.search(r"apellido\s+y\s+nombre", cand, re.IGNORECASE):
                break
            cl = cand.lower()
            if cl in _SKIP_LINEAS_TRAS_RAZON_LABEL:
                continue
            digits_only = re.sub(r"\D", "", cand)
            if len(digits_only) == 11 and digits_only.isdigit():
                continue
            if _RE_CUIT.search(cand) or _RE_CUIT_11_ETIQUETA.search(cand):
                continue
            if len(cand) > 3 and not _descartar_como_razon_social(cand):
                return cand[:200]
    return None


def _cuit_proveedor(texto: str, lineas_raw: list[str]) -> str | None:
    m = _RE_CUIT.search(texto)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    for ln in lineas_raw[:45]:
        s = ln.strip()
        if re.fullmatch(r"\d{11}", s):
            return _cuit_format_11(s)
    m2 = _RE_CUIT_11_ETIQUETA.search(texto)
    if m2:
        return _cuit_format_11(m2.group(1))
    return None


def parsear_texto_factura(texto: str) -> tuple[dict[str, Any], list[dict[str, Any]], float]:
    """
    Devuelve (campos_cabecera, lineas_sugeridas, confianza aproximada 0..1).
    """
    texto = (texto or "").replace("\r", "\n")
    if not texto.strip():
        return {}, [], 0.0

    cab: dict[str, Any] = {}
    lineas: list[dict[str, Any]] = []
    puntuacion = 0.25
    lineas_raw = [ln.strip() for ln in texto.split("\n") if ln.strip()]

    # Número de comprobante (punto venta + número)
    for m in _RE_NRO_COMP.finditer(texto):
        nro = _nro_comprobante_desde_match(m)
        if nro:
            cab["nro_comprobante_texto"] = nro
            puntuacion += 0.18
            break
    if "nro_comprobante_texto" not in cab:
        m_pv = _RE_COMP_NRO_PV.search(texto)
        if m_pv:
            cab["nro_comprobante_texto"] = f"{m_pv.group(1)}-{m_pv.group(2)}"
            puntuacion += 0.16

    # Fecha: preferir emisión tras línea de período (tres fechas); si no, etiquetada / suelta
    fecha_trip = _fecha_emision_despues_de_periodo(texto)
    if fecha_trip:
        d, mo, y = fecha_trip
        cab["fecha_comprobante_texto"] = _normalizar_fecha(d, mo, y)
        puntuacion += 0.15
    else:
        fm = _RE_FECHA.search(texto)
        if not fm:
            fm = _RE_FECHA_SUELTA.search(texto)
        if fm:
            f_norm = _normalizar_fecha(
                fm.group(1), fm.group(2), fm.group(3)
            )
            if f_norm:
                cab["fecha_comprobante_texto"] = f_norm
                puntuacion += 0.15
        else:
            # OCR ruidoso: variantes como 9zoz/20/92 (YYYY/MM/DD con letras parecidas).
            tx_num = _ocr_digits(texto)
            ym = _RE_FECHA_YMD_SUELTA.search(tx_num)
            if ym:
                f_norm = _normalizar_fecha(
                    ym.group(3), ym.group(2), ym.group(1)
                )
                if f_norm:
                    cab["fecha_comprobante_texto"] = f_norm
                    puntuacion += 0.12

    cuit_str = _cuit_proveedor(texto, lineas_raw)
    if cuit_str:
        cab["proveedor_cuit_texto"] = cuit_str
        puntuacion += 0.15

    tf = _tipo_factura_desde_texto(texto)
    if tf:
        cab["tipo_factura"] = tf
        puntuacion += 0.06

    rs_emisor = _razon_social_emisor_afip(texto)
    if rs_emisor:
        cab["proveedor_texto"] = rs_emisor
        puntuacion += 0.12

    # Razón social por etiqueta (Proveedor:, Vendedor:, etc.) si no hubo bloque AFIP
    if "proveedor_texto" not in cab:
        for linea in texto.split("\n"):
            linea = linea.strip()
            pm = _RE_PROV_LABEL.match(linea)
            if pm:
                val = pm.group(1).strip()
                if len(val) > 3 and not _descartar_como_razon_social(val):
                    cab["proveedor_texto"] = val[:200]
                    puntuacion += 0.12
                    break

    if "proveedor_texto" not in cab:
        # Primera línea sustancial antes del primer CUIT o en cabecera
        cuit_idx = None
        for i, ln in enumerate(lineas_raw):
            if _RE_CUIT.search(ln):
                cuit_idx = i
                break
        candidato = None
        if cuit_idx is not None and cuit_idx > 0:
            candidato = lineas_raw[cuit_idx - 1]
        elif lineas_raw:
            candidato = lineas_raw[0]
        if candidato and len(candidato) > 8 and not _RE_CUIT.match(candidato):
            if not any(candidato.lower().startswith(p) for p in _SKIP_LINE_PREFIXES):
                if not _descartar_como_razon_social(candidato):
                    cab["proveedor_texto"] = candidato[:200]
                    puntuacion += 0.08

    # Segundo intento: línea con "S.A." / "S.R.L." / "S.A.I.C." cerca del encabezado
    if "proveedor_texto" not in cab:
        for linea in texto.split("\n")[:40]:
            linea = linea.strip()
            if len(linea) < 6 or _descartar_como_razon_social(linea):
                continue
            if (
                _RE_CUIT.search(linea)
                or _RE_NRO_COMP.search(linea)
                or _RE_COMP_NRO_PV.search(linea)
            ):
                continue
            low = linea.lower()
            if any(
                x in low
                for x in (
                    " s.a.",
                    " s.r.l.",
                    " s.a.i.c.",
                    " s.h.",
                    " s.c.s.",
                    " s.u.i.p.",
                    " sociedad",
                )
            ):
                cab["proveedor_texto"] = linea[:200]
                puntuacion += 0.06
                break

    tm = _RE_TOTAL.search(texto)
    if not tm:
        for linea in texto.split("\n"):
            linea = linea.strip()
            m2 = _RE_TOTAL_SUELTO.search(linea)
            if m2:
                tm = m2
                break
    if tm:
        monto = _monto_a_texto_plano(tm.group(1))
        if monto:
            cab["importe_total_texto"] = monto
            puntuacion += 0.12
    if not cab.get("importe_total_texto"):
        fb = _importe_total_desde_montos_ar(texto)
        if fb:
            cab["importe_total_texto"] = fb
            puntuacion += 0.1

    # Ítems: líneas con patrón descripción + 2–3 números
    for linea in texto.split("\n"):
        linea = linea.strip()
        if len(linea) < 12:
            continue
        low = linea.lower()
        if any(low.startswith(p) for p in _SKIP_LINE_PREFIXES):
            continue
        if _RE_NRO_COMP.search(linea) or _RE_CUIT.search(linea) or _RE_COMP_NRO_PV.search(
            linea
        ):
            continue
        imu = _RE_LINEA_ITEM_UNIDADES.match(linea)
        if imu:
            desc = imu.group(1).strip()
            if len(desc) >= 3 and "código producto" not in desc.lower():
                cant = _monto_a_texto_plano(imu.group(2))
                precio = _monto_a_texto_plano(imu.group(3))
                lineas.append(
                    {
                        "descripcion": desc[:500],
                        "cantidad": cant or "1",
                        "precio_unitario": precio or "0",
                    }
                )
            continue
        im = _RE_LINEA_ITEM.match(linea)
        if not im:
            continue
        desc = im.group(1).strip()
        if len(desc) < 3:
            continue
        nums = [im.group(2), im.group(3), im.group(4)]
        nums = [n for n in nums if n]
        if len(nums) < 2:
            continue
        cant = _monto_a_texto_plano(nums[0])
        precio = _monto_a_texto_plano(nums[1] if len(nums) >= 2 else "0")
        lineas.append(
            {
                "descripcion": desc[:500],
                "cantidad": cant or "1",
                "precio_unitario": precio or "0",
            }
        )

    lineas_antes = len(lineas)
    lineas = _dedupe_lineas_misma_factura(lineas)
    if lineas_antes > len(lineas):
        cab["lineas_repetidas_omitidas"] = lineas_antes - len(lineas)

    extra_lineas = min(0.2, 0.04 * len(lineas))
    puntuacion += extra_lineas
    conf = min(0.95, puntuacion)
    return cab, lineas, round(conf, 3)


def analizar_archivo_factura(
    ruta_archivo: str,
    mime_type: str,
    *,
    tesseract_lang: str = "spa+eng",
    tesseract_cmd: str | None = None,
    tesseract_enabled: bool = True,
    engine_mode: str = "legacy",
) -> dict[str, Any]:
    """
    - ``application/pdf``: texto embebido con pypdf + heurísticas.
    - ``image/jpeg`` / ``image/png``: Tesseract + mismas heurísticas.
    """
    mt = (mime_type or "").lower().split(";")[0].strip()

    if mt in MIME_IMAGEN_OCR:
        if not tesseract_enabled:
            return {
                "texto_plano": "",
                "confianza_global": 0.0,
                "campos_cabecera": {},
                "lineas_sugeridas": [],
                "raw": {
                    "motor": "heuristic",
                    "mime_type": mime_type,
                    "extraccion": "deshabilitada",
                    "advertencia": (
                        "OCR Tesseract deshabilitado (FACTURA_COMPRA_OCR_TESSERACT_ENABLED=false)."
                    ),
                },
            }
        texto, document_engine_v1 = _procesar_imagen_ocr_por_modo(
            ruta_archivo,
            lang=tesseract_lang or "spa+eng",
            tesseract_cmd=tesseract_cmd,
            engine_mode=engine_mode,
        )
        cab, lineas, conf = parsear_texto_factura(texto)
        if texto.strip():
            conf = min(conf, 0.88)
        else:
            conf = 0.0
        raw: dict[str, Any] = {
            "motor": "heuristic",
            "mime_type": mime_type,
            "extraccion": "tesseract",
            "idioma_ocr": tesseract_lang,
            "caracteres_texto": len(texto),
        }
        ocr_s = (
            document_engine_v1.get("ocr_structured")
            if document_engine_v1
            else None
        )
        em_norm = (engine_mode or "legacy").strip().lower()
        if em_norm not in ("legacy", "preprocess_only", "structured_ocr"):
            em_norm = "legacy"
        _enriquecer_raw_document_engine_stage2(
            raw,
            texto,
            cab,
            lineas,
            ocr_structured=ocr_s,
            document_engine_v1_base=document_engine_v1,
            engine_mode=em_norm,
        )
        if not texto.strip():
            raw["advertencia"] = (
                "Tesseract no detectó texto (imagen borrosa, reflejos o sin texto legible)."
            )
        elif not cab and not lineas:
            raw["advertencia"] = (
                "Texto reconocido pero no se identificaron campos típicos de factura; revisá manualmente."
            )
        return {
            "texto_plano": texto[:50000],
            "confianza_global": conf,
            "campos_cabecera": cab,
            "lineas_sugeridas": lineas[:200],
            "raw": raw,
        }

    if mt != "application/pdf":
        return {
            "texto_plano": "",
            "confianza_global": 0.0,
            "campos_cabecera": {},
            "lineas_sugeridas": [],
            "raw": {
                "motor": "heuristic",
                "mime_type": mime_type,
                "advertencia": "Tipo de archivo no soportado para análisis local.",
            },
        }

    try:
        texto = extraer_texto_pdf(ruta_archivo)
    except Exception as exc:  # PdfReadError, etc.
        raise ValueError(str(exc)) from exc

    cab, lineas, conf = parsear_texto_factura(texto)
    raw = {
        "motor": "heuristic",
        "mime_type": mime_type,
        "extraccion": "pypdf",
        "caracteres_texto": len(texto),
    }
    _enriquecer_raw_document_engine_stage2(
        raw,
        texto,
        cab,
        lineas,
        ocr_structured=None,
        document_engine_v1_base=None,
        engine_mode=None,
    )
    if not texto.strip():
        raw["advertencia"] = (
            "No se extrajo texto del PDF (posible documento escaneado sin capa de texto). "
            "Podés subir una foto con la cámara para OCR con Tesseract."
        )
    elif not cab and not lineas:
        raw["advertencia"] = (
            "Texto extraído pero no se reconocieron campos típicos de factura; revisá manualmente."
        )

    return {
        "texto_plano": texto[:50000],
        "confianza_global": conf,
        "campos_cabecera": cab,
        "lineas_sugeridas": lineas[:200],
        "raw": raw,
    }
