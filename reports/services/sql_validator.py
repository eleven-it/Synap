"""
Validador SQL semántico para expresiones de reportes declarativos.

Este módulo valida expresiones SQL de métricas, dimensiones y filtros
contra el esquema real de MySQL, detectando columnas inexistentes y
bloqueando patrones peligrosos.
"""
from __future__ import annotations

from typing import Dict, List, Set, Optional, Tuple, Any
import logging
import re
from functools import lru_cache

from .connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)

# Palabras peligrosas que no deben aparecer en expresiones SQL
DANGEROUS_KEYWORDS = {
    'DROP', 'TRUNCATE', 'INSERT', 'UPDATE', 'DELETE', 'ALTER', 'CREATE',
    'EXEC', 'EXECUTE', 'CALL', 'SHOW', 'GRANT', 'REVOKE', 'FLUSH',
    'LOCK', 'UNLOCK', 'KILL', 'SHUTDOWN', '--', '/*', '*/', ';'
}

# Palabras clave SQL permitidas (para evitar falsos positivos)
ALLOWED_KEYWORDS = {
    'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING',
    'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON', 'AS', 'AND', 'OR',
    'SUM', 'COUNT', 'AVG', 'MAX', 'MIN', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END',
    'COALESCE', 'NULLIF', 'IFNULL', 'ISNULL', 'DATE_FORMAT', 'YEAR', 'MONTH', 'DAY',
    'CAST', 'CONVERT', 'DISTINCT', 'LIMIT', 'OFFSET'
}


class SQLValidator:
    """
    Validador de expresiones SQL contra esquema MySQL.
    
    Valida que las expresiones no contengan comandos peligrosos y que
    las columnas referenciadas existan en las tablas especificadas.
    """
    
    def __init__(self, connection_pool=None):
        """
        Inicializa el validador.
        
        Args:
            connection_pool: Pool de conexiones MySQL (opcional, se obtiene automáticamente si None)
        """
        self.connection_pool = connection_pool or get_mysql_pool()
        self._column_cache: Dict[str, Set[str]] = {}  # Cache de columnas por tabla
    
    def validate_expression(
        self,
        expression: str,
        datasource: str,
        joins: Optional[List[Dict[str, str]]] = None,
        allowed_tables: Optional[List[str]] = None,
        base_empresa: Optional[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Valida una expresión SQL.
        
        Args:
            expression: Expresión SQL a validar
            datasource: Tabla principal (puede incluir alias, ej: "cuentacliente cc")
            joins: Lista de JOINs opcionales
            allowed_tables: Lista de tablas permitidas (opcional)
            base_empresa: Base de datos MySQL para validar columnas (opcional)
            
        Returns:
            Tupla (es_válido, lista_de_errores)
        """
        errors = []
        
        if not expression or not isinstance(expression, str):
            return False, ["Expresión vacía o inválida"]
        
        # 1. Validar palabras peligrosas (siempre crítico, no depende de base_empresa)
        dangerous_errors = self._check_dangerous_keywords(expression)
        if dangerous_errors:
            errors.extend(dangerous_errors)
            return False, errors  # Si hay palabras peligrosas, no continuar
        
        # 2. Extraer tablas y alias
        main_table, main_alias = self._parse_table_alias(datasource)
        # Alias por defecto de la tabla base si no se especifica
        # IMPORTANTE: Usar la misma lógica que execution_engine.py para consistencia
        # execution_engine.py usa: table_name[0].lower() (primera letra)
        if not main_alias:
            main_alias = main_table[0].lower() if main_table else "c"
        tables = {main_table: main_alias or main_table}
        
        # También agregar alias alternativos comunes para compatibilidad
        # Si el alias es 'c', también aceptar 'cc' y 'cu' como variaciones comunes
        if main_alias == 'c':
            # No agregar directamente, pero reconocer en la validación
            pass
        
        if joins:
            for join_def in joins:
                if isinstance(join_def, dict):
                    join_table = join_def.get("table", "")
                    if join_table:
                        # Extraer nombre de tabla (puede venir con o sin alias en el string)
                        join_table_clean, join_alias_from_string = self._parse_table_alias(join_table)
                        
                        # El alias puede estar en el campo "alias" del JOIN o en el string
                        join_alias = join_def.get("alias", "")
                        if not join_alias:
                            # Si no hay alias en el campo separado, usar el del string o generar uno
                            if join_alias_from_string:
                                join_alias = join_alias_from_string
                            else:
                                # Generar alias por defecto
                                words = join_table_clean.split('_')
                                if len(words) > 1:
                                    join_alias = ''.join(w[0] for w in words if w)[:3].lower()
                                else:
                                    join_alias = join_table_clean[:2].lower()
                        
                        tables[join_table_clean] = join_alias
        
        # 3. Extraer referencias a columnas
        column_refs = self._extract_column_references(expression)
        
        # 4. Validar que las columnas existan (solo si tenemos base_empresa)
        if base_empresa:
            for table_name, alias, column_name in column_refs:
                # Determinar qué tabla usar
                target_table = None
                if alias:
                    # Buscar tabla por alias
                    for t_name, t_alias in tables.items():
                        if t_alias == alias:
                            target_table = t_name
                            break
                    
                    # Si no se encuentra, intentar alias alternativos comunes
                    # Para compatibilidad con expresiones que usan 'cc' o 'cu' cuando el alias real es 'c'
                    # También aceptar 'cp' para comp_ped cuando el alias principal es 'c'
                    if not target_table and main_table:
                        # Si el alias principal es 'c', aceptar también 'cc', 'cu' y 'cp' como variaciones
                        if main_alias == 'c' and alias in ['cc', 'cu', 'cp']:
                            target_table = main_table
                        # Si el alias principal es 'cu', aceptar también 'cc' y 'c' como variaciones
                        elif main_alias == 'cu' and alias in ['cc', 'c']:
                            target_table = main_table
                        # Si el alias principal es 'cc', aceptar también 'cu' y 'c' como variaciones
                        elif main_alias == 'cc' and alias in ['cu', 'c']:
                            target_table = main_table
                        # Si el alias principal es 'cp', aceptar también 'c' como variación (comp_ped)
                        elif main_alias == 'cp' and alias == 'c':
                            target_table = main_table
                else:
                    # Sin alias, usar tabla principal
                    target_table = main_table
                
                if not target_table:
                    errors.append(f"Columna '{column_name}' referencia alias '{alias}' desconocido (alias principal: '{main_alias}')")
                    continue
                
                # Validar que la columna exista
                if not self._column_exists(target_table, column_name, base_empresa):
                    errors.append(
                        f"Columna '{column_name}' no existe en tabla '{target_table}' "
                        f"(referenciada como '{alias}.{column_name}' si alias, o '{column_name}' si no)"
                    )
        
        # 5. Validar tablas permitidas (si se especificó)
        if allowed_tables:
            for table_name in tables.keys():
                if table_name not in allowed_tables:
                    errors.append(f"Tabla '{table_name}' no está en la lista de tablas permitidas")
        
        return len(errors) == 0, errors
    
    def _check_dangerous_keywords(self, expression: str) -> List[str]:
        """
        Verifica si la expresión contiene palabras peligrosas.
        
        Args:
            expression: Expresión SQL
            
        Returns:
            Lista de errores encontrados
        """
        errors = []
        expression_upper = expression.upper()
        
        for keyword in DANGEROUS_KEYWORDS:
            # Buscar palabra completa (no parte de otra palabra)
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, expression_upper):
                errors.append(f"Expresión contiene palabra peligrosa: '{keyword}'")
        
        return errors
    
    def _parse_table_alias(self, table_spec: str) -> Tuple[str, Optional[str]]:
        """
        Parsea una especificación de tabla que puede incluir alias.
        
        Ejemplos:
            "cuentacliente" -> ("cuentacliente", None)
            "cuentacliente cc" -> ("cuentacliente", "cc")
            "cuentacliente AS cc" -> ("cuentacliente", "cc")
        
        Args:
            table_spec: Especificación de tabla
            
        Returns:
            Tupla (nombre_tabla, alias)
        """
        table_spec = table_spec.strip()
        
        # Buscar "AS" o espacio como separador
        if ' AS ' in table_spec.upper():
            parts = re.split(r'\s+AS\s+', table_spec, flags=re.IGNORECASE)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        elif ' ' in table_spec:
            parts = table_spec.split(None, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        
        return table_spec, None
    
    def _extract_column_references(self, expression: str) -> List[Tuple[str, Optional[str], str]]:
        """
        Extrae referencias a columnas de una expresión SQL.
        
        Busca patrones como:
            - nombre_columna
            - alias.nombre_columna
            - tabla.nombre_columna
        
        Args:
            expression: Expresión SQL
            
        Returns:
            Lista de tuplas (tabla, alias, columna)
        """
        references = []
        
        # Patrón para alias.columna o tabla.columna
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
        
        for match in re.finditer(pattern, expression):
            prefix = match.group(1)
            column = match.group(2)
            
            # Ignorar si es una función conocida o palabra clave
            if prefix.upper() in ALLOWED_KEYWORDS:
                continue
            
            references.append((None, prefix, column))
        
        # También buscar columnas sin prefijo (más complejo, puede dar falsos positivos)
        # Por ahora, solo buscamos referencias con punto
        
        return references
    
    def _column_exists(self, table_name: str, column_name: str, base_empresa: Optional[str] = None) -> bool:
        """
        Verifica si una columna existe en una tabla.
        
        Args:
            table_name: Nombre de la tabla
            column_name: Nombre de la columna
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            True si la columna existe, False en caso contrario
        """
        if not base_empresa:
            # Sin base_empresa, no podemos validar, retornar True para no bloquear
            return True
        
        cache_key = f"{table_name}.{column_name}"
        
        # Verificar cache
        if table_name in self._column_cache:
            return column_name in self._column_cache[table_name]
        
        # Obtener columnas de la tabla
        columns = self.get_table_columns(table_name, base_empresa)
        return column_name in columns
    
    def get_table_columns(self, table_name: str, base_empresa: Optional[str] = None) -> Set[str]:
        """
        Obtiene las columnas de una tabla desde MySQL.
        
        Args:
            table_name: Nombre de la tabla
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            Conjunto de nombres de columnas
        """
        # Verificar cache
        if table_name in self._column_cache:
            return self._column_cache[table_name]
        
        columns = set()
        
        try:
            # Si no hay base_empresa, no podemos validar
            if not base_empresa:
                logger.warning(f"No se puede validar tabla '{table_name}' sin base_empresa")
                return columns
            
            # Obtener conexión
            with self.connection_pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                
                try:
                    # Obtener columnas
                    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        if row and len(row) > 0:
                            column_name = row[0]
                            columns.add(column_name)
                    
                    # Guardar en cache
                    self._column_cache[table_name] = columns
                    
                except Exception as e:
                    logger.warning(f"Error obteniendo columnas de '{table_name}': {e}")
                    # Retornar conjunto vacío en caso de error
        except Exception as e:
            logger.warning(f"Error conectando a MySQL para validar '{table_name}': {e}")
        
        return columns
    
    def clear_cache(self):
        """Limpia el cache de columnas."""
        self._column_cache.clear()


# Instancia global del validador (opcional, para reutilizar cache)
_global_validator: Optional[SQLValidator] = None


def get_sql_validator() -> SQLValidator:
    """
    Obtiene una instancia del validador SQL (singleton para cache compartido).
    
    Returns:
        Instancia de SQLValidator
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = SQLValidator()
    return _global_validator
