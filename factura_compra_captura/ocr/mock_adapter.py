from __future__ import annotations

from django.conf import settings

from factura_compra_captura.ocr.base import OcrAdapterError, OcrExtractResult


class MockOcrAdapter:
    """
    OCR simulado para CI y entornos sin D-01.
    Configuración opcional vía settings (tests):
    FACTURA_COMPRA_OCR_MOCK_FAIL = True -> siempre falla.
    """

    def extract(self, *, ruta_archivo: str, mime_type: str) -> OcrExtractResult:
        if getattr(settings, "FACTURA_COMPRA_OCR_MOCK_FAIL", False):
            raise OcrAdapterError(
                "MOCK_FORZADO",
                "Fallo simulado del motor OCR (test o configuración).",
            )
        return OcrExtractResult(
            texto_plano="FACTURA MOCK — proveedor demo — total 1000.00",
            confianza_global=0.92,
            campos_cabecera={
                "proveedor_texto": "Proveedor Mock S.A.",
                "nro_comprobante_texto": "0001-00001234",
                "fecha_comprobante_texto": "01/01/2026",
            },
            lineas_sugeridas=[
                {
                    "descripcion": "Ítem mock",
                    "cantidad": "1",
                    "precio_unitario": "1000.00",
                }
            ],
            raw={"motor": "mock", "mime_type": mime_type},
        )
