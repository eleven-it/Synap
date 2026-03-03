"""
Pool de conexiones MySQL: re-exporta desde core (origen único).
Mantener este módulo para compatibilidad con imports existentes en reports.
"""
from core.mysql_pool import (
    MySQLConnectionPool,
    get_mysql_pool,
    get_connection,
    mysql_cursor,
)

__all__ = ['MySQLConnectionPool', 'get_mysql_pool', 'get_connection', 'mysql_cursor']
