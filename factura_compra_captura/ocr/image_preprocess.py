"""
Preprocesado de imágenes para OCR (Stage 1 — OpenCV opcional).

Si OpenCV falla o no está instalado, se debe usar la imagen original (fallback).
"""

from __future__ import annotations

from typing import Any

from PIL import Image


def preprocesar_imagen_factura(pil_rgb: Image.Image) -> tuple[Image.Image, dict[str, Any]]:
    """
    Mejora contraste y reduce ruido antes de Tesseract.

    Returns:
        (imagen_para_ocr, metadata): si falla cualquier paso, devuelve la entrada
        sin cambios y metadata con ``fallback=True``.
    """
    meta: dict[str, Any] = {
        "applied": False,
        "steps": [],
        "fallback": True,
        "motivo": None,
    }
    try:
        import cv2  # type: ignore[import-untyped]
        import numpy as np
    except ImportError as e:
        meta["motivo"] = f"opencv_no_disponible:{e}"
        return pil_rgb, meta

    try:
        arr = np.asarray(pil_rgb)
        if arr.ndim == 2:
            gray = arr
            meta["steps"].append("entrada_escala_grises")
        else:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            meta["steps"].append("rgb_a_gris")

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        meta["steps"].append("clahe")

        denoised = cv2.fastNlMeansDenoising(
            enhanced, h=10, templateWindowSize=7, searchWindowSize=21
        )
        meta["steps"].append("denoise")

        rgb = cv2.cvtColor(denoised, cv2.COLOR_GRAY2RGB)
        out = Image.fromarray(rgb)
        meta["applied"] = True
        meta["fallback"] = False
        return out, meta
    except Exception as e:
        meta["motivo"] = str(e)[:500]
        return pil_rgb, meta
