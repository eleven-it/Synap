"""
Servicio de Connection Pooling para MySQL de administraNET
Maneja un pool de conexiones reutilizables para reducir overhead de conexión
"""
import MySQLdb
import threading
import logging
from typing import Optional, Dict, Any
from django.conf import settings
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MySQLConnectionPool:
    """
    Pool simple de conexiones MySQL usando threading.Lock para thread-safety.
    
    Nota: MySQLdb no soporta pooling nativo, así que implementamos un pool simple
    que reutiliza conexiones cuando están disponibles.
    """
    
    _pools: Dict[str, 'MySQLConnectionPool'] = {}
    _pools_lock = threading.Lock()
    
    def __init__(self, host: str, port: int, user: str, password: str, max_connections: int = 5):
        """
        Inicializa el pool de conexiones.
        
        Args:
            host: Host de MySQL
            port: Puerto de MySQL
            user: Usuario de MySQL
            password: Contraseña de MySQL
            max_connections: Número máximo de conexiones en el pool
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.max_connections = max_connections
        
        self._available_connections = []
        self._in_use_connections = set()
        self._lock = threading.Lock()
        self._connection_count = 0
        
        logger.info(f"✅ Connection pool inicializado: max_connections={max_connections}")
    
    @classmethod
    def get_pool(cls, host: str, port: int, user: str, password: str, max_connections: int = 5) -> 'MySQLConnectionPool':
        """
        Obtiene o crea un pool de conexiones para una configuración específica.
        
        Args:
            host: Host de MySQL
            port: Puerto de MySQL
            user: Usuario de MySQL
            password: Contraseña de MySQL
            max_connections: Número máximo de conexiones en el pool
        
        Returns:
            Instancia del pool de conexiones
        """
        pool_key = f"{host}:{port}:{user}"
        
        with cls._pools_lock:
            if pool_key not in cls._pools:
                cls._pools[pool_key] = cls(host, port, user, password, max_connections)
            return cls._pools[pool_key]
    
    def _create_connection(self, database: str) -> MySQLdb.Connection:
        """Crea una nueva conexión MySQL."""
        try:
            conn = MySQLdb.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                passwd=self.password,
                db=database,
                charset='latin1',
                connect_timeout=10
            )
            self._init_connection_session(conn)
            logger.debug(f"🔌 Nueva conexión creada para {database}")
            return conn
        except Exception as e:
            logger.error(f"❌ Error creando conexión MySQL: {e}")
            raise
    
    def _init_connection_session(self, conn: MySQLdb.Connection) -> None:
        """Inicializa la sesión MySQL para evitar OperationalError (2000, 'Unknown or undefined error code').
        Suele ocurrir por incompatibilidad sql_mode o charset entre cliente y servidor."""
        try:
            cursor = conn.cursor()
            cursor.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES'")
            cursor.close()
        except Exception as init_err:
            logger.debug(f"⚠️ No se pudo ejecutar init en conexión: {init_err}")

    def _is_connection_alive(self, conn: MySQLdb.Connection) -> bool:
        """Verifica si una conexión está viva."""
        try:
            conn.ping()
            return True
        except:
            return False
    
    @contextmanager
    def get_connection(self, database: str):
        """
        Context manager para obtener una conexión del pool.
        
        Usage:
            with pool.get_connection('database_name') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ...")
                ...
        """
        conn = None
        try:
            # Intentar obtener conexión del pool
            with self._lock:
                # Buscar conexión disponible para esta base de datos
                for i, (pool_conn, pool_db) in enumerate(self._available_connections):
                    if pool_db == database and self._is_connection_alive(pool_conn):
                        # Reutilizar conexión existente
                        conn = self._available_connections.pop(i)[0]
                        self._in_use_connections.add(conn)
                        logger.debug(f"♻️ Conexión reutilizada del pool para {database}")
                        break
                
                # Si no hay conexión disponible, crear una nueva si no excedemos el límite
                if conn is None:
                    if self._connection_count < self.max_connections:
                        conn = self._create_connection(database)
                        self._connection_count += 1
                        self._in_use_connections.add(conn)
                        logger.debug(f"🆕 Nueva conexión creada (total: {self._connection_count}/{self.max_connections})")
                    else:
                        # Pool lleno, esperar o crear temporal (por ahora creamos temporal)
                        logger.warning(f"⚠️ Pool lleno, creando conexión temporal para {database}")
                        conn = self._create_connection(database)
                        self._in_use_connections.add(conn)
            
            # Inicializar sesión en cada uso (evita OperationalError 2000 en conexiones reutilizadas)
            self._init_connection_session(conn)
            
            # Retornar conexión
            yield conn
            
        finally:
            # Devolver conexión al pool
            if conn:
                with self._lock:
                    if conn in self._in_use_connections:
                        self._in_use_connections.remove(conn)
                        
                        # Verificar que la conexión sigue viva antes de devolverla
                        if self._is_connection_alive(conn):
                            # Cambiar a la base de datos correcta antes de devolver
                            try:
                                conn.select_db(database)
                                self._available_connections.append((conn, database))
                                logger.debug(f"✅ Conexión devuelta al pool para {database}")
                            except Exception as e:
                                logger.warning(f"⚠️ Error devolviendo conexión al pool: {e}, cerrando")
                                try:
                                    conn.close()
                                    self._connection_count -= 1
                                except:
                                    pass
                        else:
                            # Conexión muerta, cerrarla
                            logger.debug(f"💀 Conexión muerta detectada, cerrando")
                            try:
                                conn.close()
                                self._connection_count -= 1
                            except:
                                pass
    
    def close_all(self):
        """Cierra todas las conexiones del pool."""
        with self._lock:
            for conn, _ in self._available_connections:
                try:
                    conn.close()
                except:
                    pass
            for conn in self._in_use_connections:
                try:
                    conn.close()
                except:
                    pass
            self._available_connections.clear()
            self._in_use_connections.clear()
            self._connection_count = 0
            logger.info("🔒 Todas las conexiones del pool cerradas")


def get_mysql_pool() -> MySQLConnectionPool:
    """
    Obtiene el pool de conexiones MySQL configurado en settings.
    
    Returns:
        Instancia del pool de conexiones
    """
    mysql_config = settings.DATABASES['mysql']
    return MySQLConnectionPool.get_pool(
        host=mysql_config['HOST'],
        port=int(mysql_config['PORT']),
        user=mysql_config['USER'],
        password=mysql_config['PASSWORD'],
        max_connections=5  # Configurable desde settings si es necesario
    )

