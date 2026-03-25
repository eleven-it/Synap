"""
OCR estructurado vía salida TSV de Tesseract (pytesseract image_to_data).

Resume palabras/líneas y confianza sin almacenar el TSV completo en BD.
"""

from __future__ import annotations

from typing import Any

from PIL import Image

# Límite de palabras detalladas en JSON (evita explosión en documentos grandes)
_MAX_PALABRAS_DETALLE = 500
_TESSERACT_CONFIG_DEFAULT = "--oem 1 --psm 3"


def construir_resumen_desde_dict_tsv(data: dict[str, Any]) -> dict[str, Any]:
    """
    A partir del dict devuelto por pytesseract.image_to_data(..., output_type=Output.DICT),
    construye un resumen con líneas agrupadas y estadísticas.
    """
    n = len(data.get("text", []))
    if n == 0:
        return {
            "word_count": 0,
            "pages": [],
            "mean_confidence": None,
            "palabras_muestra": [],
        }

    confidences: list[float] = []
    palabras_muestra: list[dict[str, Any]] = []

    # Agrupa por (page_num, block_num, par_num, line_num)
    lineas_map: dict[tuple[int, int, int, int], list[dict[str, Any]]] = {}

    for i in range(n):
        txt = (data["text"][i] or "").strip()
        try:
            conf = int(data["conf"][i])
        except (TypeError, ValueError, KeyError):
            conf = -1
        if conf >= 0:
            confidences.append(float(conf))

        if txt:
            page = int(data.get("page_num", [0] * n)[i] or 0)
            block = int(data.get("block_num", [0] * n)[i] or 0)
            par = int(data.get("par_num", [0] * n)[i] or 0)
            line = int(data.get("line_num", [0] * n)[i] or 0)

            left = int(data["left"][i])
            top = int(data["top"][i])
            w = int(data["width"][i])
            h = int(data["height"][i])

            witem = {
                "text": txt[:200],
                "conf": conf,
                "page": page,
                "left": left,
                "top": top,
                "width": w,
                "height": h,
            }
            line_key = (page, block, par, line)
            lineas_map.setdefault(line_key, []).append(witem)

            if len(palabras_muestra) < _MAX_PALABRAS_DETALLE:
                palabras_muestra.append(witem)

    pages: dict[int, list[dict[str, Any]]] = {}
    for (page, block, par, line), words in lineas_map.items():
        texto_linea = " ".join(w["text"] for w in words).strip()
        if not texto_linea:
            continue
        confs_linea = [w["conf"] for w in words if w["conf"] >= 0]
        mean_l = (
            sum(confs_linea) / len(confs_linea) if confs_linea else None
        )
        entry = {
            "line_id": f"{block}-{par}-{line}",
            "text": texto_linea[:500],
            "mean_confidence": round(mean_l, 2) if mean_l is not None else None,
            "word_count": len(words),
        }
        pages.setdefault(page, []).append(entry)

    pages_list = []
    for p in sorted(pages.keys()):
        lines = pages[p]
        lines_sorted = sorted(lines, key=lambda x: x["line_id"])
        pages_list.append(
            {
                "page_num": p,
                "lines": lines_sorted,
                "line_count": len(lines_sorted),
            }
        )

    mean_conf = None
    if confidences:
        mean_conf = round(sum(confidences) / len(confidences), 2)

    n_words = sum(1 for i in range(n) if (data.get("text", [""] * n)[i] or "").strip())

    return {
        "word_count": n_words,
        "pages": pages_list,
        "page_count": len(pages_list),
        "mean_confidence": mean_conf,
        "palabras_muestra": palabras_muestra,
    }


def construir_ocr_structured_desde_imagen(
    pil_image: Image.Image,
    *,
    lang: str = "spa+eng",
    tesseract_cmd: str | None = None,
    config: str = _TESSERACT_CONFIG_DEFAULT,
) -> dict[str, Any]:
    """Ejecuta image_to_data (TSV interno) y devuelve resumen JSON-serializable."""
    import pytesseract
    from pytesseract import Output

    prev_cmd = pytesseract.pytesseract.tesseract_cmd
    try:
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        data = pytesseract.image_to_data(
            pil_image,
            lang=lang,
            config=config,
            output_type=Output.DICT,
        )
        resumen = construir_resumen_desde_dict_tsv(data)
        resumen["fuente"] = "tesseract_tsv"
        return resumen
    finally:
        pytesseract.pytesseract.tesseract_cmd = prev_cmd
