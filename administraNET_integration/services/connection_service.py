"""
Servicio de conexión para AdministraNET
Maneja la conexión a la base de datos MySQL de AdministraNET
"""

import mysql.connector
from mysql.connector import Error
import logging
from typing import Dict, Any, Optional
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

class AdministraNETConnectionService:
    """
    Servicio para manejar conexiones a la base de datos de AdministraNET
    """
    
    def __init__(self, config):
        """
        Inicializar servicio con configuración
        
        Args:
            config: Instancia de AdministraNETConfig
        """
        self.config = config
        self.connection = None
        
    def get_connection_params(self) -> Dict[str, Any]:
        """
        Obtener parámetros de conexión
        
        Returns:
            Dict con parámetros de conexión
        """
        return {
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database_name,
            'user': self.config.username,
            'password': self.config.password,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': True,
            'connect_timeout': 10,
            'read_timeout': 30,
            'write_timeout': 30,
        }
    
    def test_connection(self, test_tables: bool = False) -> Dict[str, Any]:
        """
        Probar conexión a la base de datos
        
        Args:
            test_tables: Si debe verificar tablas específicas
            
        Returns:
            Dict con resultado del test
        """
        try:
            # Establecer conexión
            connection_params = self.get_connection_params()
            self.connection = mysql.connector.connect(**connection_params)
            
            if not self.connection.is_connected():
                return {
                    'success': False,
                    'error': _('Failed to establish connection')
                }
            
            # Obtener información básica
            cursor = self.connection.cursor(dictionary=True)
            
            # Información de la base de datos
            database_info = self._get_database_info(cursor)
            
            # Información de versión
            version_info = self._get_version_info(cursor)
            
            # Test de tablas si se solicita
            tables_count = 0
            if test_tables:
                tables_count = self._test_tables(cursor)
            
            cursor.close()
            
            return {
                'success': True,
                'database_info': database_info,
                'version': version_info,
                'tables_count': tables_count,
                'connection_string': self.config.get_connection_string()
            }
            
        except Error as e:
            error_msg = str(e)
            logger.error(f"Database connection error: {error_msg}")
            
            # Traducir errores comunes
            if "Access denied" in error_msg:
                error_msg = _("Access denied. Check username and password.")
            elif "Can't connect" in error_msg:
                error_msg = _("Cannot connect to server. Check host and port.")
            elif "Unknown database" in error_msg:
                error_msg = _("Database does not exist. Check database name.")
            elif "Connection timed out" in error_msg:
                error_msg = _("Connection timed out. Check network connectivity.")
            
            return {
                'success': False,
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Unexpected error testing connection: {error_msg}")
            return {
                'success': False,
                'error': _("Unexpected error: ") + error_msg
            }
            
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()
    
    def _get_database_info(self, cursor) -> Dict[str, Any]:
        """
        Obtener información de la base de datos
        
        Args:
            cursor: Cursor de MySQL
            
        Returns:
            Dict con información de la base de datos
        """
        try:
            cursor.execute("SELECT DATABASE() as name")
            result = cursor.fetchone()
            
            cursor.execute("""
                SELECT 
                    table_schema as database_name,
                    COUNT(*) as table_count,
                    SUM(data_length + index_length) as size_bytes
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                GROUP BY table_schema
            """)
            stats = cursor.fetchone()
            
            return {
                'name': result['name'] if result else self.config.database_name,
                'table_count': stats['table_count'] if stats else 0,
                'size_bytes': stats['size_bytes'] if stats else 0,
                'size_mb': round((stats['size_bytes'] or 0) / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.warning(f"Error getting database info: {e}")
            return {
                'name': self.config.database_name,
                'table_count': 0,
                'size_bytes': 0,
                'size_mb': 0
            }
    
    def _get_version_info(self, cursor) -> str:
        """
        Obtener información de versión de MySQL
        
        Args:
            cursor: Cursor de MySQL
            
        Returns:
            String con información de versión
        """
        try:
            cursor.execute("SELECT VERSION() as version")
            result = cursor.fetchone()
            return result['version'] if result else 'Unknown'
            
        except Exception as e:
            logger.warning(f"Error getting version info: {e}")
            return 'Unknown'
    
    def _test_tables(self, cursor) -> int:
        """
        Verificar tablas específicas de AdministraNET
        
        Args:
            cursor: Cursor de MySQL
            
        Returns:
            Número de tablas encontradas
        """
        try:
            # Tablas comunes de AdministraNET
            expected_tables = [
                'empresas', 'usuarios', 'clientes', 'proveedores',
                'productos', 'ventas', 'compras', 'inventario',
                'configuracion', 'logs', 'sincronizacion'
            ]
            
            found_tables = []
            for table in expected_tables:
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE() 
                    AND table_name = %s
                """, (table,))
                result = cursor.fetchone()
                if result and result['count'] > 0:
                    found_tables.append(table)
            
            logger.info(f"Found {len(found_tables)} expected tables: {found_tables}")
            return len(found_tables)
            
        except Exception as e:
            logger.warning(f"Error testing tables: {e}")
            return 0
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> Dict[str, Any]:
        """
        Ejecutar consulta SQL
        
        Args:
            query: Consulta SQL
            params: Parámetros de la consulta
            
        Returns:
            Dict con resultado de la consulta
        """
        try:
            if not self.connection or not self.connection.is_connected():
                # Reestablecer conexión si es necesario
                connection_params = self.get_connection_params()
                self.connection = mysql.connector.connect(**connection_params)
            
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                cursor.close()
                return {
                    'success': True,
                    'data': results,
                    'row_count': len(results)
                }
            else:
                self.connection.commit()
                affected_rows = cursor.rowcount
                cursor.close()
                return {
                    'success': True,
                    'affected_rows': affected_rows
                }
                
        except Error as e:
            logger.error(f"Query execution error: {e}")
            # Cerrar cursor si hay error
            if 'cursor' in locals():
                cursor.close()
            return {
                'success': False,
                'error': str(e)
            }
            
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            # Cerrar cursor si hay error
            if 'cursor' in locals():
                cursor.close()
            return {
                'success': False,
                'error': str(e)
            }
    
    def close_connection(self):
        """
        Cerrar conexión a la base de datos
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.connection = None 

    def list_tables(self) -> list:
        """
        Listar todas las tablas de la base de datos
        
        Returns:
            list: Lista de nombres de tablas
        """
        try:
            if not self.connection or not self.connection.is_connected():
                # Reestablecer conexión si es necesario
                connection_params = self.get_connection_params()
                self.connection = mysql.connector.connect(**connection_params)
            
            cursor = self.connection.cursor()
            
            # Obtener todas las tablas
            cursor.execute("SHOW TABLES")
            results = cursor.fetchall()
            cursor.close()
            
            # Extraer nombres de tablas
            tables = [row[0] for row in results]
            
            logger.info(f"Found {len(tables)} tables in database")
            return tables
            
        except Error as e:
            logger.error(f"Error listing tables: {e}")
            raise e
            
        except Exception as e:
            logger.error(f"Unexpected error listing tables: {e}")
            raise e

    def get_table_data(self, table_name: str, limit: int = 1000) -> list:
        """
        Obtener todos los datos de una tabla específica
        
        Args:
            table_name (str): Nombre de la tabla
            limit (int): Límite de registros a obtener
            
        Returns:
            list: Lista de registros de la tabla
        """
        try:
            if not self.connection or not self.connection.is_connected():
                # Reestablecer conexión si es necesario
                connection_params = self.get_connection_params()
                self.connection = mysql.connector.connect(**connection_params)
            
            cursor = self.connection.cursor(dictionary=True)
            
            # Obtener todos los datos de la tabla
            query = f"SELECT * FROM {table_name} LIMIT %s"
            cursor.execute(query, (limit,))
            
            results = cursor.fetchall()
            cursor.close()
            
            logger.info(f"Retrieved {len(results)} records from table {table_name}")
            return results
            
        except Error as e:
            logger.error(f"Error getting table data for {table_name}: {e}")
            raise e
            
        except Exception as e:
            logger.error(f"Unexpected error getting table data for {table_name}: {e}")
            raise e

    def get_table_fields(self, table_name: str) -> list:
        """
        Obtener campos de una tabla específica
        
        Args:
            table_name (str): Nombre de la tabla
            
        Returns:
            list: Lista de nombres de campos
        """
        try:
            with self.get_connection() as connection:
                cursor = connection.cursor(dictionary=True)
                
                # Obtener información de la tabla
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (table_name,))
                
                columns = cursor.fetchall()
                
                # Formatear resultado
                fields = []
                for column in columns:
                    field_info = {
                        'name': column['COLUMN_NAME'],
                        'type': column['DATA_TYPE'],
                        'nullable': column['IS_NULLABLE'] == 'YES',
                        'default': column['COLUMN_DEFAULT'],
                        'comment': column['COLUMN_COMMENT'] or '',
                    }
                    fields.append(field_info)
                
                return fields
                
        except Exception as e:
            logger.error(f"Error getting table fields for {table_name}: {e}")
            raise e 