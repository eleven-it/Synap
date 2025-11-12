"""
Servicio de cache para resultados y reglas
"""
from django.core.cache import cache
from typing import Any, Optional

class CacheService:
    """Gestión de cache para el sistema"""
    
    PREFIX = 'reports_ai_'
    DEFAULT_TIMEOUT = 3600  # 1 hora
    
    @classmethod
    def get(cls, key: str) -> Optional[Any]:
        """Obtiene valor del cache"""
        return cache.get(f"{cls.PREFIX}{key}")
    
    @classmethod
    def set(cls, key: str, value: Any, timeout: int = DEFAULT_TIMEOUT):
        """Guarda valor en cache"""
        cache.set(f"{cls.PREFIX}{key}", value, timeout)
    
    @classmethod
    def delete(cls, key: str):
        """Elimina valor del cache"""
        cache.delete(f"{cls.PREFIX}{key}")

