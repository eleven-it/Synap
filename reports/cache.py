from django.core.cache import cache


def build_cache_key(tenant_id: int | None, slug: str, payload_hash: str) -> str:
    """Genera claves consistentes para cacheos de reportes."""
    tenant_part = tenant_id or "global"
    return f"reports:{tenant_part}:{slug}:{payload_hash}"


def get_cached_report(tenant_id: int | None, slug: str, payload_hash: str):
    """Recupera un resultado cacheado."""
    return cache.get(build_cache_key(tenant_id, slug, payload_hash))


def set_cached_report(tenant_id: int | None, slug: str, payload_hash: str, data, ttl: int = 900):
    """Guarda un resultado cacheado."""
    cache.set(build_cache_key(tenant_id, slug, payload_hash), data, timeout=ttl)


def invalidate_report_cache(slug: str):
    """Invalida caches por slug (borrado amplio)."""
    # Comentario: Implementar limpieza masiva con key patterns si se usa Redis directo.
    return cache.delete_pattern(f"reports:*:{slug}:*") if hasattr(cache, "delete_pattern") else None


