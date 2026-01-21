"""
Servicio semántico para obtener metadata de tablas y campos de MySQL.

Este módulo proporciona información sobre las tablas disponibles, sus campos,
tipos de datos y relaciones posibles para el Builder Visual.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
import logging
from functools import lru_cache

from django.conf import settings
from .connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)


@dataclass
class SemanticField:
    """Campo de una tabla con metadata semántica."""
    name: str
    data_type: str  # MySQL type: INT, VARCHAR, DECIMAL, DATE, DATETIME, etc.
    is_nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    referenced_table: Optional[str] = None
    referenced_field: Optional[str] = None
    description: Optional[str] = None
    
    # Agregaciones válidas inferidas del tipo
    valid_aggregations: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Inferir agregaciones válidas basadas en el tipo de dato."""
        if not self.valid_aggregations:
            self.valid_aggregations = self._infer_aggregations()
    
    def _infer_aggregations(self) -> List[str]:
        """Infiere agregaciones válidas según el tipo de dato."""
        type_upper = self.data_type.upper()
        
        # Tipos numéricos
        if any(t in type_upper for t in ['INT', 'DECIMAL', 'FLOAT', 'DOUBLE', 'NUMERIC']):
            return ['SUM', 'AVG', 'MAX', 'MIN', 'COUNT']
        
        # Tipos de fecha
        if any(t in type_upper for t in ['DATE', 'DATETIME', 'TIMESTAMP']):
            return ['MIN', 'MAX', 'COUNT']
        
        # Tipos de texto
        if any(t in type_upper for t in ['VARCHAR', 'CHAR', 'TEXT']):
            return ['COUNT', 'COUNT DISTINCT']
        
        # Por defecto, solo COUNT
        return ['COUNT']


@dataclass
class SemanticRelationship:
    """Relación entre tablas (para JOINs)."""
    from_table: str
    from_field: str
    to_table: str
    to_field: str
    relationship_type: str = "ONE_TO_MANY"  # ONE_TO_MANY, ONE_TO_ONE, MANY_TO_MANY
    description: Optional[str] = None
    confidence: float = 1.0  # Confianza de la relación (1.0 = FK explícita, <1.0 = inferida)
    source: str = "foreign_key"  # "foreign_key" | "heuristic"
    label: Optional[str] = None  # Nombre amigable para la tabla destino
    cardinality: Optional[str] = None  # "N:1", "1:1", "1:N", "N:M"


@dataclass
class SemanticDatasource:
    """Fuente de datos (tabla) con metadata completa."""
    name: str
    description: Optional[str] = None
    fields: List[SemanticField] = field(default_factory=list)
    relationships: List[SemanticRelationship] = field(default_factory=list)
    estimated_rows: Optional[int] = None


class SemanticService:
    """
    Servicio para obtener metadata semántica de tablas MySQL.
    
    Proporciona información sobre tablas, campos, tipos y relaciones
    para facilitar la construcción visual de reportes.
    """
    
    # Cache simple en memoria (puede mejorarse con Redis)
    _cache: Dict[str, Any] = {}
    _cache_ttl: int = 3600  # 1 hora
    
    # Tablas conocidas del sistema (puede expandirse)
    KNOWN_TABLES = [
        'cuentacliente',
        'caja',
        'productos',
        'sucursales',
        'punto_venta',
        'clientes',
        'proveedores',
        'articulos',
        'movimientos',
    ]
    
    @classmethod
    def list_datasources(cls, base_empresa: Optional[str] = None) -> List[SemanticDatasource]:
        """
        Lista todas las tablas disponibles como fuentes de datos.
        
        Args:
            base_empresa: Base de datos MySQL (opcional, si no se proporciona, retorna tablas conocidas)
            
        Returns:
            Lista de SemanticDatasource con información básica
        """
        cache_key = f"datasources_{base_empresa or 'default'}"
        
        # Verificar cache
        if cache_key in cls._cache:
            logger.debug(f"📦 Cache hit para {cache_key}")
            return cls._cache[cache_key]
        
        datasources = []
        
        if base_empresa:
            # Obtener tablas reales de MySQL
            try:
                pool = get_mysql_pool()
                with pool.get_connection(base_empresa) as conn:
                    cursor = conn.cursor()
                    
                    # Obtener lista de tablas
                    cursor.execute("""
                        SELECT TABLE_NAME, TABLE_COMMENT
                        FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA = %s
                        AND TABLE_TYPE = 'BASE TABLE'
                        ORDER BY TABLE_NAME
                    """, (base_empresa,))
                    
                    tables = cursor.fetchall()
                    
                    for table_name, table_comment in tables:
                        datasources.append(SemanticDatasource(
                            name=table_name,
                            description=table_comment or f"Tabla {table_name}",
                            fields=[],  # Se cargan bajo demanda
                            relationships=[]  # Se cargan bajo demanda
                        ))
                    
                    cursor.close()
                    
            except Exception as e:
                logger.error(f"❌ Error obteniendo tablas de {base_empresa}: {e}")
                # Fallback a tablas conocidas
                for table_name in cls.KNOWN_TABLES:
                    datasources.append(SemanticDatasource(
                        name=table_name,
                        description=f"Tabla {table_name}",
                        fields=[],
                        relationships=[]
                    ))
        else:
            # Sin base_empresa, retornar tablas conocidas
            for table_name in cls.KNOWN_TABLES:
                datasources.append(SemanticDatasource(
                    name=table_name,
                    description=f"Tabla {table_name}",
                    fields=[],
                    relationships=[]
                ))
        
        # Guardar en cache
        cls._cache[cache_key] = datasources
        
        logger.info(f"✅ {len(datasources)} datasources encontradas")
        return datasources
    
    @classmethod
    def get_fields(cls, datasource_name: str, base_empresa: Optional[str] = None) -> List[SemanticField]:
        """
        Obtiene los campos de una tabla con metadata completa.
        
        Args:
            datasource_name: Nombre de la tabla
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            Lista de SemanticField con información completa
        """
        cache_key = f"fields_{datasource_name}_{base_empresa or 'default'}"
        
        # Verificar cache
        if cache_key in cls._cache:
            logger.debug(f"📦 Cache hit para {cache_key}")
            return cls._cache[cache_key]
        
        fields = []
        
        if base_empresa:
            try:
                pool = get_mysql_pool()
                with pool.get_connection(base_empresa) as conn:
                    cursor = conn.cursor()
                    
                    # Obtener información de columnas
                    cursor.execute("""
                        SELECT 
                            COLUMN_NAME,
                            DATA_TYPE,
                            COLUMN_TYPE,
                            IS_NULLABLE,
                            COLUMN_KEY,
                            COLUMN_COMMENT,
                            EXTRA
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s
                        AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION
                    """, (base_empresa, datasource_name))
                    
                    columns = cursor.fetchall()
                    
                    # Obtener claves primarias
                    cursor.execute("""
                        SELECT COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = %s
                        AND TABLE_NAME = %s
                        AND CONSTRAINT_NAME = 'PRIMARY'
                    """, (base_empresa, datasource_name))
                    primary_keys = {row[0] for row in cursor.fetchall()}
                    
                    # Obtener claves foráneas
                    cursor.execute("""
                        SELECT 
                            COLUMN_NAME,
                            REFERENCED_TABLE_NAME,
                            REFERENCED_COLUMN_NAME
                        FROM information_schema.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = %s
                        AND TABLE_NAME = %s
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                    """, (base_empresa, datasource_name))
                    foreign_keys = {
                        row[0]: (row[1], row[2])
                        for row in cursor.fetchall()
                    }
                    
                    for col in columns:
                        col_name, data_type, col_type, is_nullable, col_key, col_comment, extra = col
                        
                        is_pk = col_name in primary_keys
                        is_fk = col_name in foreign_keys
                        ref_table, ref_field = foreign_keys.get(col_name, (None, None))
                        
                        field = SemanticField(
                            name=col_name,
                            data_type=data_type.upper(),
                            is_nullable=is_nullable == 'YES',
                            is_primary_key=is_pk,
                            is_foreign_key=is_fk,
                            referenced_table=ref_table,
                            referenced_field=ref_field,
                            description=col_comment or None
                        )
                        fields.append(field)
                    
                    cursor.close()
                    
            except Exception as e:
                logger.error(f"❌ Error obteniendo campos de {datasource_name}: {e}")
                # Retornar campos vacíos en caso de error
                return []
        else:
            # Sin base_empresa, retornar campos comunes conocidos
            # Esto es un fallback básico
            common_fields = {
                'cuentacliente': [
                    SemanticField('Fecha', 'DATE', False),
                    SemanticField('TipoComprobante', 'VARCHAR', False),
                    SemanticField('NumeroComprobante', 'VARCHAR', False),
                    SemanticField('SubtotalDesc', 'DECIMAL', True),
                    SemanticField('CodSucursal', 'INT', True),
                    SemanticField('id_pv', 'INT', True),
                    SemanticField('Anulado', 'VARCHAR', False),
                ],
                'caja': [
                    SemanticField('fecha', 'DATE', False),
                    SemanticField('id_caja_abm_origen', 'INT', True),
                    SemanticField('id_caja_abm_destino', 'INT', True),
                    SemanticField('importe', 'DECIMAL', True),
                    SemanticField('anulado', 'VARCHAR', False),
                ],
            }
            
            if datasource_name in common_fields:
                fields = common_fields[datasource_name]
            else:
                # Campos genéricos
                fields = [
                    SemanticField('id', 'INT', False, is_primary_key=True),
                    SemanticField('fecha', 'DATE', True),
                ]
        
        # Guardar en cache
        cls._cache[cache_key] = fields
        
        logger.info(f"✅ {len(fields)} campos encontrados para {datasource_name}")
        return fields
    
    @classmethod
    def get_relationships(cls, datasource_name: str, base_empresa: Optional[str] = None, empresa: Optional[Any] = None) -> List[SemanticRelationship]:
        """
        Obtiene las relaciones (JOINs posibles) de una tabla.
        
        Args:
            datasource_name: Nombre de la tabla
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            Lista de SemanticRelationship con información de JOINs
        """
        cache_key = f"relationships_{datasource_name}_{base_empresa or 'default'}"
        
        # Verificar cache
        if cache_key in cls._cache:
            logger.debug(f"📦 Cache hit para {cache_key}")
            return cls._cache[cache_key]
        
        relationships = []
        
        if base_empresa:
            try:
                pool = get_mysql_pool()
                with pool.get_connection(base_empresa) as conn:
                    cursor = conn.cursor()
                    
                    # Obtener todas las claves foráneas usando JOIN con REFERENTIAL_CONSTRAINTS
                    # Esto asegura que obtenemos todas las relaciones, incluyendo UPDATE_RULE y DELETE_RULE
                    cursor.execute("""
                        SELECT 
                            kcu.TABLE_NAME,
                            kcu.COLUMN_NAME,
                            kcu.REFERENCED_TABLE_NAME,
                            kcu.REFERENCED_COLUMN_NAME,
                            rc.UPDATE_RULE,
                            rc.DELETE_RULE
                        FROM information_schema.KEY_COLUMN_USAGE kcu
                        JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                            ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                           AND rc.CONSTRAINT_SCHEMA = kcu.TABLE_SCHEMA
                        WHERE kcu.REFERENCED_TABLE_NAME IS NOT NULL
                          AND kcu.TABLE_SCHEMA = %s
                          AND (kcu.TABLE_NAME = %s OR kcu.REFERENCED_TABLE_NAME = %s)
                        ORDER BY kcu.TABLE_NAME, kcu.COLUMN_NAME
                    """, (base_empresa, datasource_name, datasource_name))
                    
                    # Cache de comentarios de tablas para evitar múltiples consultas
                    table_comments_cache = {}
                    
                    for table_name, col_name, ref_table, ref_field, update_rule, delete_rule in cursor.fetchall():
                        # Obtener comentario de la tabla destino para label (con cache)
                        if ref_table not in table_comments_cache:
                            cursor.execute("""
                                SELECT TABLE_COMMENT
                                FROM information_schema.TABLES
                                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                            """, (base_empresa, ref_table))
                            table_comment = cursor.fetchone()
                            table_comments_cache[ref_table] = table_comment[0] if table_comment and table_comment[0] else ref_table
                        
                        label = table_comments_cache[ref_table]
                        
                        # Determinar tipo de relación
                        if table_name == datasource_name:
                            # Relación saliente (desde esta tabla)
                            relationship_type = "ONE_TO_MANY"
                            cardinality = "N:1"
                        else:
                            # Relación entrante (hacia esta tabla)
                            relationship_type = "MANY_TO_ONE"
                            cardinality = "1:N"
                        
                        # Construir descripción con información de reglas
                        rules_info = []
                        if update_rule and update_rule != 'RESTRICT':
                            rules_info.append(f"UPDATE: {update_rule}")
                        if delete_rule and delete_rule != 'RESTRICT':
                            rules_info.append(f"DELETE: {delete_rule}")
                        
                        description = f"Relación desde {table_name}.{col_name} a {ref_table}.{ref_field}"
                        if rules_info:
                            description += f" ({', '.join(rules_info)})"
                        
                        relationships.append(SemanticRelationship(
                            from_table=table_name,
                            from_field=col_name,
                            to_table=ref_table,
                            to_field=ref_field,
                            relationship_type=relationship_type,
                            description=description,
                            confidence=1.0,  # FK explícita = máxima confianza
                            source="foreign_key",
                            label=label,
                            cardinality=cardinality
                        ))
                    
                    # Si no hay FKs, intentar heurística
                    if len(relationships) == 0:
                        try:
                            relationships.extend(cls._infer_relationships_heuristic(
                                datasource_name, base_empresa, conn, cursor
                            ))
                        except Exception as e:
                            logger.warning(f"Error en heurística de relaciones para {datasource_name}: {e}")
                    
                    cursor.close()
                    
            except Exception as e:
                logger.error(f"❌ Error obteniendo relaciones de {datasource_name}: {e}")
                # Retornar relaciones vacías en caso de error
                return []
    
    @classmethod
    def get_all_foreign_keys(cls, base_empresa: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las claves foráneas de la base de datos de una vez.
        Función reutilizable para clustering y table networks.
        
        Args:
            base_empresa: Base de datos MySQL
            
        Returns:
            Lista de dicts con: tabla_origen, campo_origen, tabla_destino, campo_destino,
            constraint_name, update_rule, delete_rule
        """
        if not base_empresa:
            return []
        
        try:
            pool = get_mysql_pool()
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                
                # Cambiar a la base de datos correcta
                cursor.execute(f"USE `{base_empresa}`")
                
                # Usar la misma consulta que el usuario para obtener todas las FK
                cursor.execute("""
                    SELECT
                        kcu.TABLE_NAME              AS tabla_origen,
                        kcu.COLUMN_NAME             AS campo_origen,
                        kcu.REFERENCED_TABLE_NAME   AS tabla_destino,
                        kcu.REFERENCED_COLUMN_NAME  AS campo_destino,
                        rc.CONSTRAINT_NAME,
                        rc.UPDATE_RULE,
                        rc.DELETE_RULE
                    FROM information_schema.KEY_COLUMN_USAGE kcu
                    JOIN information_schema.REFERENTIAL_CONSTRAINTS rc
                        ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                       AND rc.CONSTRAINT_SCHEMA = kcu.TABLE_SCHEMA
                    WHERE kcu.REFERENCED_TABLE_NAME IS NOT NULL
                      AND kcu.TABLE_SCHEMA = DATABASE()
                    ORDER BY tabla_origen, campo_origen
                """)
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "tabla_origen": row[0],
                        "campo_origen": row[1],
                        "tabla_destino": row[2],
                        "campo_destino": row[3],
                        "constraint_name": row[4],
                        "update_rule": row[5],
                        "delete_rule": row[6],
                    })
                
                cursor.close()
                logger.debug(f"📊 Obtenidas {len(results)} FK de {base_empresa}")
                return results
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo todas las FK de {base_empresa}: {e}", exc_info=True)
            return []
        else:
            # Sin base_empresa, retornar relaciones conocidas comunes
            known_relationships = {
                'cuentacliente': [
                    SemanticRelationship(
                        from_table='cuentacliente',
                        from_field='CodSucursal',
                        to_table='sucursales',
                        to_field='id_sucursal',
                        relationship_type='ONE_TO_MANY',
                        description='Relación con sucursales'
                    ),
                    SemanticRelationship(
                        from_table='cuentacliente',
                        from_field='id_pv',
                        to_table='punto_venta',
                        to_field='id_punto_venta',
                        relationship_type='ONE_TO_MANY',
                        description='Relación con punto de venta'
                    ),
                ],
            }
            
            if datasource_name in known_relationships:
                relationships = known_relationships[datasource_name]
        
        # Integrar relaciones aprendidas (L1: Aprendizaje por uso)
        try:
            from .relationship_learning import RelationshipLearningService
            
            # Obtener relaciones aprendidas (empresa puede venir como parámetro)
            # Por defecto, solo incluir APPROVED. PROPOSED solo si tienen alta confianza (>=0.8)
            # Esto puede ser configurable en el futuro desde el frontend
            learned_rels = RelationshipLearningService.get_learned_relationships(
                empresa=empresa,
                from_table=datasource_name,
                include_proposed=True,  # Incluir propuestas con alta confianza
                min_confidence_proposed=0.8  # Threshold para propuestas
            )
            
            # Convertir SemanticRelationship a diccionarios para merge
            fk_heuristic_dicts = []
            for rel in relationships:
                fk_heuristic_dicts.append({
                    'from_table': rel.from_table,
                    'from_column': rel.from_field,
                    'to_table': rel.to_table,
                    'to_column': rel.to_field,
                    'confidence': rel.confidence,
                    'source': rel.source,
                    'label': rel.label,
                    'description': rel.description,
                    'cardinality': rel.cardinality,
                })
            
            # Merge y ranking
            merged_dicts = RelationshipLearningService.merge_relationship_sources(
                fk_or_heuristic_rels=fk_heuristic_dicts,
                learned_rels=learned_rels
            )
            
            # Convertir de vuelta a SemanticRelationship
            # Nota: SemanticRelationship no tiene campo 'badge', pero lo preservamos
            # en el diccionario para que llegue al frontend
            relationships = []
            for rel_dict in merged_dicts:
                rel = SemanticRelationship(
                    from_table=rel_dict.get('from_table', ''),
                    from_field=rel_dict.get('from_column', ''),
                    to_table=rel_dict.get('to_table', ''),
                    to_field=rel_dict.get('to_column', ''),
                    relationship_type="ONE_TO_MANY",  # Default
                    description=rel_dict.get('description', ''),
                    confidence=rel_dict.get('confidence', 0.5),
                    source=rel_dict.get('source', 'heuristic'),
                    label=rel_dict.get('label'),
                    cardinality=rel_dict.get('cardinality', 'N:1')
                )
                # Agregar badge y status como atributos dinámicos (no están en el dataclass)
                rel.badge = rel_dict.get('badge', 'Sugerido')
                if 'status' in rel_dict:
                    rel.status = rel_dict.get('status')
                relationships.append(rel)
            
        except Exception as e:
            logger.warning(f"⚠️ Error integrando relaciones aprendidas: {e}")
            # Continuar con relaciones FK/heurísticas si falla el aprendizaje
        
        # Guardar en cache
        cls._cache[cache_key] = relationships
        
        logger.info(f"✅ {len(relationships)} relaciones encontradas para {datasource_name} (incluye aprendidas)")
        return relationships
    
    @classmethod
    def suggest_joins(cls, base_table: str, selected_fields_tables: List[str], base_empresa: Optional[str] = None) -> List[SemanticRelationship]:
        """
        Sugiere JOINs basándose en la tabla base y las tablas de campos seleccionados.
        
        Args:
            base_table: Tabla principal del reporte
            selected_fields_tables: Lista de nombres de tablas de campos ya seleccionados
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            Lista de SemanticRelationship sugeridas, ordenadas por confianza
        """
        suggestions = []
        seen_joins = set()  # Para evitar duplicados
        
        # Obtener relaciones directas de la tabla base
        base_relationships = cls.get_relationships(base_table, base_empresa)
        
        for rel in base_relationships:
            # Si la tabla destino está en las tablas seleccionadas, es una buena sugerencia
            if rel.to_table in selected_fields_tables:
                key = (rel.from_table, rel.to_table, rel.from_field, rel.to_field)
                if key not in seen_joins:
                    seen_joins.add(key)
                    suggestions.append(rel)
        
        # También buscar relaciones inversas (tablas que apuntan a la base)
        # y que están en las tablas seleccionadas
        for table in selected_fields_tables:
            if table == base_table:
                continue
            
            table_relationships = cls.get_relationships(table, base_empresa)
            for rel in table_relationships:
                # Si la relación apunta a la tabla base
                if rel.to_table == base_table:
                    key = (rel.from_table, rel.to_table, rel.from_field, rel.to_field)
                    if key not in seen_joins:
                        seen_joins.add(key)
                        # Invertir la relación para el JOIN
                        suggestions.append(SemanticRelationship(
                            from_table=base_table,
                            from_field=rel.to_field,
                            to_table=rel.from_table,
                            to_field=rel.from_field,
                            relationship_type="ONE_TO_MANY",
                            description=f"Relación sugerida desde {base_table} a {rel.from_table}",
                            confidence=rel.confidence
                        ))
        
        # Ordenar por confianza (mayor primero)
        suggestions.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info(f"✅ {len(suggestions)} JOINs sugeridos para {base_table}")
        return suggestions
    
    @classmethod
    def get_join_candidates(cls, current_graph_tables: List[Dict[str, str]], base_empresa: Optional[str] = None) -> Dict[str, List[SemanticRelationship]]:
        """
        Obtiene candidatas de JOIN para cada tabla presente en el grafo actual.
        
        Args:
            current_graph_tables: Lista de diccionarios con 'table' y 'alias' de tablas ya presentes
                Ejemplo: [{'table': 'cuentacliente', 'alias': 'cc'}, {'table': 'sucursales', 'alias': 's'}]
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            Diccionario donde la clave es el nombre de la tabla (o alias) y el valor es una lista
            de SemanticRelationship con las candidatas para esa tabla
        """
        candidates = {}
        
        for table_info in current_graph_tables:
            table_name = table_info.get('table', '')
            alias = table_info.get('alias', '')
            display_name = alias if alias else table_name
            
            if not table_name:
                continue
            
            # Obtener relaciones de esta tabla (sin empresa específica para este método)
            relationships = cls.get_relationships(table_name, base_empresa, empresa=None)
            
            # Filtrar relaciones que apuntan a tablas que aún no están en el grafo
            existing_tables = {t.get('table', '') for t in current_graph_tables}
            filtered_relationships = [
                rel for rel in relationships
                if rel.to_table not in existing_tables
            ]
            
            if filtered_relationships:
                candidates[display_name] = filtered_relationships
        
        logger.info(f"✅ {sum(len(v) for v in candidates.values())} candidatas de JOIN encontradas para {len(current_graph_tables)} tablas")
        return candidates
    
    @classmethod
    def get_join_candidates_for_graph(cls, base_table: str, current_joins: List[Dict[str, str]], base_empresa: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtiene candidatas de JOIN para un grafo de tablas (base + joins existentes).
        
        Args:
            base_table: Tabla principal del reporte
            current_joins: Lista de joins existentes con formato [{"table": "...", "alias": "..."}]
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            Lista de diccionarios con estructura:
            [
                {
                    "source_table": "cuentacliente",
                    "source_alias": "cc",
                    "candidates": [SemanticRelationship, ...]
                },
                ...
            ]
        """
        result = []
        
        # Construir grafo de tablas presentes
        graph_tables = [{"table": base_table, "alias": cls._get_default_alias(base_table)}]
        graph_tables.extend(current_joins)
        
        existing_tables = {t.get("table", "") for t in graph_tables}
        
        # Para cada tabla en el grafo, obtener sus candidatas
        for table_info in graph_tables:
            table_name = table_info.get("table", "")
            alias = table_info.get("alias", "") or cls._get_default_alias(table_name)
            
            if not table_name:
                continue
            
            # Obtener relaciones de esta tabla (sin empresa específica para este método)
            relationships = cls.get_relationships(table_name, base_empresa, empresa=None)
            
            # Filtrar: solo tablas que no están ya en el grafo
            # Y normalizar: si la relación es inversa (from_table != table_name), invertirla
            candidates = []
            for rel in relationships:
                # Determinar tabla destino
                if rel.from_table == table_name:
                    target_table = rel.to_table
                    from_field = rel.from_field
                    to_field = rel.to_field
                else:
                    # Relación inversa: invertir
                    target_table = rel.from_table
                    from_field = rel.to_field
                    to_field = rel.from_field
                
                # Solo agregar si la tabla destino no está ya en el grafo
                if target_table not in existing_tables:
                    candidates.append({
                        "from_table": table_name,
                        "from_field": from_field,
                        "to_table": target_table,
                        "to_field": to_field,
                        "label": rel.label or target_table,
                        "description": rel.description or f"Relación con {target_table}",
                        "confidence": rel.confidence,
                        "source": rel.source,
                        "badge": getattr(rel, 'badge', 'Sugerido'),  # Badge del merge
                        "cardinality": rel.cardinality or "N:1"
                    })
            
            if candidates:
                # Convertir SemanticRelationship a diccionarios con badge
                candidates_dicts = []
                for rel in candidates:
                    candidates_dicts.append({
                        "from_table": rel.from_table,
                        "from_field": rel.from_field,
                        "to_table": rel.to_table,
                        "to_field": rel.to_field,
                        "label": getattr(rel, 'label', None) or rel.to_table,
                        "description": rel.description or f"Relación con {rel.to_table}",
                        "confidence": rel.confidence,
                        "source": rel.source,
                        "badge": getattr(rel, 'badge', 'Sugerido'),  # Badge del merge
                        "cardinality": rel.cardinality or "N:1"
                    })
                
                result.append({
                    "source_table": table_name,
                    "source_alias": alias,
                    "candidates": candidates_dicts
                })
        
        return result
    
    @classmethod
    def _get_default_alias(cls, table_name: str) -> str:
        """Genera un alias por defecto para una tabla (primeras letras)."""
        if not table_name:
            return ""
        # Tomar primeras letras de cada palabra o primeros caracteres
        words = table_name.split('_')
        if len(words) > 1:
            return ''.join(w[0].lower() for w in words if w)[:3]
        return table_name[0:2].lower()
    
    @classmethod
    def get_join_candidates(cls, current_graph_tables: List[Dict[str, str]], base_empresa: Optional[str] = None) -> Dict[str, List[SemanticRelationship]]:
        """
        Obtiene candidatas de JOIN para cada tabla en el grafo actual.
        
        Args:
            current_graph_tables: Lista de diccionarios con 'table' y 'alias' de tablas ya presentes
                Ejemplo: [{'table': 'cuentacliente', 'alias': 'cc'}, {'table': 'sucursales', 'alias': 's'}]
            base_empresa: Base de datos MySQL (opcional)
            
        Returns:
            Diccionario donde la clave es el alias (o nombre de tabla) y el valor es una lista
            de SemanticRelationship candidatas para esa tabla
        """
        candidates = {}
        
        for table_info in current_graph_tables:
            table_name = table_info.get('table', '')
            alias = table_info.get('alias', table_name)
            
            if not table_name:
                continue
            
            # Obtener relaciones de esta tabla (sin empresa específica para este método)
            relationships = cls.get_relationships(table_name, base_empresa, empresa=None)
            
            # Filtrar relaciones que apuntan a tablas que NO están ya en el grafo
            # (para evitar sugerir JOINs a tablas ya conectadas)
            existing_tables = {t.get('table', '').lower() for t in current_graph_tables}
            
            filtered_relationships = []
            for rel in relationships:
                # Considerar relaciones salientes (desde esta tabla hacia otra)
                if rel.to_table.lower() not in existing_tables:
                    filtered_relationships.append(rel)
                
                # También considerar relaciones entrantes (otra tabla apunta a esta)
                # pero invertir la relación para el JOIN
                if rel.from_table.lower() == table_name.lower() and rel.to_table.lower() not in existing_tables:
                    # Ya está incluida arriba
                    pass
            
            # Si no hay relaciones explícitas, usar heurística (búsqueda por nombre similar)
            if not filtered_relationships:
                # Buscar tablas con nombres similares o patrones comunes
                # Por ejemplo: si la tabla es 'cuentacliente', buscar 'cliente', 'clientes', etc.
                # Esto es una heurística simple, puede mejorarse
                logger.debug(f"⚠️ No se encontraron relaciones explícitas para {table_name}, usando heurística")
            
            candidates[alias] = filtered_relationships
        
        logger.info(f"✅ Candidatas obtenidas para {len(candidates)} tablas del grafo")
        return candidates
    
    @classmethod
    def _infer_relationships_heuristic(cls, from_table: str, base_empresa: Optional[str], conn, cursor) -> List[SemanticRelationship]:
        """
        Infiere relaciones por heurística cuando no hay foreign keys explícitas.
        
        Heurísticas:
        - Campos que terminan en _id, id_*, cod*
        - Nombres normalizados (ej: CodSucursal -> sucursales)
        """
        inferred = []
        
        try:
            # Obtener todas las columnas de la tabla origen
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """, (base_empresa, from_table))
            
            columns = cursor.fetchall()
            
            # Obtener todas las tablas disponibles
            cursor.execute("""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            """, (base_empresa,))
            
            available_tables = [row[0] for row in cursor.fetchall()]
            
            for col_name, col_type in columns:
                # Heurística 1: Campos que terminan en _id
                if col_name.lower().endswith('_id'):
                    # Intentar encontrar tabla relacionada
                    potential_table = col_name[:-3]  # Quitar _id
                    # Buscar tabla que coincida (singular o plural)
                    for table in available_tables:
                        if table.lower() == potential_table or table.lower() == potential_table + 's':
                            # Verificar si la tabla tiene un campo id o id_*
                            cursor.execute("""
                                SELECT COLUMN_NAME
                                FROM information_schema.COLUMNS
                                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                                AND (COLUMN_NAME = 'id' OR COLUMN_NAME LIKE 'id_%' OR COLUMN_NAME = %s)
                            """, (base_empresa, table, col_name))
                            
                            target_cols = cursor.fetchall()
                            if target_cols:
                                target_col = target_cols[0][0]
                                inferred.append(SemanticRelationship(
                                    from_table=from_table,
                                    from_field=col_name,
                                    to_table=table,
                                    to_field=target_col,
                                    relationship_type="ONE_TO_MANY",
                                    description=f"Relación inferida: {from_table}.{col_name} → {table}.{target_col}",
                                    confidence=0.6,  # Confianza media para heurística
                                    source="heuristic",
                                    label=table,
                                    cardinality="N:1"
                                ))
                
                # Heurística 2: Campos que empiezan con Cod* o cod*
                elif col_name.lower().startswith('cod'):
                    # Normalizar nombre: CodSucursal -> sucursales
                    potential_table = col_name[3:].lower() if len(col_name) > 3 else None
                    if potential_table:
                        # Buscar tabla que coincida
                        for table in available_tables:
                            table_lower = table.lower()
                            if potential_table in table_lower or table_lower in potential_table:
                                # Buscar campo id en la tabla destino
                                cursor.execute("""
                                    SELECT COLUMN_NAME
                                    FROM information_schema.COLUMNS
                                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                                    AND (COLUMN_NAME = 'id' OR COLUMN_NAME LIKE 'id_%')
                                    LIMIT 1
                                """, (base_empresa, table))
                                
                                target_cols = cursor.fetchall()
                                if target_cols:
                                    target_col = target_cols[0][0]
                                    inferred.append(SemanticRelationship(
                                        from_table=from_table,
                                        from_field=col_name,
                                        to_table=table,
                                        to_field=target_col,
                                        relationship_type="ONE_TO_MANY",
                                        description=f"Relación inferida: {from_table}.{col_name} → {table}.{target_col}",
                                        confidence=0.5,  # Confianza baja para heurística
                                        source="heuristic",
                                        label=table,
                                        cardinality="N:1"
                                    ))
            
            logger.info(f"🔍 {len(inferred)} relaciones inferidas por heurística para {from_table}")
            
        except Exception as e:
            logger.warning(f"⚠️ Error en heurística de relaciones para {from_table}: {e}")
        
        return inferred
    
    @classmethod
    def clear_cache(cls, pattern: Optional[str] = None):
        """
        Limpia el cache de metadata.
        
        Args:
            pattern: Patrón opcional para limpiar solo ciertas claves (ej: "datasources_*")
        """
        if pattern:
            keys_to_remove = [k for k in cls._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del cls._cache[key]
            logger.info(f"🗑️ Cache limpiado: {len(keys_to_remove)} entradas")
        else:
            cls._cache.clear()
            logger.info("🗑️ Cache completamente limpiado")
    
    @classmethod
    def get_available_tables(cls, base_empresa: str) -> List[str]:
        """
        Obtiene lista de nombres de tablas disponibles.
        
        Args:
            base_empresa: Base de datos MySQL
            
        Returns:
            Lista de nombres de tablas
        """
        datasources = cls.list_datasources(base_empresa=base_empresa)
        return [ds.name for ds in datasources]
    
    @classmethod
    def get_table_fields(cls, base_empresa: str, table_name: str) -> List[Dict[str, Any]]:
        """
        Obtiene campos de una tabla en formato diccionario (compatible con ExportImportService).
        
        Args:
            base_empresa: Base de datos MySQL
            table_name: Nombre de la tabla
            
        Returns:
            Lista de diccionarios con información de campos
        """
        fields = cls.get_fields(datasource_name=table_name, base_empresa=base_empresa)
        return [
            {
                "name": f.name,
                "data_type": f.data_type,
                "nullable": f.is_nullable,
            }
            for f in fields
        ]





