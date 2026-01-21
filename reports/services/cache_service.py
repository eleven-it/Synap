"""
Servicio de cache con TTL y LRU para el Mapa de Datos.
Implementa un cache en memoria con expiración por tiempo (TTL) y política LRU.
"""
import time
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class TTLCacheLRU:
    """
    Cache con TTL (Time To Live) y política LRU (Least Recently Used).
    
    Características:
    - Expiración automática de entradas por tiempo (TTL)
    - Política LRU: elimina la entrada menos usada cuando se alcanza maxsize
    - Thread-safe usando threading.Lock
    - Soporte para borrado por prefijo
    """
    
    def __init__(self, maxsize: int = 100, ttl_seconds: int = 1800):
        """
        Inicializa el cache.
        
        Args:
            maxsize: Número máximo de entradas en el cache (default: 100)
            ttl_seconds: Tiempo de vida en segundos (default: 1800 = 30 min)
        """
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()
        logger.info(f"🔧 TTLCacheLRU inicializado: maxsize={maxsize}, ttl={ttl_seconds}s")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del cache.
        
        Args:
            key: Clave del cache
            
        Returns:
            Valor almacenado o None si no existe o expiró
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            expire_at, value = self._cache[key]
            
            # Verificar si expiró
            if time.time() > expire_at:
                del self._cache[key]
                logger.debug(f"⏰ Cache expirado para key: {key}")
                return None
            
            # Mover al final (LRU: más recientemente usado)
            self._cache.move_to_end(key)
            
            return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Almacena un valor en el cache.
        
        Args:
            key: Clave del cache
            value: Valor a almacenar
        """
        with self._lock:
            expire_at = time.time() + self.ttl_seconds
            
            # Si la clave ya existe, actualizar
            if key in self._cache:
                self._cache[key] = (expire_at, value)
                self._cache.move_to_end(key)
                logger.debug(f"🔄 Cache actualizado: {key}")
                return
            
            # Si alcanzamos el límite, eliminar el menos usado (LRU)
            if len(self._cache) >= self.maxsize:
                # El primer elemento es el menos usado
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"🗑️ Cache LRU: eliminada key más antigua: {oldest_key}")
            
            # Agregar nueva entrada
            self._cache[key] = (expire_at, value)
            logger.debug(f"✅ Cache almacenado: {key} (expira en {self.ttl_seconds}s)")
    
    def delete(self, key: str) -> bool:
        """
        Elimina una clave del cache.
        
        Args:
            key: Clave a eliminar
            
        Returns:
            True si se eliminó, False si no existía
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"🗑️ Cache eliminado: {key}")
                return True
            return False
    
    def clear_prefix(self, prefix: str) -> int:
        """
        Elimina todas las claves que empiezan con el prefijo dado.
        
        Args:
            prefix: Prefijo de las claves a eliminar
            
        Returns:
            Número de claves eliminadas
        """
        with self._lock:
            keys_to_delete = [key for key in self._cache.keys() if key.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            
            count = len(keys_to_delete)
            if count > 0:
                logger.info(f"🗑️ Cache clear_prefix '{prefix}': {count} claves eliminadas")
            
            return count
    
    def clear(self) -> None:
        """Elimina todas las entradas del cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"🗑️ Cache limpiado completamente: {count} entradas eliminadas")
    
    def size(self) -> int:
        """Retorna el número de entradas actuales en el cache."""
        with self._lock:
            return len(self._cache)
    
    def cleanup_expired(self) -> int:
        """
        Limpia manualmente las entradas expiradas.
        
        Returns:
            Número de entradas expiradas eliminadas
        """
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (expire_at, _) in self._cache.items()
                if current_time > expire_at
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            count = len(expired_keys)
            if count > 0:
                logger.debug(f"🧹 Cache cleanup: {count} entradas expiradas eliminadas")
            
            return count

