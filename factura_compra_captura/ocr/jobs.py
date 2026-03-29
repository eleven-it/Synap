"""
Programación del pipeline OCR tras persistir DocumentoFuente.

- FACTURA_COMPRA_OCR_DEFER=False (default): ejecuta OCR en línea en el mismo proceso
  tras el `transaction.atomic` del servicio (compatible con TestCase; respuesta API
  incluye estado ya procesado si el motor es rápido).

- FACTURA_COMPRA_OCR_DEFER=True: tras `transaction.on_commit`, lanza hilo daemon
  (sin Celery en el proyecto principal; ver D-08). Requiere commit real de la transacción.

- FACTURA_COMPRA_OCR_SYNC=True: igual que defer=False (alias explícito para forzar inline).

Si en el futuro se activa Celery, sustituir _spawn_async por shared_task.delay.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from django.conf import settings
from django.db import close_old_connections, transaction

from factura_compra_captura.ocr.pipeline import ejecutar_pipeline_ocr

logger = logging.getLogger(__name__)


def _spawn_async(target: Callable[[], None]) -> None:
    t = threading.Thread(target=target, daemon=True)
    t.start()


def _ejecutar_con_db_limpia(documento_fuente_id: int) -> None:
    close_old_connections()
    try:
        ejecutar_pipeline_ocr(documento_fuente_id)
    except Exception:
        logger.exception("Fallo worker OCR documento=%s", documento_fuente_id)
    finally:
        close_old_connections()


def programar_ocr_documento(documento_fuente_id: int) -> None:
    """
    Encola o ejecuta OCR. Idempotente por documento: pipeline ignora si ya completado.
    """
    if getattr(settings, "FACTURA_COMPRA_OCR_SYNC", False):
        ejecutar_pipeline_ocr(documento_fuente_id)
        return
    if not getattr(settings, "FACTURA_COMPRA_OCR_DEFER", False):
        ejecutar_pipeline_ocr(documento_fuente_id)
        return

    def al_commit():
        _spawn_async(lambda: _ejecutar_con_db_limpia(documento_fuente_id))

    transaction.on_commit(al_commit)
