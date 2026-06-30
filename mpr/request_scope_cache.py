"""
Cache por request (contextvars) para servicios MPR.

No usa TTL ni cache global: solo deduplica lecturas dentro del mismo request HTTP
cuando RequestScopedMysqlMiddleware está activo. Se limpia al inicio y al cierre
del request en core.middleware.request_scoped_mysql.
"""
from contextvars import ContextVar
from typing import Any, Dict, List, Optional, Tuple

DepositoSumaStockKey = Tuple[str, Optional[int]]

_depositos_suma_stock_cache: ContextVar[
    Optional[Dict[DepositoSumaStockKey, List[Dict[str, Any]]]]
] = ContextVar("mpr_depositos_suma_stock_cache", default=None)


def reset_mpr_request_caches() -> None:
    """Limpia caches MPR del contexto actual (inicio/fin de request)."""
    _depositos_suma_stock_cache.set(None)


def mpr_request_cache_enabled() -> bool:
    """True cuando hay conexión MySQL por request (middleware activo)."""
    try:
        from core.mysql_pool import request_mysql_conn_var

        return request_mysql_conn_var.get() is not None
    except Exception:
        return False


def get_cached_depositos_con_suma_stock(
    key: DepositoSumaStockKey,
) -> Optional[List[Dict[str, Any]]]:
    cache = _depositos_suma_stock_cache.get()
    if not cache:
        return None
    hit = cache.get(key)
    if hit is None:
        return None
    return [dict(d) for d in hit]


def set_cached_depositos_con_suma_stock(
    key: DepositoSumaStockKey,
    depositos: List[Dict[str, Any]],
) -> None:
    cache = _depositos_suma_stock_cache.get()
    if cache is None:
        cache = {}
        _depositos_suma_stock_cache.set(cache)
    cache[key] = [dict(d) for d in depositos]
