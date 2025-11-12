"""
Schema Analyzer para AdministraNET MySQL

Analiza el schema completo de la base de datos para proporcionar
información detallada al Data Analyst Agent.

Incluye:
- Estructura completa de tablas (columnas, tipos, índices)
- Relaciones (FK formales + heurísticas)
- Estadísticas de columnas (cardinalidad, valores únicos)
- Comentarios y documentación
"""
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import hashlib

from administraNET_integration.services.connection_service import AdministraNETConnectionService
from administraNET_integration.models import AdministraNETConfig

logger = logging.getLogger(__name__)


class SchemaAnalyzer:
    """
    Analiza el schema completo de MySQL de AdministraNET
    """
    
    def __init__(self):
        # Obtener configuración de administraNET
        self.config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not self.config:
            raise ValueError("No se encontró configuración activa de administraNET")
        
        self.connection_service = AdministraNETConnectionService(self.config)
        self.db_name = self.config.database_name
        self.schema_cache = {}
        self.cache_timestamp = None
        self.cache_duration = timedelta(hours=1)  # Cache por 1 hora
    
    def get_complete_schema(self, force_refresh: bool = False) -> Dict:
        """
        Obtiene el schema completo con todos los detalles
        
        Args:
            force_refresh: Forzar actualización del caché
        
        Returns:
            Dict con estructura completa del schema
        """
        # Verificar caché
        if not force_refresh and self._is_cache_valid():
            logger.info("[SchemaAnalyzer] 📦 Usando schema en caché")
            return self.schema_cache
        
        logger.info("[SchemaAnalyzer] 🔍 Analizando schema completo...")
        start_time = datetime.now()
        
        self.schema_cache = {
            'tables': {},
            'relationships': [],
            'column_statistics': {},
            'indexes': {},
            'metadata': {
                'analyzed_at': datetime.now().isoformat(),
                'total_tables': 0,
                'total_columns': 0,
                'total_fks': 0
            }
        }
        
        try:
            # Conectar a MySQL
            import mysql.connector
            connection_params = self.connection_service.get_connection_params()
            conn = mysql.connector.connect(**connection_params)
            
            try:
                # 1. Obtener todas las tablas
                tables = self._get_all_tables(conn)
                self.schema_cache['metadata']['total_tables'] = len(tables)
                
                logger.info(f"[SchemaAnalyzer] 📊 Tablas encontradas: {len(tables)}")
                
                # 2. Para cada tabla, analizar estructura
                for table_name in tables:
                    logger.debug(f"[SchemaAnalyzer] Analizando tabla: {table_name}")
                    
                    table_info = self._analyze_table(conn, table_name)
                    if table_info:
                        self.schema_cache['tables'][table_name] = table_info
                        self.schema_cache['metadata']['total_columns'] += len(table_info['columns'])
                
                # 3. Descubrir relaciones (FK formales + heurísticas)
                logger.info("[SchemaAnalyzer] 🔗 Descubriendo relaciones...")
                relationships = self._discover_relationships(conn)
                self.schema_cache['relationships'] = relationships
                self.schema_cache['metadata']['total_fks'] = len([r for r in relationships if r['type'] == 'FOREIGN_KEY'])
                
                # 4. Calcular estadísticas de columnas (para optimización)
                logger.info("[SchemaAnalyzer] 📈 Calculando estadísticas de columnas...")
                self.schema_cache['column_statistics'] = self._calculate_column_statistics(conn)
                
                # 5. Guardar timestamp de caché
                self.cache_timestamp = datetime.now()
                
                duration = (datetime.now() - start_time).total_seconds()
                logger.info(f"[SchemaAnalyzer] ✅ Schema analizado en {duration:.2f}s")
                
                return self.schema_cache
                
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"[SchemaAnalyzer] ❌ Error analizando schema: {e}", exc_info=True)
            return self.schema_cache
    
    def _get_all_tables(self, conn) -> List[str]:
        """
        Obtiene lista de todas las tablas en la BD
        """
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        cursor.close()
        return sorted(tables)
    
    def _analyze_table(self, conn, table_name: str) -> Optional[Dict]:
        """
        Analiza una tabla específica
        
        Args:
            conn: Conexión MySQL
            table_name: Nombre de la tabla
        
        Returns:
            Dict con estructura completa de la tabla
        """
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 1. Obtener columnas con comentarios
            cursor.execute(f"SHOW FULL COLUMNS FROM `{table_name}`")
            columns = cursor.fetchall()
            
            # 2. Obtener información adicional de la tabla
            cursor.execute(f"""
                SELECT 
                    TABLE_COMMENT,
                    TABLE_ROWS as estimated_rows,
                    AVG_ROW_LENGTH,
                    DATA_LENGTH,
                    INDEX_LENGTH
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = '{table_name}'
            """)
            meta = cursor.fetchone()
            
            # 3. Obtener índices
            cursor.execute(f"SHOW INDEX FROM `{table_name}`")
            indexes_raw = cursor.fetchall()
            
            cursor.close()
            
            # 4. Enriquecer información de columnas
            enriched_columns = []
            for col in columns:
                # Determinar tipo base y tamaño
                col_type = col['Type']
                col_type_lower = col_type.lower()
                
                type_base = 'unknown'
                max_length = None
                precision = None
                scale = None
                
                if 'int' in col_type_lower:
                    type_base = 'integer'
                elif 'varchar' in col_type_lower or 'char' in col_type_lower:
                    type_base = 'string'
                    # Extraer longitud: varchar(100) -> 100
                    import re
                    length_match = re.search(r'\((\d+)\)', col_type)
                    if length_match:
                        max_length = int(length_match.group(1))
                elif 'decimal' in col_type_lower or 'numeric' in col_type_lower:
                    type_base = 'decimal'
                    # Extraer precisión y escala: decimal(10,2) -> precision=10, scale=2
                    import re
                    prec_match = re.search(r'\((\d+),(\d+)\)', col_type)
                    if prec_match:
                        precision = int(prec_match.group(1))
                        scale = int(prec_match.group(2))
                elif 'datetime' in col_type_lower or 'timestamp' in col_type_lower:
                    type_base = 'datetime'
                elif 'date' in col_type_lower:
                    type_base = 'date'
                elif 'text' in col_type_lower:
                    type_base = 'text'
                elif 'bit' in col_type_lower or 'tinyint' in col_type_lower and 'unsigned' in col_type_lower:
                    type_base = 'boolean'
                elif 'blob' in col_type_lower:
                    type_base = 'blob'
                
                enriched_col = {
                    'name': col['Field'],
                    'type': {
                        'raw': col_type,
                        'base': type_base,
                        'max_length': max_length,
                        'precision': precision,
                        'scale': scale
                    },
                    'nullable': col['Null'] == 'YES',
                    'default': col['Default'],
                    'key_info': {
                        'is_primary': col['Key'] == 'PRI',
                        'is_foreign': col['Key'] == 'MUL',
                        'is_unique': col['Key'] == 'UNI',
                        'key_name': None
                    },
                    'extra': col['Extra'],
                    'comment': col['Comment'],
                    'auto_increment': 'auto_increment' in col['Extra'].lower()
                }
                
                enriched_columns.append(enriched_col)
            
            # 5. Procesar índices
            indexes = {}
            for idx in indexes_raw:
                idx_name = idx['Key_name']
                if idx_name not in indexes:
                    indexes[idx_name] = {
                        'name': idx_name,
                        'columns': [],
                        'unique': idx['Non_unique'] == 0,
                        'type': idx.get('Index_type', 'BTREE')
                    }
                indexes[idx_name]['columns'].append({
                    'column': idx['Column_name'],
                    'subpart': idx.get('Sub_part'),
                    'collation': idx.get('Collation'),
                    'cardinality': idx.get('Cardinality')
                })
            
            # 6. Construir información completa
            table_info = {
                'name': table_name,
                'columns': enriched_columns,
                'indexes': list(indexes.values()),
                'primary_key': [c['name'] for c in enriched_columns if c['key_info']['is_primary']],
                'estimated_rows': meta.get('estimated_rows', 0),
                'size': {
                    'data_length': meta.get('DATA_LENGTH', 0),
                    'index_length': meta.get('INDEX_LENGTH', 0),
                    'avg_row_length': meta.get('AVG_ROW_LENGTH', 0)
                },
                'comment': meta.get('TABLE_COMMENT', ''),
                'engine': 'InnoDB'  # Asumimos InnoDB para MySQL 5.7
            }
            
            return table_info
            
        except Exception as e:
            logger.error(f"[SchemaAnalyzer] Error analizando tabla {table_name}: {e}")
            return None
    
    def _discover_relationships(self, conn) -> List[Dict]:
        """
        Descubre relaciones entre tablas
        
        1. FK formales desde INFORMATION_SCHEMA
        2. Heurísticas por nombres de columnas
        3. Heurísticas por tipos compatibles
        """
        relationships = []
        
        try:
            cursor = conn.cursor(dictionary=True)
            
            # 1. FK formales desde MySQL
            cursor.execute("""
                SELECT 
                    TABLE_NAME as from_table,
                    COLUMN_NAME as from_column,
                    REFERENCED_TABLE_NAME as to_table,
                    REFERENCED_COLUMN_NAME as to_column,
                    CONSTRAINT_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE 
                    TABLE_SCHEMA = DATABASE()
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                    AND REFERENCED_COLUMN_NAME IS NOT NULL
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """)
            
            for fk in cursor.fetchall():
                relationships.append({
                    'from_table': fk['from_table'],
                    'from_column': fk['from_column'],
                    'to_table': fk['to_table'],
                    'to_column': fk['to_column'],
                    'type': 'FOREIGN_KEY',
                    'confidence': 1.0,
                    'source': 'DDL',
                    'constraint_name': fk['CONSTRAINT_NAME']
                })
            
            # 2. Heurísticas por nombres similares (si no hay FK formales)
            if not relationships:
                logger.info("[SchemaAnalyzer] 🔍 Aplicando heurísticas para descubrir relaciones...")
                relationships.extend(self._heuristic_relationships(conn))
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"[SchemaAnalyzer] Error descubriendo relaciones: {e}")
        
        return relationships
    
    def _heuristic_relationships(self, conn) -> List[Dict]:
        """
        Descubre relaciones usando heurísticas
        
        Estrategia:
        1. Buscar columnas con prefijos/sufijos comunes: IdCliente, CodCliente, ClienteID, etc.
        2. Verificar que exista tabla de destino con columna compatible
        3. Validar compatibilidad de tipos
        """
        heuristics = []
        
        try:
            # Obtener todas las tablas y sus columnas
            all_tables = self.schema_cache['tables']
            
            for from_table, from_table_info in all_tables.items():
                for column in from_table_info['columns']:
                    col_name = column['name']
                    
                    # Buscar patrones de FK
                    # Ejemplo: IdCliente -> cliente.id
                    potential_targets = []
                    
                    # Patrón 1: Id<Entity> -> <entity>.id
                    if col_name.startswith('Id') and len(col_name) > 2:
                        entity_name = col_name[2:].lower()
                        potential_targets.append({
                            'table': entity_name,
                            'column': 'Id'
                        })
                    
                    # Patrón 2: Cod<Entity> -> <entity>.Codigo
                    elif col_name.startswith('Cod') and len(col_name) > 3:
                        entity_name = col_name[3:].lower()
                        potential_targets.append({
                            'table': entity_name,
                            'column': col_name  # Mantener mismo nombre
                        })
                    
                    # Patrón 3: <entity>Id -> <entity>.id
                    elif col_name.endswith('Id') and len(col_name) > 2:
                        entity_name = col_name[:-2].lower()
                        potential_targets.append({
                            'table': entity_name,
                            'column': 'Id'
                        })
                    
                    # Buscar tabla de destino
                    for target in potential_targets:
                        target_table_name = None
                        
                        # Buscar coincidencia exacta o similar
                        for table_name in all_tables.keys():
                            if table_name.lower() == target['table'] or \
                               table_name.lower().startswith(target['table']) or \
                               target['table'].startswith(table_name.lower()):
                                target_table_name = table_name
                                break
                        
                        if target_table_name and target_table_name in all_tables:
                            # Verificar que existe la columna de destino
                            target_table = all_tables[target_table_name]
                            target_column_name = target['column']
                            
                            for target_col in target_table['columns']:
                                if target_col['name'] == target_column_name or \
                                   target_col['key_info']['is_primary'] or \
                                   target_col['key_info']['is_unique']:
                                    
                                    # Verificar compatibilidad de tipos
                                    if self._are_types_compatible(column, target_col):
                                        heuristics.append({
                                            'from_table': from_table,
                                            'from_column': col_name,
                                            'to_table': target_table_name,
                                            'to_column': target_col['name'],
                                            'type': 'HEURISTIC',
                                            'confidence': 0.75,  # Media confianza para heurísticas
                                            'source': 'naming_pattern',
                                            'pattern': col_name
                                        })
                    
                    # Solo una relación por columna
                    if len([h for h in heuristics if h['from_table'] == from_table and h['from_column'] == col_name]) >= 1:
                        break
        
        except Exception as e:
            logger.error(f"[SchemaAnalyzer] Error en heurísticas: {e}")
        
        return heuristics[:50]  # Limitar a 50 para evitar explosión combinatoria
    
    def _are_types_compatible(self, col1: Dict, col2: Dict) -> bool:
        """
        Verifica si dos columnas tienen tipos compatibles para JOIN
        """
        type1 = col1['type']['base']
        type2 = col2['type']['base']
        
        # Tipos exactamente iguales
        if type1 == type2:
            return True
        
        # Compatibilidades comunes
        compatible_groups = [
            ['integer', 'bigint', 'smallint', 'tinyint'],
            ['decimal', 'double', 'float'],
            ['string', 'varchar', 'char', 'text'],
            ['date', 'datetime', 'timestamp']
        ]
        
        for group in compatible_groups:
            if type1 in group and type2 in group:
                return True
        
        return False
    
    def _calculate_column_statistics(self, conn) -> Dict[str, Dict]:
        """
        Calcula estadísticas básicas de columnas para optimización
        
        Returns:
            Dict {table.column: {distinct_count, null_count, most_common_values}}
        """
        stats = {}
        
        try:
            # Obtener stats solo para tablas principales (evitar todas las tablas)
            main_tables = list(self.schema_cache['tables'].keys())[:20]  # Solo primeras 20
            
            for table_name in main_tables:
                table_info = self.schema_cache['tables'].get(table_name)
                if not table_info:
                    continue
                
                for column in table_info['columns'][:5]:  # Solo primeras 5 columnas por tabla
                    column_name = column['name']
                    
                    try:
                        cursor = conn.cursor(dictionary=True)
                        
                        # COUNT(DISTINCT) para cardinalidad
                        cursor.execute(f"""
                            SELECT COUNT(DISTINCT `{column_name}`) as distinct_count
                            FROM `{table_name}`
                        """)
                        distinct_count = cursor.fetchone()['distinct_count']
                        
                        # COUNT(*) para total
                        cursor.execute(f"SELECT COUNT(*) as total_count FROM `{table_name}`")
                        total_count = cursor.fetchone()['total_count']
                        
                        # NULL count
                        cursor.execute(f"""
                            SELECT COUNT(*) as null_count
                            FROM `{table_name}`
                            WHERE `{column_name}` IS NULL
                        """)
                        null_count = cursor.fetchone()['null_count']
                        
                        stats[f"{table_name}.{column_name}"] = {
                            'distinct_count': distinct_count,
                            'null_count': null_count,
                            'total_count': total_count,
                            'cardinality': distinct_count / total_count if total_count > 0 else 0
                        }
                        
                        cursor.close()
                        
                    except Exception as e:
                        # Ignorar errores en stats individuales
                        logger.debug(f"Error calculando stats para {table_name}.{column_name}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"[SchemaAnalyzer] Error calculando estadísticas: {e}")
        
        return stats
    
    def _is_cache_valid(self) -> bool:
        """
        Verifica si el caché del schema es válido
        """
        if not self.schema_cache or not self.cache_timestamp:
            return False
        
        elapsed = datetime.now() - self.cache_timestamp
        return elapsed < self.cache_duration
    
    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """
        Obtiene información detallada de una tabla específica
        
        Args:
            table_name: Nombre de la tabla
        
        Returns:
            Dict con información de la tabla o None si no existe
        """
        if not self.schema_cache:
            self.get_complete_schema()
        
        return self.schema_cache.get('tables', {}).get(table_name)
    
    def find_related_tables(self, table_name: str) -> List[Dict]:
        """
        Encuentra tablas relacionadas con una tabla dada
        
        Args:
            table_name: Nombre de la tabla
        
        Returns:
            Lista de relaciones
        """
        if not self.schema_cache:
            self.get_complete_schema()
        
        relationships = self.schema_cache.get('relationships', [])
        
        return [
            r for r in relationships
            if r['from_table'] == table_name or r['to_table'] == table_name
        ]
    
    def suggest_join_path(self, from_table: str, to_table: str) -> List[str]:
        """
        Sugiere ruta de JOIN entre dos tablas
        
        Args:
            from_table: Tabla origen
            to_table: Tabla destino
        
        Returns:
            Lista de tablas intermedias: [tabla1, tabla2, ..., tablaDestino]
        """
        # Implementación simple: BFS para encontrar shortest path
        relationships = self.schema_cache.get('relationships', [])
        
        # Crear grafo de relaciones
        graph = {}
        for rel in relationships:
            from_t = rel['from_table']
            to_t = rel['to_table']
            
            if from_t not in graph:
                graph[from_t] = []
            graph[from_t].append(to_t)
        
        # BFS para encontrar camino
        from collections import deque
        
        queue = deque([(from_table, [from_table])])
        visited = {from_table}
        
        while queue:
            current_table, path = queue.popleft()
            
            if current_table == to_table:
                return path
            
            for neighbor in graph.get(current_table, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        # No se encontró camino
        return [from_table, to_table]  # Fallback: join directo


# Función helper para instanciar fácilmente
def get_schema_analyzer() -> SchemaAnalyzer:
    """
    Obtiene una instancia del Schema Analyzer
    """
    return SchemaAnalyzer()

