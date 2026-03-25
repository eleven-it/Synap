from __future__ import annotations

from django.conf import settings

from factura_compra_captura.ocr.base import OcrAdapter
from factura_compra_captura.ocr.mock_adapter import MockOcrAdapter


def get_ocr_adapter() -> OcrAdapter:
    """
    FACTURA_COMPRA_OCR_ADAPTER:
      - mock (default): MockOcrAdapter
      - http: reservado proveedor HTTP real (Fase posterior; hoy levanta si se usa sin implementar)
    """
    nombre = getattr(settings, "FACTURA_COMPRA_OCR_ADAPTER", "mock").lower().strip()
    if nombre == "mock":
        return MockOcrAdapter()
    if nombre == "http":
        raise NotImplementedError(
            "Adapter OCR HTTP no implementado; usar mock o definir integración (D-01)."
        )
    raise ValueError(f"FACTURA_COMPRA_OCR_ADAPTER desconocido: {nombre!r}")
