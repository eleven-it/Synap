"""
Pool de conexiones MySQL para Synap (acceso a administraNET).
Patrón único para todo el proyecto: core, login, reports, self_checkout.

Una conexión por request: cuando el middleware RequestScopedMysqlMiddleware
asigna una conexión para el request, get_connection/mysql_cursor la reutilizan
vía request_mysql_conn_var (contextvars) y no la devuelven al pool; el middleware
la libera al final del request.

Las conexiones ociosas en el pool NO se mantienen indefinidamente: si superan
``idle_seconds`` (OPTIONS.POOL_IDLE_SECONDS, default 30) se cierran. Al salir
del proceso se llama ``close_all`` (atexit).

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
import atexit
import MySQLdb
import threading
import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, List, Optional, Tuple, Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# Variable de contexto: (base_empresa, conn) cuando el middleware asignó una conexión por request.
# Usado por get_connection() para reutilizar la misma conexión sin devolverla al pool.
request_mysql_conn_var: ContextVar[Optional[Tuple[str, Any]]] = ContextVar(
    "request_mysql_conn", default=None
)

# Segundos máximos que una conexión puede quedar en Sleep en el pool.
DEFAULT_POOL_IDLE_SECONDS = 30


class MySQLConnectionPool:
    """
    Pool de conexiones MySQL (thread-safe).
    Reutiliza conexiones recientes; cierra las ociosas para no dejar Sleep abiertos
    en el servidor MySQL (restore, mantenimiento, límites de conexión).
    """

    _pools: Dict[str, 'MySQLConnectionPool'] = {}
    _pools_lock = threading.Lock()
    _atexit_registered = False

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        max_connections: int = 5,
        idle_seconds: int = DEFAULT_POOL_IDLE_SECONDS,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.max_connections = max_connections
        self.idle_seconds = max(0, int(idle_seconds))
        # (conn, database, returned_at_monotonic)
        self._available_connections: List[Tuple[Any, str, float]] = []
        self._in_use_connections = set()
        self._lock = threading.Lock()
        self._connection_count = 0
        logger.info(
            "MySQL connection pool inicializado: max_connections=%s idle_seconds=%s",
            max_connections,
            self.idle_seconds,
        )

    @classmethod
    def get_pool(
        cls,
        host: str,
        port: int,
        user: str,
        password: str,
        max_connections: int = 5,
        idle_seconds: int = DEFAULT_POOL_IDLE_SECONDS,
    ) -> 'MySQLConnectionPool':
        pool_key = f"{host}:{port}:{user}"
        with cls._pools_lock:
            if pool_key not in cls._pools:
                cls._pools[pool_key] = cls(
                    host, port, user, password, max_connections, idle_seconds=idle_seconds
                )
                cls._ensure_atexit()
            return cls._pools[pool_key]

    @classmethod
    def _ensure_atexit(cls) -> None:
        if cls._atexit_registered:
            return
        cls._atexit_registered = True

        def _cerrar_pools_al_salir() -> None:
            with cls._pools_lock:
                pools = list(cls._pools.values())
            for pool in pools:
                try:
                    pool.close_all()
                except Exception:
                    pass

        atexit.register(_cerrar_pools_al_salir)

    @classmethod
    def close_all_pools(cls) -> int:
        """Cierra todos los pools del proceso. Devuelve cuántos pools cerró."""
        with cls._pools_lock:
            pools = list(cls._pools.values())
        for pool in pools:
            pool.close_all()
        return len(pools)

    def _discard_connection(self, conn: Any) -> None:
        try:
            conn.close()
        except Exception:
            pass
        self._connection_count = max(0, self._connection_count - 1)

    def _purge_idle_unlocked(self, now: Optional[float] = None) -> int:
        """Cierra conexiones disponibles ociosas. Requiere self._lock."""
        if self.idle_seconds <= 0:
            # idle_seconds=0 → no retener: cerrar todo lo disponible
            closed = 0
            for conn, _db, _ts in self._available_connections:
                self._discard_connection(conn)
                closed += 1
            self._available_connections.clear()
            return closed
        now = time.monotonic() if now is None else now
        kept: List[Tuple[Any, str, float]] = []
        closed = 0
        for conn, db, returned_at in self._available_connections:
            if (now - returned_at) >= self.idle_seconds:
                self._discard_connection(conn)
                closed += 1
            else:
                kept.append((conn, db, returned_at))
        self._available_connections = kept
        return closed

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
        temporal = False  # conexión extra sobre el tope: no vuelve al pool
        try:
            with self._lock:
                self._purge_idle_unlocked()
                kept: List[Tuple[Any, str, float]] = []
                for pool_conn, pool_db, returned_at in self._available_connections:
                    if conn is None and pool_db == database:
                        if self._is_connection_alive(pool_conn):
                            conn = pool_conn
                            self._in_use_connections.add(conn)
                            logger.debug("Conexión reutilizada del pool para %s", database)
                        else:
                            self._discard_connection(pool_conn)
                        continue
                    kept.append((pool_conn, pool_db, returned_at))
                self._available_connections = kept
                if conn is None:
                    if self._connection_count < self.max_connections:
                        conn = self._create_connection(database)
                        self._connection_count += 1
                        self._in_use_connections.add(conn)
                    else:
                        logger.warning("Pool lleno, creando conexión temporal para %s", database)
                        conn = self._create_connection(database)
                        self._in_use_connections.add(conn)
                        temporal = True
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
                        # idle_seconds=0 o temporal → cerrar siempre (no Sleep ocioso)
                        if temporal or self.idle_seconds <= 0 or not self._is_connection_alive(conn):
                            self._discard_connection(conn)
                        else:
                            try:
                                conn.select_db(database)
                                self._available_connections.append((conn, database, time.monotonic()))
                                self._purge_idle_unlocked()
                            except Exception as e:
                                logger.warning("Error devolviendo conexión al pool: %s", e)
                                self._discard_connection(conn)

    def close_all(self) -> None:
        with self._lock:
            for c, _db, _ts in self._available_connections:
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
    opts = cfg.get('OPTIONS') or {}
    return MySQLConnectionPool.get_pool(
        host=cfg['HOST'],
        port=int(cfg.get('PORT', 3306)),
        user=cfg['USER'],
        password=cfg['PASSWORD'],
        max_connections=int(opts.get('MAX_CONNECTIONS', 5)),
        idle_seconds=int(opts.get('POOL_IDLE_SECONDS', DEFAULT_POOL_IDLE_SECONDS)),
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
