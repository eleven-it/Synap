"""
Middleware: una conexión MySQL por request.

Cuando la sesión tiene base_empresa y el path no está excluido, obtiene una conexión
del pool al inicio del request, la guarda en request_mysql_conn_var (contextvars) y
en request para liberarla en process_response o process_exception. Así context
processors y vistas reutilizan la misma conexión vía core.mysql_pool.get_connection.

Si MySQL rechaza la base (inexistente o sin permiso), se cierra la sesión y se
redirige al login para que el usuario elija otra empresa.

Especificación: docs/general/ESPEC_UNA_CONEXION_POR_REQUEST.md
"""
import logging
from typing import Optional

import MySQLdb
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from core.mysql_pool import get_mysql_pool, request_mysql_conn_var

logger = logging.getLogger(__name__)

# Sesión inconsistente con el servidor MySQL local: no tiene sentido seguir con la sesión actual.
_MYSQL_SESSION_INVALID_ERRNOS = frozenset(
    (
        1049,  # Unknown database
        1044,  # Access denied for user ... to database
    )
)

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


def _reset_mpr_request_caches() -> None:
    try:
        from mpr.request_scope_cache import reset_mpr_request_caches

        reset_mpr_request_caches()
    except ImportError:
        pass


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
        _reset_mpr_request_caches()
        if _path_excluded(request.path):
            return None
        base_empresa = _base_empresa_from_request(request)
        if not base_empresa:
            return None
        pool = get_mysql_pool()
        conn_cm = pool.get_connection(base_empresa)
        try:
            conn = conn_cm.__enter__()
        except MySQLdb.OperationalError as exc:
            errno = exc.args[0] if exc.args else None
            if errno not in _MYSQL_SESSION_INVALID_ERRNOS:
                raise
            logger.warning(
                "MySQL rechazó base_empresa=%s (errno=%s): %s. Cerrando sesión y redirigiendo a login.",
                base_empresa,
                errno,
                exc,
            )
            request.session.flush()
            messages.error(
                request,
                "La empresa seleccionada no está disponible en este servidor o no tenés acceso a su base de datos. "
                "Iniciá sesión de nuevo y elegí otra empresa.",
            )
            return redirect("login:login")

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
        _reset_mpr_request_caches()
