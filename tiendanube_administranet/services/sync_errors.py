"""
Clasificación de errores sync Tienda Nube ↔ AdministraNET.

Semántica adminnet-module-migration: NOT CONFIGURED, INVALID DATA, TRANSIENT FAILURE.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Optional


class SyncErrorKind(Enum):
    NOT_CONFIGURED = 'not_configured'
    INVALID_DATA = 'invalid_data'
    TRANSIENT_FAILURE = 'transient_failure'


_NOT_CONFIGURED_HTTP = frozenset({402})
_TRANSIENT_HTTP = frozenset({429, 502, 503, 504})


def classify_tiendanube_response(status: int) -> SyncErrorKind:
    """Clasifica respuesta HTTP de la API Tienda Nube."""
    if status in _NOT_CONFIGURED_HTTP:
        return SyncErrorKind.NOT_CONFIGURED
    if status in _TRANSIENT_HTTP:
        return SyncErrorKind.TRANSIENT_FAILURE
    return SyncErrorKind.INVALID_DATA


def classify_webhook_error(
    exc: BaseException,
    http_status: Optional[int] = None,
) -> SyncErrorKind:
    """Clasifica excepción o código HTTP de procesamiento webhook."""
    if isinstance(exc, json.JSONDecodeError):
        return SyncErrorKind.INVALID_DATA
    if http_status is not None:
        return classify_tiendanube_response(http_status)
    return SyncErrorKind.INVALID_DATA


def should_retry_webhook_failure(
    exc: Optional[BaseException] = None,
    http_status: Optional[int] = None,
) -> bool:
    """Indica si un fallo webhook debe programar retry (solo TRANSIENT)."""
    if exc is not None:
        kind = classify_webhook_error(exc, http_status=http_status)
    elif http_status is not None:
        kind = classify_tiendanube_response(http_status)
    else:
        kind = SyncErrorKind.INVALID_DATA
    return kind == SyncErrorKind.TRANSIENT_FAILURE
