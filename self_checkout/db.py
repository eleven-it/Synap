"""
Conexión a MySQL por base_empresa.
Usa el pool de core (origen único). Para transacciones largas usar get_mysql_connection como context manager.
"""
from typing import Optional

from django.conf import settings

from core.mysql_pool import get_connection, mysql_cursor

# Re-exportar para que los imports existentes sigan funcionando
get_mysql_connection = get_connection  # context manager: with get_mysql_connection(base) as conn
__all__ = ['get_mysql_connection', 'mysql_cursor', 'get_base_empresa_from_request']


def get_base_empresa_from_request(request) -> Optional[str]:
    """
    Obtiene base_empresa de la sesión (elegida en el login desde la base 'empresas').
    Si no hay base_empresa en sesión, usa la base configurada en settings (mysql NAME).
    """
    base = request.session.get('user', {}).get('base_empresa')
    if base:
        return base
    return settings.DATABASES.get('mysql', {}).get('NAME')
