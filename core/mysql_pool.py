"""
Pool de conexiones MySQL para Synap (acceso a administraNET).
Patrón único para todo el proyecto: core, login, reports, self_checkout.

Una conexión por request: cuando el middleware RequestScopedMysqlMiddleware
asigna una conexión para el request, get_connection/mysql_cursor la reutilizan
vía request_mysql_conn_var (contextvars) y no la devuelven al pool; el middleware
la libera al final del request.

Uso:
    from core.mysql_pool import mysql_cursor, get_connection, get_mysql_pool

    with mysql_cursor('base_empresa', dict_cursor=True) as cursor:
        cursor.execute("SELECT ...")

    with get_connection('base_empresa') as conn:
        conn.autocommit(False)
        cursor = conn.cursor()
        ...
        conn.commit()
"""
import MySQLdb
import threading
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Optional, Tuple, Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# Variable de contexto: (base_empresa, conn) cuando el middleware asignó una conexión por request.
# Usado por get_connection() para reutilizar la misma conexión sin devolverla al pool.
request_mysql_conn_var: ContextVar[Optional[Tuple[str, Any]]] = ContextVar(
    "request_mysql_conn", default=None
)


class MySQLConnectionPool:
    """
    Pool de conexiones MySQL (thread-safe).
    Reutiliza conexiones para limitar el número abierto y reducir overhead.
    """

    _pools: Dict[str, 'MySQLConnectionPool'] = {}
    _pools_lock = threading.Lock()

    def __init__(self, host: str, port: int, user: str, password: str, max_connections: int = 5):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.max_connections = max_connections
        self._available_connections = []
        self._in_use_connections = set()
        self._lock = threading.Lock()
        self._connection_count = 0
        logger.info("MySQL connection pool inicializado: max_connections=%s", max_connections)

    @classmethod
    def get_pool(
        cls,
        host: str,
        port: int,
        user: str,
        password: str,
        max_connections: int = 5,
    ) -> 'MySQLConnectionPool':
        pool_key = f"{host}:{port}:{user}"
        with cls._pools_lock:
            if pool_key not in cls._pools:
                cls._pools[pool_key] = cls(host, port, user, password, max_connections)
            return cls._pools[pool_key]

    def _create_connection(self, database: str) -> MySQLdb.Connection:
        conn = MySQLdb.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            passwd=self.password,
            db=database,
            charset='latin1',
            connect_timeout=10,
        )
        self._init_connection_session(conn)
        logger.debug("Nueva conexión MySQL creada para %s", database)
        return conn

    def _init_connection_session(self, conn: MySQLdb.Connection) -> None:
        """Deja la conexión en estado limpio para ver los últimos datos comprometidos."""
        try:
            conn.rollback()
            conn.autocommit(True)
        except Exception as e:
            logger.debug("No se pudo hacer rollback/autocommit en conexión: %s", e)
        try:
            cursor = conn.cursor()
            cursor.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES'")
            cursor.close()
        except Exception as e:
            logger.debug("No se pudo ejecutar init en conexión: %s", e)

    def _is_connection_alive(self, conn: MySQLdb.Connection) -> bool:
        try:
            conn.ping()
            return True
        except Exception:
            return False

    @contextmanager
    def get_connection(self, database: str):
        conn = None
        try:
            with self._lock:
                for i, (pool_conn, pool_db) in enumerate(self._available_connections):
                    if pool_db == database and self._is_connection_alive(pool_conn):
                        conn = self._available_connections.pop(i)[0]
                        self._in_use_connections.add(conn)
                        logger.debug("Conexión reutilizada del pool para %s", database)
                        break
                if conn is None:
                    if self._connection_count < self.max_connections:
                        conn = self._create_connection(database)
                        self._connection_count += 1
                        self._in_use_connections.add(conn)
                    else:
                        logger.warning("Pool lleno, creando conexión temporal para %s", database)
                        conn = self._create_connection(database)
                        self._in_use_connections.add(conn)
                else:
                    # Reutilizada: asegurar que está en la base correcta (evita leer de otra empresa)
                    if database:
                        try:
                            conn.select_db(database)
                        except Exception as e:
                            logger.warning("No se pudo select_db(%s) en conexión reutilizada: %s", database, e)
            self._init_connection_session(conn)
            yield conn
        finally:
            if conn:
                with self._lock:
                    if conn in self._in_use_connections:
                        self._in_use_connections.remove(conn)
                        if self._is_connection_alive(conn):
                            try:
                                conn.select_db(database)
                                self._available_connections.append((conn, database))
                            except Exception as e:
                                logger.warning("Error devolviendo conexión al pool: %s", e)
                                try:
                                    conn.close()
                                    self._connection_count -= 1
                                except Exception:
                                    pass
                        else:
                            try:
                                conn.close()
                                self._connection_count -= 1
                            except Exception:
                                pass

    def close_all(self) -> None:
        with self._lock:
            for c, _ in self._available_connections:
                try:
                    c.close()
                except Exception:
                    pass
            for c in self._in_use_connections:
                try:
                    c.close()
                except Exception:
                    pass
            self._available_connections.clear()
            self._in_use_connections.clear()
            self._connection_count = 0
            logger.info("Todas las conexiones del pool cerradas")


def get_mysql_pool() -> MySQLConnectionPool:
    """Obtiene el pool MySQL configurado en settings.DATABASES['mysql']."""
    try:
        cfg = settings.DATABASES['mysql']
    except KeyError as exc:
        raise ImproperlyConfigured(
            "DATABASES['mysql'] no está definido. Si SYNAP_MIGRATIONS_POSTGRES_ONLY=1 "
            "está en el entorno del contenedor, no afecta runserver tras actualizar settings; "
            "reiniciá el proceso. Revisá DB_HOST, DB_USER, DB_PASSWORD y DB_NAME en .env."
        ) from exc
    return MySQLConnectionPool.get_pool(
        host=cfg['HOST'],
        port=int(cfg.get('PORT', 3306)),
        user=cfg['USER'],
        password=cfg['PASSWORD'],
        max_connections=int(cfg.get('OPTIONS', {}).get('MAX_CONNECTIONS', 5)),
    )


@contextmanager
def _noop_connection_manager(conn: Any):
    """Context manager que solo hace yield conn y en exit no libera (para conexión de request)."""
    yield conn


@contextmanager
def get_connection(base_empresa: str):
    """
    Context manager para obtener una conexión del pool (transacciones largas).
    Si hay una conexión de request para esta base_empresa (vía RequestScopedMysqlMiddleware),
    la reutiliza y no la devuelve al pool.
    """
    base_empresa = (base_empresa or "").strip()
    try:
        current = request_mysql_conn_var.get()
        if current is not None and len(current) >= 2 and current[0] == base_empresa:
            conn = current[1]
            with _noop_connection_manager(conn):
                yield conn
            return
    except LookupError:
        pass
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        yield conn


@contextmanager
def mysql_cursor(base_empresa: str, dict_cursor: bool = False):
    """
    Context manager: obtiene conexión del pool, entrega cursor, commit/rollback al salir.
    Uso: with mysql_cursor('base', dict_cursor=True) as cursor: ...
    """
    cursor = None
    with get_connection(base_empresa) as conn:
        cursor_class = MySQLdb.cursors.DictCursor if dict_cursor else MySQLdb.cursors.Cursor
        cursor = conn.cursor(cursor_class)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
