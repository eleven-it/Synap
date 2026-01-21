from django.core.cache import cache
from typing import Optional, Any


def build_cache_key(tenant_id: int | None, slug: str, payload_hash: str) -> str:
    """Genera claves consistentes para cacheos de reportes."""
    tenant_part = tenant_id or "global"
    return f"reports:{tenant_part}:{slug}:{payload_hash}"


def get_cached_report(tenant_id: int | None, slug: str, payload_hash: str) -> Optional[Any]:
    """
    Recupera un resultado cacheado.
    
    Returns:
        QueryResult si existe en caché, None si no existe
    """
    # Importación diferida para evitar circular
    from .services.query_runner import QueryResult
    
    cache_key = build_cache_key(tenant_id, slug, payload_hash)
    cached_data = cache.get(cache_key)
    
    if cached_data is None:
        return None
    
    # Si es un dict (formato serializado), convertirlo a QueryResult
    if isinstance(cached_data, dict):
        try:
            return QueryResult(
                meta=cached_data.get('meta', {}),
                data=cached_data.get('data', []),
                totals=cached_data.get('totals', {}),
                notes=cached_data.get('notes', [])
            )
        except Exception as e:
            # Si hay error al reconstruir, retornar None (cache corrupto)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error reconstruyendo QueryResult desde caché: {e}")
            return None
    
    # Si ya es un QueryResult, retornarlo directamente
    if isinstance(cached_data, QueryResult):
        return cached_data
    
    return None


def set_cached_report(tenant_id: int | None, slug: str, payload_hash: str, data: Any, ttl: int = 900):
    """
    Guarda un resultado cacheado.
    
    Args:
        tenant_id: ID del tenant (opcional)
        slug: Slug del reporte
        payload_hash: Hash del payload de filtros
        data: QueryResult a cachear
        ttl: Time to live en segundos
    """
    cache_key = build_cache_key(tenant_id, slug, payload_hash)
    
    # Convertir QueryResult a dict para serialización
    # Esto asegura compatibilidad con diferentes backends de caché
    if hasattr(data, 'meta') and hasattr(data, 'data') and hasattr(data, 'totals') and hasattr(data, 'notes'):
        # Es un QueryResult
        cache_data = {
            'meta': data.meta,
            'data': data.data,
            'totals': data.totals,
            'notes': data.notes
        }
    else:
        # Ya es un dict
        cache_data = data
    
    cache.set(cache_key, cache_data, timeout=ttl)


def invalidate_report_cache(slug: str):
    """Invalida caches por slug (borrado amplio)."""
    # Comentario: Implementar limpieza masiva con key patterns si se usa Redis directo.
    return cache.delete_pattern(f"reports:*:{slug}:*") if hasattr(cache, "delete_pattern") else None


