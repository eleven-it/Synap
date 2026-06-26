"""Rate limiter para API Nuvemshop (2 req/s documentado)."""

import logging
import threading
import time
from typing import Any, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Nuvemshop: máximo 2 requests por segundo por tienda
NUVEMSHOP_MAX_REQUESTS_PER_SECOND = 2
_MIN_INTERVAL = 1.0 / NUVEMSHOP_MAX_REQUESTS_PER_SECOND

DEFAULT_MAX_RETRIES = 5
DEFAULT_MAX_CONSECUTIVE_429 = 5

_BACKOFF_BASE_SECONDS = 1.0
_BACKOFF_MAX_SECONDS = 60.0

_lock = threading.Lock()
_last_request_at = 0.0
_rate_limit_remaining: Optional[int] = None
_rate_limit_reset_at: Optional[float] = None


def get_max_retries() -> int:
    """Máximo de reintentos por request HTTP (configurable vía settings)."""
    return getattr(settings, 'NUVEMSHOP_MAX_RETRIES', DEFAULT_MAX_RETRIES)


def get_max_consecutive_429() -> int:
    """Máximo de 429 consecutivos antes de abandonar un request."""
    return getattr(
        settings,
        'NUVEMSHOP_MAX_CONSECUTIVE_429',
        DEFAULT_MAX_CONSECUTIVE_429,
    )


def reset_rate_limit_state() -> None:
    """Reinicia estado interno del rate limiter (útil en tests)."""
    global _last_request_at, _rate_limit_remaining, _rate_limit_reset_at
    with _lock:
        _last_request_at = 0.0
        _rate_limit_remaining = None
        _rate_limit_reset_at = None


def _get_header(response: Any, name: str) -> Optional[str]:
    headers = getattr(response, 'headers', None)
    if headers is None:
        return None
    return headers.get(name) or headers.get(name.lower()) or headers.get(name.title())


def _parse_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == '':
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def update_rate_limit_from_response(response) -> None:
    """Lee headers x-rate-limit-* y adapta el estado interno del limiter."""
    global _rate_limit_remaining, _rate_limit_reset_at

    remaining = _parse_int(_get_header(response, 'x-rate-limit-remaining'))
    reset_ms = _parse_int(_get_header(response, 'x-rate-limit-reset'))

    with _lock:
        if remaining is not None:
            _rate_limit_remaining = remaining
        if reset_ms is not None and reset_ms > 0:
            _rate_limit_reset_at = time.monotonic() + (reset_ms / 1000.0)


def wait_for_rate_limit() -> None:
    """Espera el intervalo mínimo entre llamadas HTTP a la API."""
    global _last_request_at

    with _lock:
        now = time.monotonic()

        if _rate_limit_remaining is not None and _rate_limit_remaining <= 0:
            if _rate_limit_reset_at is not None and _rate_limit_reset_at > now:
                sleep_time = _rate_limit_reset_at - now
                if sleep_time > 0:
                    logger.debug(
                        'Rate limit: esperando %.2fs (remaining=0)',
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    now = time.monotonic()

        elapsed = now - _last_request_at
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        _last_request_at = time.monotonic()


def _compute_backoff_seconds(attempt: int, reset_ms: Optional[int] = None) -> float:
    """Calcula pausa: header x-rate-limit-reset (ms) o backoff exponencial."""
    if reset_ms is not None and reset_ms > 0:
        return reset_ms / 1000.0
    delay = _BACKOFF_BASE_SECONDS * (2 ** max(0, attempt - 1))
    return min(delay, _BACKOFF_MAX_SECONDS)


def wait_after_rate_limit_response(response, attempt: int = 1) -> None:
    """Espera tras 429 o error transitorio según reset header o backoff exponencial."""
    reset_ms = _parse_int(_get_header(response, 'x-rate-limit-reset'))
    delay = _compute_backoff_seconds(attempt, reset_ms)
    logger.warning(
        'Rate limit / error transitorio: reintento %s, esperando %.2fs (reset_ms=%s)',
        attempt,
        delay,
        reset_ms,
    )
    time.sleep(delay)
