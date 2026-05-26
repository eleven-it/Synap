from __future__ import annotations

import logging

from django.conf import settings

from factura_compra_captura.ocr.base import OcrAdapter
from factura_compra_captura.ocr.heuristic_adapter import HeuristicOcrAdapter
from factura_compra_captura.ocr.http_adapter import HttpOcrAdapter

logger = logging.getLogger(__name__)


def get_ocr_adapter() -> OcrAdapter:
    """
    FACTURA_COMPRA_OCR_ADAPTER:
      - heuristic (default): texto PDF local + patrones ES/AR
      - http: cliente HTTP contra servicio OCR externo
    """
    nombre = getattr(settings, "FACTURA_COMPRA_OCR_ADAPTER", "heuristic").lower().strip()
    if nombre == "mock":
        logger.warning(
            "FACTURA_COMPRA_OCR_ADAPTER=mock ya no existe; se usa heuristic. "
            "Actualizá .env a FACTURA_COMPRA_OCR_ADAPTER=heuristic."
        )
        nombre = "heuristic"
    if nombre == "heuristic":
        return HeuristicOcrAdapter()
    if nombre == "http":
        return HttpOcrAdapter()
    raise ValueError(f"FACTURA_COMPRA_OCR_ADAPTER desconocido: {nombre!r}")
