"""
Logs estructurados (JSON en una línea) para observabilidad Fase 5.
"""

from __future__ import annotations

import json
import logging
from typing import Any


def log_factura_compra_event(
    logger: logging.Logger,
    evento: str,
    *,
    expediente_id: str | None = None,
    codigo_movimiento: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload = {
        "componente": "factura_compra_posting",
        "evento": evento,
        "expediente_id": expediente_id,
        "codigo_movimiento": codigo_movimiento,
    }
    if extra:
        payload.update(extra)
    logger.info(json.dumps(payload, default=str, ensure_ascii=False))
