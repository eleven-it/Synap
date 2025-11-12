"""
Servicio de acceso a base de datos
Wrapper sobre MySQLTool para operaciones comunes
"""
from reports_ai.tools.mysql_tool import MySQLTool

class DatabaseService:
    """Servicio simplificado de acceso a datos"""
    
    def __init__(self):
        self.mysql_tool = MySQLTool()
    
    def execute_query(self, query: str, **kwargs):
        """Ejecuta query y retorna resultados"""
        return self.mysql_tool.execute_query(query, **kwargs)
    
    def get_tables(self):
        """Lista tablas disponibles"""
        return self.mysql_tool.get_schema_info()

