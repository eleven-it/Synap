from __future__ import annotations

from django.conf import settings

from factura_compra_captura.ocr.base import OcrAdapterError, OcrExtractResult
from factura_compra_captura.ocr.heuristic_pdf import (
    TesseractNotAvailableError,
    analizar_archivo_factura,
)


class HeuristicOcrAdapter:
    """
    PDF: texto embebido (pypdf) + heurísticas.
    JPEG/PNG: Tesseract en servidor + mismas heurísticas (fotos desde PWA / cámara).
    """

    def extract(self, *, ruta_archivo: str, mime_type: str) -> OcrExtractResult:
        lang = getattr(settings, "FACTURA_COMPRA_OCR_TESSERACT_LANG", "spa+eng") or "spa+eng"
        cmd = (getattr(settings, "FACTURA_COMPRA_OCR_TESSERACT_CMD", "") or "").strip() or None
        tess_on = getattr(settings, "FACTURA_COMPRA_OCR_TESSERACT_ENABLED", True)
        engine_mode = getattr(
            settings, "FACTURA_COMPRA_OCR_ENGINE_MODE", "legacy"
        ) or "legacy"
        try:
            data = analizar_archivo_factura(
                ruta_archivo,
                mime_type,
                tesseract_lang=lang,
                tesseract_cmd=cmd,
                tesseract_enabled=tess_on,
                engine_mode=str(engine_mode).strip().lower(),
            )
        except TesseractNotAvailableError as e:
            raise OcrAdapterError("OCR_TESSERACT_NO_INSTALADO", str(e)) from e
        except ValueError as e:
            msg = str(e)
            if msg == "OCR_IMAGEN_NO_VALIDA":
                raise OcrAdapterError(
                    "OCR_IMAGEN_NO_VALIDA",
                    "No se pudo leer la imagen.",
                ) from e
            raise OcrAdapterError(
                "OCR_PDF_ILEGIBLE",
                f"No se pudo leer el PDF: {e}",
            ) from e
        return OcrExtractResult(
            texto_plano=data["texto_plano"],
            confianza_global=float(data["confianza_global"]),
            campos_cabecera=data["campos_cabecera"],
            lineas_sugeridas=data["lineas_sugeridas"],
            raw=data["raw"],
        )
