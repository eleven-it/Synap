"""
Conexión MySQL MPR por base_empresa (pool Synap).
"""
from typing import Optional

from django.conf import settings

from core.mysql_pool import get_connection, mysql_cursor

get_mysql_connection = get_connection
__all__ = ["get_mysql_connection", "mysql_cursor", "get_base_empresa_from_request"]


def get_base_empresa_from_request(request) -> Optional[str]:
    """base_empresa de sesión o fallback settings DATABASES mysql NAME."""
    base = request.session.get("user", {}).get("base_empresa")
    if base:
        return base
    return settings.DATABASES.get("mysql", {}).get("NAME")
