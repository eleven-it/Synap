from __future__ import annotations

from typing import Any

import requests
from django.conf import settings

from factura_compra_captura.ocr.base import OcrAdapterError, OcrExtractResult


def _as_dict(val: Any) -> dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _as_list(val: Any) -> list[dict[str, Any]]:
    if not isinstance(val, list):
        return []
    out: list[dict[str, Any]] = []
    for x in val:
        if isinstance(x, dict):
            out.append(x)
    return out


class HttpOcrAdapter:
    """
    Adapter OCR HTTP.

    Espera endpoint que reciba multipart 'archivo' y devuelva JSON.
    JSON soportado (flexible):
      - texto_plano | text | raw_text
      - confianza_global | confidence
      - campos_cabecera | header | fields
      - lineas_sugeridas | lines | items
    """

    def __init__(self):
        self.url = str(
            getattr(settings, "FACTURA_COMPRA_OCR_HTTP_URL", "") or ""
        ).strip()
        self.timeout = int(getattr(settings, "FACTURA_COMPRA_OCR_HTTP_TIMEOUT", 30))
        self.verify_ssl = bool(
            getattr(settings, "FACTURA_COMPRA_OCR_HTTP_VERIFY_SSL", True)
        )
        self.token = str(
            getattr(settings, "FACTURA_COMPRA_OCR_HTTP_BEARER_TOKEN", "") or ""
        ).strip()

    def extract(self, *, ruta_archivo: str, mime_type: str) -> OcrExtractResult:
        if not self.url:
            raise OcrAdapterError(
                "OCR_HTTP_URL_REQUERIDA",
                "FACTURA_COMPRA_OCR_HTTP_URL no está configurada.",
            )
        headers: dict[str, str] = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with open(ruta_archivo, "rb") as fh:
                r = requests.post(
                    self.url,
                    files={"archivo": ("documento", fh, mime_type or "application/octet-stream")},
                    data={"mime_type": mime_type or ""},
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
        except requests.RequestException as e:
            raise OcrAdapterError("OCR_HTTP_NETWORK_ERROR", str(e)) from e

        if r.status_code >= 400:
            detalle = (r.text or "").strip()
            if len(detalle) > 500:
                detalle = detalle[:500] + "..."
            raise OcrAdapterError(
                "OCR_HTTP_STATUS_ERROR",
                f"OCR HTTP devolvió {r.status_code}. {detalle}",
            )

        try:
            payload = r.json()
        except ValueError as e:
            raise OcrAdapterError(
                "OCR_HTTP_JSON_INVALIDO",
                "OCR HTTP devolvió una respuesta no JSON.",
            ) from e

        texto = str(
            payload.get("texto_plano")
            or payload.get("text")
            or payload.get("raw_text")
            or ""
        ).strip()
        confianza = payload.get("confianza_global", payload.get("confidence", 0.0))
        try:
            confianza_f = float(confianza or 0.0)
        except (ValueError, TypeError):
            confianza_f = 0.0
        campos = _as_dict(
            payload.get("campos_cabecera")
            or payload.get("header")
            or payload.get("fields")
        )
        lineas = _as_list(
            payload.get("lineas_sugeridas")
            or payload.get("lines")
            or payload.get("items")
        )
        return OcrExtractResult(
            texto_plano=texto,
            confianza_global=confianza_f,
            campos_cabecera=campos,
            lineas_sugeridas=lineas,
            raw={"motor": "http", "response": payload},
        )
