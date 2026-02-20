"""Conexión a MySQL por base_empresa."""
import logging
from contextlib import contextmanager
from typing import Optional

import MySQLdb
from django.conf import settings

logger = logging.getLogger(__name__)


def get_mysql_connection(base_empresa: str):
    """Obtiene conexión MySQL a la base de la empresa."""
    mysql_config = settings.DATABASES['mysql']
    return MySQLdb.connect(
        host=mysql_config['HOST'],
        port=int(mysql_config.get('PORT', 3306)),
        user=mysql_config['USER'],
        passwd=mysql_config['PASSWORD'],
        db=base_empresa,
        charset='latin1',
    )


@contextmanager
def mysql_cursor(base_empresa: str, dict_cursor: bool = False):
    """Context manager para cursor MySQL."""
    conn = get_mysql_connection(base_empresa)
    try:
        cursor_class = MySQLdb.cursors.DictCursor if dict_cursor else MySQLdb.cursors.Cursor
        cursor = conn.cursor(cursor_class)
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_base_empresa_from_request(request) -> Optional[str]:
    """
    Obtiene base_empresa de la sesión (elegida en el login desde la base 'empresas' del servidor).
    Si la sesión no tiene base_empresa, usa la base configurada en .env (DATABASES['mysql']['NAME']).
    """
    base = request.session.get('user', {}).get('base_empresa')
    if base:
        return base
    return settings.DATABASES.get('mysql', {}).get('NAME')
