# Servicio de conexión desacoplado para MySQL (reutilizable)
import mysql.connector
from mysql.connector import Error
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MySQLConnectionService:
    def __init__(self, config):
        """
        config: dict con claves host, port, database, user, password
        """
        self.config = config
        self.connection = None
    def get_connection_params(self) -> Dict[str, Any]:
        return {
            'host': self.config['host'],
            'port': self.config.get('port', 3306),
            'database': self.config['database'],
            'user': self.config['user'],
            'password': self.config['password'],
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30,
        }
    def test_connection(self, test_tables: bool = False) -> Dict[str, Any]:
        try:
            connection_params = self.get_connection_params()
            self.connection = mysql.connector.connect(**connection_params)
            if not self.connection.is_connected():
                return {'success': False, 'error': 'Failed to establish connection'}
            cursor = self.connection.cursor(dictionary=True)
            database_info = self._get_database_info(cursor)
            version_info = self._get_version_info(cursor)
            tables_count = 0
            if test_tables:
                tables_count = self._test_tables(cursor)
            cursor.close()
            return {
                'success': True,
                'database_info': database_info,
                'version': version_info,
                'tables_count': tables_count,
            }
        except Error as e:
            logger.error(f"Database connection error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error testing connection: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()
    def _get_database_info(self, cursor) -> Dict[str, Any]:
        try:
            cursor.execute("SELECT DATABASE() as name")
            result = cursor.fetchone()
            cursor.execute("""
                SELECT table_schema as database_name, COUNT(*) as table_count, SUM(data_length + index_length) as size_bytes
                FROM information_schema.tables WHERE table_schema = DATABASE() GROUP BY table_schema
            """)
            stats = cursor.fetchone()
            return {
                'name': result['name'] if result else self.config['database'],
                'table_count': stats['table_count'] if stats else 0,
                'size_bytes': stats['size_bytes'] if stats else 0,
                'size_mb': round((stats['size_bytes'] or 0) / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.warning(f"Error getting database info: {e}")
            return {'name': self.config['database'], 'table_count': 0, 'size_bytes': 0, 'size_mb': 0}
    def _get_version_info(self, cursor) -> str:
        try:
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            return result['version'] if result else 'Unknown'
        except Exception as e:
            logger.warning(f"Error getting version info: {e}")
            return 'Unknown'
    def _test_tables(self, cursor) -> int:
        try:
            cursor.execute("SHOW TABLES")
            results = cursor.fetchall()
            return len(results)
        except Exception as e:
            logger.warning(f"Error testing tables: {e}")
            return 0
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        connection = None
        cursor = None
        try:
            connection_params = self.get_connection_params()
            connection = mysql.connector.connect(**connection_params)
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT') or query.strip().upper().startswith('SHOW'):
                results = cursor.fetchall()
                return {'success': True, 'results': results, 'row_count': len(results)}
            else:
                connection.commit()
                affected_rows = cursor.rowcount
                return {'success': True, 'affected_rows': affected_rows}
                
        except Error as e:
            logger.error(f"Query execution error: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
    def close_connection(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None 