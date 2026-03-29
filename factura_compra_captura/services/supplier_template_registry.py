"""
Registro declarativo de plantillas por proveedor (Stage 5).

Las plantillas son reglas en código; evolución futura puede cargar desde BD.
"""

from __future__ import annotations

from typing import Any

# Plantilla sintética: motor genérico sin reglas propias
SUPPLIER_TEMPLATES: dict[str, dict[str, Any]] = {
    "generic": {
        "label": "Motor genérico",
        "priority": 0,
    },
    # Usada en tests (mismo CUIT que test_heuristic_pdf)
    "demo_cuit_30701855008": {
        "label": "Demo proveedor tests",
        "priority": 100,
        "match_cuit_digits": "30701855008",
        "cae_regex": r"CAE\s*N[°º]?\s*:?\s*(\d+)",
        # Filas tipo detalle (misma familia que el parser heurístico)
        "extra_item_line_regex": (
            r"(?mi)^(.{4,100}?)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)"
            r"(?:\s+(\d+(?:[.,]\d+)?))?\s*$"
        ),
    },
}
