"""
Herramienta MySQL para acceso READ-ONLY a la base de datos de Administranet
Siguiendo las directivas del documento: solo SELECT, sin exponer SQL al usuario
"""
import logging
from typing import Dict, List, Any, Optional
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService

logger = logging.getLogger(__name__)


class MySQLTool:
    """
    Herramienta para ejecutar consultas MySQL de solo lectura
    ESTRICTAMENTE: Solo SELECT, sin DML/DDL
    """
    
    def __init__(self, config: Optional[AdministraNETConfig] = None):
        """
        Inicializa la herramienta MySQL
        
        Args:
            config: Configuración de conexión a administranet
        """
        if config is None:
            # Obtener la primera configuración activa
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                raise ValueError("No se encontró configuración activa de administraNET")
        
        self.config = config
        self.connection_service = AdministraNETConnectionService(config)
        self.connection = None
    
    def _validate_query(self, query: str) -> Dict[str, Any]:
        """
        Valida que la consulta sea READ-ONLY (solo SELECT)
        
        Args:
            query: Query SQL a validar
            
        Returns:
            Dict con resultado de validación
        """
        query_upper = query.strip().upper()
        
        # Palabras prohibidas (DML/DDL)
        forbidden_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
            'GRANT', 'REVOKE', 'TRUNCATE', 'REPLACE', 'MERGE',
            'RENAME', 'CALL', 'EXECUTE', 'EXEC'
        ]
        
        # Verificar que comience con SELECT
        if not query_upper.startswith('SELECT'):
            return {
                'valid': False,
                'error': 'Solo se permiten consultas SELECT'
            }
        
        # Verificar palabras prohibidas
        for keyword in forbidden_keywords:
            if keyword in query_upper:
                return {
                    'valid': False,
                    'error': f'Operación prohibida: {keyword}. Solo lectura permitida.'
                }
        
        return {'valid': True}
    
    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Ejecuta una consulta SELECT de forma segura
        """
        # Normalizar límite (evitar comparaciones int vs None)
        try:
            safe_limit = int(limit) if isinstance(limit, (int, float, str)) and str(limit).isdigit() else 1000
        except Exception:
            safe_limit = 1000
        if safe_limit <= 0:
            safe_limit = 1000
        
        # Validar query
        validation = self._validate_query(query)
        if not validation['valid']:
            logger.warning(f"Query rechazada: {validation['error']}")
            return {
                'success': False,
                'error': validation['error'],
                'data': []
            }
        
        try:
            # Establecer conexión
            connection_params = self.connection_service.get_connection_params()
            import mysql.connector
            self.connection = mysql.connector.connect(**connection_params)
            
            cursor = self.connection.cursor(dictionary=True)
            
            # Aplicar LIMIT si no existe
            if 'LIMIT' not in query.upper():
                query = f"{query.rstrip(';')} LIMIT {min(safe_limit, 1000)}"
            
            # Ejecutar query
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            row_count = len(results)
            
            cursor.close()
            self.connection.close()
            
            # Retornar resultados SIN exponer el SQL
            return {
                'success': True,
                'data': results,
                'row_count': row_count,
                'source': 'administranet_mysql',  # Descripción funcional
                'limited': row_count >= min(safe_limit, 1000)
            }
        except Exception as e:
            logger.error(f"Error ejecutando query MySQL: {e}")
            if self.connection:
                self.connection.close()
            
            return {
                'success': False,
                'error': 'Error al consultar datos de Administranet',
                'data': []
            }
    
    def get_schema_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información del schema (estructura de tablas)
        Útil para que el agente conozca las tablas disponibles
        
        Args:
            table_name: Nombre de tabla específica (opcional)
            
        Returns:
            Dict con información del schema (nombres funcionales, no técnicos en respuesta)
        """
        try:
            connection_params = self.connection_service.get_connection_params()
            import mysql.connector
            self.connection = mysql.connector.connect(**connection_params)
            
            cursor = self.connection.cursor(dictionary=True)
            
            if table_name:
                # Información de una tabla específica
                query = """
                    SELECT 
                        COLUMN_NAME as column_name,
                        DATA_TYPE as data_type,
                        IS_NULLABLE as is_nullable
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """
                cursor.execute(query, (self.config.database_name, table_name))
            else:
                # Listar todas las tablas
                query = """
                    SELECT 
                        TABLE_NAME as table_name,
                        TABLE_TYPE as table_type
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = %s
                    ORDER BY TABLE_NAME
                """
                cursor.execute(query, (self.config.database_name,))
            
            results = cursor.fetchall()
            cursor.close()
            self.connection.close()
            
            return {
                'success': True,
                'data': results
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo schema: {e}")
            if self.connection:
                self.connection.close()
            
            return {
                'success': False,
                'error': 'Error al obtener estructura de datos',
                'data': []
            }
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión a MySQL
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            test_result = self.connection_service.test_connection()
            return test_result.get('success', False)
        except Exception as e:
            logger.error(f"Error probando conexión MySQL: {e}")
            return False

