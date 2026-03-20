"""
Middleware: una conexión MySQL por request.

Cuando la sesión tiene base_empresa y el path no está excluido, obtiene una conexión
del pool al inicio del request, la guarda en request_mysql_conn_var (contextvars) y
en request para liberarla en process_response o process_exception. Así context
processors y vistas reutilizan la misma conexión vía core.mysql_pool.get_connection.

Especificación: docs/general/ESPEC_UNA_CONEXION_POR_REQUEST.md
"""
import logging
from typing import Callable, Optional

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from core.mysql_pool import get_mysql_pool, request_mysql_conn_var

logger = logging.getLogger(__name__)

# Paths que no usan MySQL de administraNET: no abrir conexión de request.
REQUEST_MYSQL_EXCLUDED_PREFIXES = (
    "/static/",
    "/media/",
    "/sw.js",
    "/manifest.json",
    "/offline/",
)


def _path_excluded(path: str) -> bool:
    if not path:
        return True
    path = path.split("?")[0]
    return any(path.startswith(p) or path == p.rstrip("/") for p in REQUEST_MYSQL_EXCLUDED_PREFIXES)


def _base_empresa_from_request(request: HttpRequest) -> Optional[str]:
    session_user = getattr(request, "session", {}).get("user") or {}
    base_empresa = session_user.get("base_empresa")
    if isinstance(base_empresa, str) and base_empresa.strip():
        return base_empresa.strip()
    return None


class RequestScopedMysqlMiddleware(MiddlewareMixin):
    """
    Asigna una conexión MySQL por request cuando hay base_empresa en sesión
    y la ruta no está excluida. La libera en process_response o process_exception.
    """

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        if _path_excluded(request.path):
            return None
        base_empresa = _base_empresa_from_request(request)
        if not base_empresa:
            return None
        pool = get_mysql_pool()
        conn_cm = pool.get_connection(base_empresa)
        conn = conn_cm.__enter__()
        request._mysql_conn_ref = conn_cm
        request._mysql_base_empresa = base_empresa
        request_mysql_conn_var.set((base_empresa, conn))
        return None

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        self._release_request_connection(request)
        return response

    def process_exception(
        self, request: HttpRequest, exception: Exception
    ) -> Optional[HttpResponse]:
        self._release_request_connection(request)
        return None

    def _release_request_connection(self, request: HttpRequest) -> None:
        conn_cm = getattr(request, "_mysql_conn_ref", None)
        if conn_cm is not None:
            try:
                conn_cm.__exit__(None, None, None)
            except Exception as e:
                logger.warning("Error liberando conexión de request: %s", e)
            finally:
                delattr(request, "_mysql_conn_ref")
                if hasattr(request, "_mysql_base_empresa"):
                    delattr(request, "_mysql_base_empresa")
            try:
                request_mysql_conn_var.set(None)
            except Exception:
                pass
