"""
Estructura estándar de evidencia por campo (Stage 2.5).

Todas las evidencias comparten el mismo contrato JSON para consumo interno y trazabilidad.
"""

from __future__ import annotations

from typing import Any

from factura_compra_captura.services.confidence_catalog import EVIDENCIA_SCHEMA_VERSION


def evidencia_estandar(
    *,
    page: int | None = None,
    bbox: dict[str, int] | None = None,
    raw_text: str = "",
) -> dict[str, Any]:
    """
    ``bbox``: rectángulo en coordenadas de imagen Tesseract (left, top, width, height)
    o ``None`` si la evidencia proviene de línea OCR sin caja única o de texto plano.
    """
    b: dict[str, Any] | None
    if bbox is None:
        b = None
    else:
        b = {
            "left": int(bbox.get("left", 0)),
            "top": int(bbox.get("top", 0)),
            "width": int(bbox.get("width", 0)),
            "height": int(bbox.get("height", 0)),
        }
    return {
        "schema_version": EVIDENCIA_SCHEMA_VERSION,
        "page": page,
        "bbox": b,
        "raw_text": (raw_text or "")[:800],
    }
