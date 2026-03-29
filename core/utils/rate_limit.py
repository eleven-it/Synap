"""
Rate limiting ligero vía cache (sin dependencias extra).
Usar con Redis/LocMem en tests; incr debe estar soportado por el backend.
Si el backend no está disponible, se omite el límite (log warning) para no bloquear login en local.
"""
from __future__ import annotations

import logging
from typing import Optional

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)


def client_ip(request: HttpRequest) -> str:
    forwarded = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
    if forwarded:
        return forwarded
    return (request.META.get('REMOTE_ADDR') or '').strip() or 'unknown'


def check_rate_limit(
    request: HttpRequest,
    *,
    key_prefix: str,
    limit: int,
    period_seconds: int = 60,
    exceeded_body: Optional[dict] = None,
) -> Optional[JsonResponse]:
    """
    Incrementa contador por IP. Si supera limit en la ventana period_seconds, devuelve JsonResponse 429.
    exceeded_body: cuerpo JSON; por defecto { success, error } (API empresas).
    """
    ip = client_ip(request)
    key = f'synap_rl:{key_prefix}:{ip}'
    try:
        try:
            n = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=period_seconds)
            n = 1
    except Exception as e:
        logger.warning('Rate limit omitido (cache no disponible): %s', e)
        return None
    if n > limit:
        body = exceeded_body or {
            'success': False,
            'error': 'Demasiadas solicitudes desde esta dirección. Espere unos minutos e intente de nuevo.',
        }
        return JsonResponse(body, status=429)
    return None
