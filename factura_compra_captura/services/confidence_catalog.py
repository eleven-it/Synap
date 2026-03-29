"""
Catálogo formal de bandas y pesos para confianza de campos (Stage 2.5).

Los valores numéricos se alinean con el comportamiento actual de ``header_parser``;
cualquier cambio futuro debe actualizar este catálogo y la documentación.
"""

from __future__ import annotations

from typing import Literal

# Versión del esquema de evidencia embebido en cada campo de cabecera
EVIDENCIA_SCHEMA_VERSION = 1

# Bandas interpretativas (solo documentación / reglas; el valor sigue siendo float 0..1)
BandaConfianza = Literal["alta", "media", "baja"]


def banda_desde_valor(confidence: float) -> BandaConfianza:
    if confidence >= 0.75:
        return "alta"
    if confidence >= 0.5:
        return "media"
    return "baja"


# --- Confianza por tipo de extracción (cabecera) ---
# structured: coincidencia en línea/token OCR estructurado
CONF_STRUCTURED_LINEA = 0.78
CONF_STRUCTURED_TOKEN = 0.82
CONF_STRUCTURED_TIPO_LINEA = 0.85
CONF_STRUCTURED_TOTAL_LINEA = 0.8

# heuristic: valor tomado del dict devuelto por parsear_texto_factura (legacy)
CONF_HEURISTIC_PROVEEDOR = 0.62
CONF_HEURISTIC_TIPO = 0.58
CONF_HEURISTIC_PV_NRO = 0.6
CONF_HEURISTIC_FECHA = 0.6
CONF_HEURISTIC_TOTAL = 0.58

# raw: solo regex sobre texto plano (sin capa OCR posicional)
CONF_RAW_TIPO = 0.72
CONF_RAW_COD_AFIP = 0.55
CONF_RAW_PV_NRO = 0.68
CONF_RAW_COMP_PV = 0.64
CONF_RAW_FECHA = 0.65
CONF_RAW_TOTAL = 0.66

# fallback débil (CUIT como nombre de proveedor)
CONF_WEAK_CUIT_STRUCTURED = 0.35
CONF_WEAK_CUIT_RAW = 0.32

# Ítems de línea (Stage 3)
CONF_LINE_ITEM_STRUCTURED = 0.72
CONF_LINE_ITEM_HEURISTIC_FALLBACK = 0.55
LINE_ITEMS_QUALITY_SCHEMA_VERSION = 1

# Pesos para document_score (suma = 1.0)
PESO_CLASIFICACION_DOC = 0.15
PESO_PROMEDIO_CAMPOS = 0.55
PESO_COMPLETITUD = 0.2
PESO_CONSISTENCIA = 0.1

# Campos considerados críticos para resumen de faltantes
CAMPOS_CRITICOS_CABECERA: tuple[str, ...] = (
    "proveedor",
    "tipo_factura",
    "punto_venta",
    "numero",
    "fecha",
    "total",
)
