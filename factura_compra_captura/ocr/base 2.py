from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class OcrAdapterError(Exception):
    """Error recuperable o no del motor OCR."""

    def __init__(self, codigo: str, mensaje: str):
        self.codigo = codigo
        super().__init__(mensaje)


@dataclass
class OcrExtractResult:
    """Salida normalizada del adapter (lista para mapear a cabecera/líneas en Fase 3)."""

    texto_plano: str = ""
    confianza_global: float = 0.0
    campos_cabecera: dict[str, Any] = field(default_factory=dict)
    lineas_sugeridas: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class OcrAdapter(Protocol):
    def extract(self, *, ruta_archivo: str, mime_type: str) -> OcrExtractResult:
        """Lee archivo ya persistido en disco/storage."""
