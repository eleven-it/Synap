"""
Servicio de Descubrimiento de Relaciones entre Tablas
Encuentra relaciones automáticamente sin necesidad de FKs formales
"""
import re
from typing import List, Dict, Tuple, Optional, Set
from difflib import SequenceMatcher
from django.db import connection
from django.utils import timezone
from datetime import timedelta

from ..models import (
    RelationshipCandidate,
    ColumnStatistics,
    SynonymMapping
)
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService


class RelationshipDiscoveryService:
    """
    Descubre relaciones entre tablas mediante múltiples señales:
    - Coincidencia de nombres (exacta, parcial, patterns)
    - Compatibilidad de tipos
    - Inclusión de dominios (valores)
    - Unicidad y cardinalidad
    - Hints del Logic Interpreter
    """
    
    # Patrones CONSERVADORES para FK (solo estos se analizan)
    FK_PATTERNS = [
        r'^Cod(\w+)$',            # CodLaboratorio, CodCliente
        r'^codigo_(\w+)$',        # codigo_articulo
        r'^cod(\w+)$',            # codlaboratorio
        r'^ID_(\w+)$',            # ID_Articulo, ID_Cliente
        r'^(\w+)ID$',             # ClienteID, ArticuloID
        r'^(\w+)_id$',            # cliente_id, articulo_id
        r'^(\w+)_ID$',            # cliente_ID
        r'^id(\w+)$',             # idarticulo
        r'^ID(\w+)$',             # IDCliente, IDArticulo
    ]
    
    # Solo tipos numéricos enteros son válidos para relaciones
    NUMERIC_INTEGER_TYPES = ['int', 'tinyint', 'smallint', 'mediumint', 'bigint']
    
    # Tipos compatibles para joins (solo numéricos)
    TYPE_COMPATIBILITY = {
        ('int', 'int'): 1.0,
        ('bigint', 'int'): 0.9,
        ('int', 'bigint'): 0.9,
        ('tinyint', 'int'): 0.85,
        ('smallint', 'int'): 0.85,
        ('mediumint', 'int'): 0.95,
        ('mediumint', 'bigint'): 0.9,
    }
    
    def __init__(self):
        # Obtener configuración de administraNET
        self.config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not self.config:
            raise ValueError("No se encontró configuración activa de administraNET")
        
        self.connection_service = AdministraNETConnectionService(self.config)
        self.db_name = self.config.database_name
    
    def _get_mysql_connection(self):
        """Obtiene conexión de MySQL para administraNET"""
        import mysql.connector
        
        connection_params = self.connection_service.get_connection_params()
        conn = mysql.connector.connect(**connection_params)
        
        if not conn.is_connected():
            raise Exception("No se pudo conectar a administraNET MySQL")
        
        return conn
    
    def discover_all_relationships(self, min_confidence: float = 0.6, use_logic_interpreter: bool = True) -> int:
        """
        Descubre TODAS las relaciones posibles en el schema
        Integra información del Logic Interpreter para mayor precisión
        
        Args:
            min_confidence: Score mínimo para guardar la relación
            use_logic_interpreter: Si True, consulta Business Rules y mapas de persistencia
        
        Returns:
            Número de relaciones descubiertas
        """
        print(f"\n🔍 Iniciando descubrimiento automático de relaciones...")
        print(f"   Umbral mínimo de confianza: {min_confidence}")
        
        # 1. Obtener contexto del Logic Interpreter (si está habilitado)
        logic_context = None
        if use_logic_interpreter:
            logic_context = self._get_logic_interpreter_context()
            if logic_context:
                print(f"   🧠 Contexto del Logic Interpreter cargado:")
                print(f"      • {logic_context['business_rules_count']} reglas de negocio")
                print(f"      • {logic_context['suggested_relationships_count']} relaciones sugeridas")
        
        # 2. Actualizar estadísticas de columnas
        self._update_column_statistics()
        
        # 3. Obtener todas las columnas del schema
        columns_by_table = self._get_all_columns()
        
        # 4. Descubrir relaciones candidatas
        discovered_count = 0
        enriched_count = 0
        total_comparisons = 0
        
        for source_table, source_columns in columns_by_table.items():
            for source_col in source_columns:
                # FILTRO A: Solo analizar columnas con patrón FK válido
                if not self._has_fk_pattern(source_col['name']):
                    continue
                
                # FILTRO B: Solo tipos numéricos enteros
                if source_col['data_type'].lower() not in self.NUMERIC_INTEGER_TYPES:
                    continue
                
                # Intentar encontrar tabla destino basada en el patrón
                target_table_candidate = self._infer_target_table_from_pattern(
                    source_col['name'], 
                    source_table,
                    columns_by_table.keys()
                )
                
                if not target_table_candidate:
                    continue  # No se pudo inferir tabla destino con confianza
                
                # Buscar columna destino en la tabla candidata
                target_columns = columns_by_table.get(target_table_candidate, [])
                
                for target_col in target_columns:
                    # FILTRO B: Solo tipos numéricos enteros en destino
                    if target_col['data_type'].lower() not in self.NUMERIC_INTEGER_TYPES:
                        continue
                    
                    # FILTRO C: Verificar que columna destino sea PK o UNIQUE
                    if not (target_col['is_key'] and self._is_primary_or_unique(
                        target_table_candidate, 
                        target_col['name']
                    )):
                        continue
                    
                    total_comparisons += 1
                    
                    # Calcular score de la relación
                    relationship_data = self._analyze_relationship(
                        source_table, source_col,
                        target_table_candidate, target_col
                    )
                    
                    # Enriquecer con información del Logic Interpreter
                    if logic_context:
                        enriched = self._enrich_with_logic_context(
                            relationship_data,
                            logic_context
                        )
                        if enriched:
                            enriched_count += 1
                    
                    if relationship_data['confidence'] >= min_confidence:
                        # Guardar o actualizar la relación
                        self._save_relationship(relationship_data)
                        discovered_count += 1
                        
                        if discovered_count % 10 == 0:
                            print(f"   Descubiertas: {discovered_count} relaciones...")
        
        print(f"\n✅ Descubrimiento completo:")
        print(f"   Total comparaciones: {total_comparisons:,}")
        print(f"   Relaciones descubiertas: {discovered_count}")
        if enriched_count > 0:
            print(f"   🧠 Enriquecidas con Logic Interpreter: {enriched_count}")
        
        return discovered_count
    
    def _has_fk_pattern(self, column_name: str) -> bool:
        """
        Verifica si el nombre de la columna coincide con algún patrón FK válido
        Criterio A: Patrón de Nombre (OBLIGATORIO)
        """
        for pattern in self.FK_PATTERNS:
            if re.match(pattern, column_name, re.IGNORECASE):
                return True
        return False
    
    def _infer_target_table_from_pattern(
        self, 
        column_name: str, 
        source_table: str,
        all_tables: list
    ) -> Optional[str]:
        """
        Infiere la tabla destino basándose en el patrón del nombre de columna
        Criterio C: Confirmación de Tabla Destino (OBLIGATORIO)
        
        Returns:
            Nombre de la tabla destino si se encuentra con confianza, None si no
        """
        # Extraer entidad del patrón
        entity_name = None
        
        for pattern in self.FK_PATTERNS:
            match = re.match(pattern, column_name, re.IGNORECASE)
            if match:
                # Obtener el grupo capturado (la entidad)
                entity_name = match.group(1) if match.lastindex else None
                break
        
        if not entity_name:
            return None
        
        # Normalizar nombre de entidad
        entity_norm = entity_name.lower()
        
        # Buscar tabla que coincida
        for table in all_tables:
            table_norm = table.lower()
            
            # Coincidencia exacta
            if table_norm == entity_norm:
                return table
            
            # Singular/plural (remover 's' final)
            if table_norm == entity_norm.rstrip('s') or entity_norm == table_norm.rstrip('s'):
                return table
        
        return None
    
    def _is_primary_or_unique(self, table: str, column: str) -> bool:
        """
        Verifica si una columna es PRIMARY KEY o UNIQUE
        Parte del Criterio C
        """
        conn = None
        try:
            conn = self._get_mysql_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute(f"""
                SELECT COLUMN_KEY
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{self.db_name}'
                AND TABLE_NAME = '{table}'
                AND COLUMN_NAME = '{column}'
            """)
            
            result = cursor.fetchone()
            if result:
                return result['COLUMN_KEY'] in ('PRI', 'UNI')
            
            return False
        
        except Exception as e:
            print(f"   ⚠️ Error verificando PK/UNIQUE para {table}.{column}: {e}")
            return False
        
        finally:
            if conn and conn.is_connected():
                conn.close()
    
    def _update_column_statistics(self):
        """Actualiza estadísticas de todas las columnas"""
        print("\n📊 Actualizando estadísticas de columnas...")
        
        conn = self._get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Obtener todas las tablas
            cursor.execute(f"""
                SELECT TABLE_NAME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = '{self.db_name}'
                AND TABLE_TYPE = 'BASE TABLE'
            """)
            
            tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
            stats_count = 0
            
            for table in tables:
                # Obtener columnas de la tabla
                cursor.execute(f"""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = '{self.db_name}'
                    AND TABLE_NAME = '{table}'
                """)
                
                columns = cursor.fetchall()
                
                for col_info in columns:
                    col_name = col_info['COLUMN_NAME']
                    data_type = col_info['DATA_TYPE']
                    is_nullable = col_info['IS_NULLABLE']
                    
                    # Calcular estadísticas
                    stats = self._calculate_column_stats(table, col_name)
                    
                    if stats:
                        # Guardar o actualizar
                        ColumnStatistics.objects.update_or_create(
                            table_name=table,
                            column_name=col_name,
                            defaults=stats
                        )
                        stats_count += 1
            
            print(f"   ✅ Estadísticas calculadas para {stats_count} columnas")
        
        finally:
            cursor.close()
            conn.close()
    
    def _calculate_column_stats(self, table: str, column: str) -> Optional[Dict]:
        """Calcula estadísticas para una columna específica"""
        conn = None
        try:
            conn = self._get_mysql_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Total, únicos, nulos
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT `{column}`) as unique_count,
                    SUM(CASE WHEN `{column}` IS NULL THEN 1 ELSE 0 END) as null_count
                FROM `{self.db_name}`.`{table}`
            """)
            
            result = cursor.fetchone()
            total = result['total']
            unique_count = result['unique_count']
            null_count = result['null_count']
            
            if total == 0:
                return None
            
            # Muestreo de valores top 20
            cursor.execute(f"""
                SELECT `{column}` as value, COUNT(*) as cnt
                FROM `{self.db_name}`.`{table}`
                WHERE `{column}` IS NOT NULL
                GROUP BY `{column}`
                ORDER BY cnt DESC
                LIMIT 20
            """)
            
            sample_values = [
                {'value': str(row['value']), 'count': row['cnt']}
                for row in cursor.fetchall()
            ]
            
            null_pct = (null_count / total * 100) if total > 0 else 0
            
            return {
                'total_count': total,
                'unique_count': unique_count,
                'null_count': null_count,
                'is_unique': (unique_count == total - null_count) if total > 0 else False,
                'is_nullable': null_count > 0,
                'null_percentage': null_pct,
                'sample_values': sample_values,
                'is_stale': False
            }
        
        except Exception as e:
            print(f"   ⚠️ Error calculando stats para {table}.{column}: {e}")
            return None
        
        finally:
            if conn and conn.is_connected():
                conn.close()
    
    def _get_all_columns(self) -> Dict[str, List[Dict]]:
        """Obtiene todas las columnas agrupadas por tabla"""
        conn = self._get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(f"""
                SELECT 
                    TABLE_NAME,
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    IS_NULLABLE,
                    COLUMN_KEY
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{self.db_name}'
                ORDER BY TABLE_NAME, ORDINAL_POSITION
            """)
            
            columns_by_table = {}
            for row in cursor.fetchall():
                table_name = row['TABLE_NAME']
                column_info = {
                    'name': row['COLUMN_NAME'],
                    'data_type': row['DATA_TYPE'],
                    'max_length': row['CHARACTER_MAXIMUM_LENGTH'],
                    'is_nullable': row['IS_NULLABLE'] == 'YES',
                    'is_key': row['COLUMN_KEY'] in ('PRI', 'UNI', 'MUL')
                }
                
                if table_name not in columns_by_table:
                    columns_by_table[table_name] = []
                
                columns_by_table[table_name].append(column_info)
            
            return columns_by_table
        
        finally:
            cursor.close()
            conn.close()
    
    def _analyze_relationship(
        self,
        source_table: str,
        source_col: Dict,
        target_table: str,
        target_col: Dict
    ) -> Dict:
        """
        Analiza una posible relación y calcula su score de confianza
        """
        # 1. Coincidencia de nombres
        name_score = self._calculate_name_match(
            source_col['name'],
            target_col['name'],
            source_table,
            target_table
        )
        
        # 2. Compatibilidad de tipos
        type_score = self._calculate_type_compatibility(
            source_col['data_type'],
            target_col['data_type']
        )
        
        # 3. Obtener estadísticas
        source_stats = ColumnStatistics.objects.filter(
            table_name=source_table,
            column_name=source_col['name']
        ).first()
        
        target_stats = ColumnStatistics.objects.filter(
            table_name=target_table,
            column_name=target_col['name']
        ).first()
        
        # 4. Inclusión de dominio
        domain_score = self._calculate_domain_inclusion(
            source_stats,
            target_stats
        ) if (source_stats and target_stats) else 0.0
        
        # 5. Score de unicidad (maestro-detalle)
        uniqueness_score = self._calculate_uniqueness_score(
            source_stats,
            target_stats
        ) if (source_stats and target_stats) else 0.0
        
        # 6. Determinar cardinalidad
        cardinality = self._infer_cardinality(source_stats, target_stats)
        
        # 7. Calcular confianza total (pesado)
        weights = {
            'name': 0.35,      # Nombre es muy importante
            'type': 0.20,      # Tipo debe ser compatible
            'domain': 0.25,    # Inclusión de valores
            'uniqueness': 0.20 # Unicidad del maestro
        }
        
        confidence = (
            weights['name'] * name_score +
            weights['type'] * type_score +
            weights['domain'] * domain_score +
            weights['uniqueness'] * uniqueness_score
        )
        
        return {
            'source_table': source_table,
            'source_column': source_col['name'],
            'target_table': target_table,
            'target_column': target_col['name'],
            'confidence': confidence,
            'name_match_score': name_score,
            'type_compatibility': type_score,
            'domain_inclusion': domain_score,
            'uniqueness_score': uniqueness_score,
            'cardinality': cardinality,
            'has_index': source_col['is_key'] or target_col['is_key'],
        }
    
    def _calculate_name_match(
        self,
        source_name: str,
        target_name: str,
        source_table: str,
        target_table: str
    ) -> float:
        """
        Calcula score de coincidencia de nombres
        Considera: exacta, parcial, patterns FK, tabla-columna
        """
        score = 0.0
        
        # Normalizar nombres
        s_norm = self._normalize_name(source_name)
        t_norm = self._normalize_name(target_name)
        
        # 1. Coincidencia exacta (máximo score)
        if s_norm == t_norm:
            return 1.0
        
        # 2. Patrones de FK
        for pattern in self.FK_PATTERNS:
            s_match = re.match(pattern, source_name, re.IGNORECASE)
            t_match = re.match(pattern, target_name, re.IGNORECASE)
            
            if s_match and t_match:
                s_entity = self._normalize_name(s_match.group(1))
                t_entity = self._normalize_name(t_match.group(1))
                
                if s_entity == t_entity:
                    score = max(score, 0.9)
        
        # 3. Relación tabla → columna
        # Ej: tabla "Cliente" con columna "IDCliente" en otra tabla
        table_norm = self._normalize_name(target_table)
        if table_norm in s_norm or s_norm in table_norm:
            score = max(score, 0.85)
        
        # 4. Similitud de secuencia
        similarity = SequenceMatcher(None, s_norm, t_norm).ratio()
        if similarity > 0.7:
            score = max(score, similarity * 0.7)
        
        # 5. Contiene el mismo sufijo/prefijo significativo
        if (s_norm.endswith(t_norm[-4:]) or t_norm.endswith(s_norm[-4:])) and len(s_norm) > 4:
            score = max(score, 0.6)
        
        return min(score, 1.0)
    
    def _normalize_name(self, name: str) -> str:
        """Normaliza nombre de columna/tabla para comparación"""
        # Remover prefijos/sufijos comunes
        name = re.sub(r'^(ID_?|Cod_?|FK_)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'(_?ID|_?Cod|_?Key)$', '', name, flags=re.IGNORECASE)
        
        # Minúsculas
        return name.lower()
    
    def _calculate_type_compatibility(self, type1: str, type2: str) -> float:
        """Calcula compatibilidad de tipos de datos"""
        # Normalizar tipos
        t1 = type1.lower()
        t2 = type2.lower()
        
        # Buscar en matriz de compatibilidad
        for (t_a, t_b), score in self.TYPE_COMPATIBILITY.items():
            if (t1.startswith(t_a) and t2.startswith(t_b)) or \
               (t1.startswith(t_b) and t2.startswith(t_a)):
                return score
        
        # Sin compatibilidad
        return 0.0
    
    def _calculate_domain_inclusion(
        self,
        source_stats: ColumnStatistics,
        target_stats: ColumnStatistics
    ) -> float:
        """
        Calcula qué porcentaje de valores de source están en target
        Alta inclusión sugiere FK válida
        """
        if not source_stats or not target_stats:
            return 0.0
        
        # Obtener valores de muestra
        source_values = set(v['value'] for v in source_stats.sample_values)
        target_values = set(v['value'] for v in target_stats.sample_values)
        
        if not source_values or not target_values:
            return 0.0
        
        # Calcular intersección
        intersection = source_values.intersection(target_values)
        
        # Porcentaje de valores de source que están en target
        inclusion_rate = len(intersection) / len(source_values)
        
        return inclusion_rate
    
    def _calculate_uniqueness_score(
        self,
        source_stats: ColumnStatistics,
        target_stats: ColumnStatistics
    ) -> float:
        """
        Score basado en unicidad:
        - Target único/PK = buen candidato a maestro
        - Source no único = buen candidato a detalle/FK
        """
        if not source_stats or not target_stats:
            return 0.0
        
        score = 0.0
        
        # Target es único → +0.5
        if target_stats.is_unique:
            score += 0.5
        
        # Source NO es único → +0.3
        if not source_stats.is_unique:
            score += 0.3
        
        # Alta cardinalidad en source vs target → +0.2
        if target_stats.unique_count > 0:
            ratio = source_stats.total_count / target_stats.unique_count
            if ratio > 2:  # Varios registros source por cada target
                score += 0.2
        
        return min(score, 1.0)
    
    def _infer_cardinality(
        self,
        source_stats: Optional[ColumnStatistics],
        target_stats: Optional[ColumnStatistics]
    ) -> str:
        """Infiere cardinalidad de la relación"""
        if not source_stats or not target_stats:
            return 'N:1'  # Default
        
        source_unique = source_stats.is_unique
        target_unique = target_stats.is_unique
        
        if source_unique and target_unique:
            return '1:1'
        elif source_unique and not target_unique:
            return '1:N'
        elif not source_unique and target_unique:
            return 'N:1'
        else:
            return 'N:M'
    
    def _save_relationship(self, data: Dict):
        """Guarda o actualiza una relación en el catálogo"""
        defaults = {
            'confidence_score': data['confidence'],
            'name_match_score': data['name_match_score'],
            'type_compatibility': data['type_compatibility'],
            'domain_inclusion': data['domain_inclusion'],
            'uniqueness_score': data['uniqueness_score'],
            'cardinality': data['cardinality'],
            'has_index': data['has_index'],
        }
        
        # Si viene del Logic Interpreter, marcarlo
        if data.get('logic_interpreter_hint', False):
            defaults['logic_interpreter_hint'] = True
        
        RelationshipCandidate.objects.update_or_create(
            source_table=data['source_table'],
            source_column=data['source_column'],
            target_table=data['target_table'],
            target_column=data['target_column'],
            defaults=defaults
        )
    
    def enrich_from_logic_interpreter(self, persistence_map: Dict):
        """
        Enriquece relaciones con hints del Logic Interpreter
        Aumenta la confianza de relaciones sugeridas
        """
        if not persistence_map or 'relaciones_candidatas' not in persistence_map:
            return
        
        for rel in persistence_map['relaciones_candidatas']:
            # Extraer tabla.campo → tabla.campo
            origen = rel.get('origen', '')
            destino = rel.get('destino', '')
            
            if '.' not in origen or '.' not in destino:
                continue
            
            source_table, source_col = origen.split('.', 1)
            target_table, target_col = destino.split('.', 1)
            
            # Buscar o crear la relación
            relationship, created = RelationshipCandidate.objects.get_or_create(
                source_table=source_table,
                source_column=source_col,
                target_table=target_table,
                target_column=target_col
            )
            
            # Marcar como sugerida por Logic Interpreter
            relationship.logic_interpreter_hint = True
            relationship.update_confidence()  # Recalcular con el hint
            relationship.save()
    
    def get_best_join_path(
        self,
        source_table: str,
        target_table: str,
        min_confidence: float = 0.7
    ) -> List[Dict]:
        """
        Encuentra la mejor ruta de joins entre dos tablas
        Retorna lista de relaciones a usar
        """
        # Implementación simple: buscar relación directa primero
        direct = RelationshipCandidate.objects.filter(
            source_table=source_table,
            target_table=target_table,
            confidence_score__gte=min_confidence
        ).order_by('-confidence_score').first()
        
        if direct:
            return [{
                'source_table': direct.source_table,
                'source_column': direct.source_column,
                'target_table': direct.target_table,
                'target_column': direct.target_column,
                'confidence': direct.confidence_score
            }]
        
        # TODO: Implementar búsqueda de camino con grafo (BFS/Dijkstra)
        # Por ahora, retornar vacío si no hay ruta directa
        return []
    
    def _get_logic_interpreter_context(self) -> Optional[Dict]:
        """
        Obtiene contexto del Logic Interpreter:
        - Business Rules con entidades mencionadas
        - Relaciones sugeridas desde VB6/PHP
        - Field Usage Maps
        """
        from ..models import BusinessRule
        
        try:
            # Obtener todas las Business Rules activas
            rules = BusinessRule.objects.filter(is_active=True)
            
            # Extraer relaciones sugeridas de las reglas
            suggested_relationships = []
            entities_found = set()
            
            for rule in rules:
                # Extraer entidades mencionadas
                entities = self._extract_entities_from_rule(rule)
                entities_found.update(entities)
                
                # Si la regla tiene información de persistencia, extraerla
                if rule.business_procedure:
                    rels = self._extract_relationships_from_procedure(rule.business_procedure)
                    suggested_relationships.extend(rels)
            
            context = {
                'business_rules_count': rules.count(),
                'entities': list(entities_found),
                'suggested_relationships': suggested_relationships,
                'suggested_relationships_count': len(suggested_relationships)
            }
            
            return context
        
        except Exception as e:
            print(f"   ⚠️ Error obteniendo contexto del Logic Interpreter: {e}")
            return None
    
    def _extract_entities_from_rule(self, rule: 'BusinessRule') -> Set[str]:
        """
        Extrae entidades mencionadas en una Business Rule
        Busca palabras clave comunes de administraNET
        """
        entities = set()
        
        # Entidades comunes de administraNET
        common_entities = [
            'cliente', 'clientes', 'proveedor', 'proveedores',
            'articulo', 'articulos', 'producto', 'productos',
            'factura', 'facturas', 'pedido', 'pedidos',
            'venta', 'ventas', 'compra', 'compras',
            'stock', 'inventario', 'deposito', 'depositos',
            'provincia', 'provincias', 'localidad', 'localidades',
            'sucursal', 'sucursales', 'empresa', 'empresas'
        ]
        
        # Buscar en descripción y tags
        text = f"{rule.description} {rule.tags}".lower()
        
        for entity in common_entities:
            if entity in text:
                # Normalizar a singular
                normalized = entity.rstrip('s')
                entities.add(normalized)
        
        return entities
    
    def _extract_relationships_from_procedure(self, procedure: str) -> List[Dict]:
        """
        Extrae relaciones potenciales desde un procedimiento de negocio
        Busca patrones como "Cliente → Pedido", "Pedido.IDCliente → Cliente.IDCliente"
        """
        relationships = []
        
        # Buscar patrones de relaciones explícitas
        import re
        
        # Patrón: Tabla.Campo → Tabla.Campo
        pattern = r'(\w+)\.(\w+)\s*(?:→|->|↔|<->)\s*(\w+)\.(\w+)'
        matches = re.findall(pattern, procedure)
        
        for match in matches:
            source_table, source_col, target_table, target_col = match
            relationships.append({
                'source_table': source_table,
                'source_column': source_col,
                'target_table': target_table,
                'target_column': target_col,
                'source': 'business_procedure'
            })
        
        # Patrón: menciones de tablas relacionadas
        # Ej: "actualizar Cliente y Pedido"
        entity_pattern = r'\b(cliente|pedido|factura|articulo|proveedor|stock|provincia)\b'
        entities = re.findall(entity_pattern, procedure.lower())
        
        # Si hay múltiples entidades, inferir posibles relaciones
        if len(entities) >= 2:
            for i in range(len(entities) - 1):
                relationships.append({
                    'entity_source': entities[i],
                    'entity_target': entities[i + 1],
                    'source': 'entity_proximity',
                    'confidence_hint': 0.5  # Menor confianza por inferencia
                })
        
        return relationships
    
    def _enrich_with_logic_context(
        self,
        relationship_data: Dict,
        logic_context: Dict
    ) -> bool:
        """
        Enriquece una relación con información del Logic Interpreter
        Retorna True si se enriqueció
        """
        enriched = False
        
        # Normalizar nombres de tablas a minúsculas para comparación
        source_table_norm = relationship_data['source_table'].lower()
        target_table_norm = relationship_data['target_table'].lower()
        
        # 1. Verificar si la relación está en las sugerencias del Logic Interpreter
        for suggested in logic_context['suggested_relationships']:
            if 'source_table' in suggested and 'target_table' in suggested:
                # Relación explícita
                if (suggested['source_table'].lower() == source_table_norm and
                    suggested['target_table'].lower() == target_table_norm):
                    
                    # Aumentar confianza (+0.10 por confirmación del Logic Interpreter)
                    relationship_data['confidence'] = min(1.0, relationship_data['confidence'] + 0.10)
                    relationship_data['logic_interpreter_hint'] = True
                    enriched = True
                    break
            
            elif 'entity_source' in suggested and 'entity_target' in suggested:
                # Relación por proximidad de entidades
                entity_source = suggested['entity_source']
                entity_target = suggested['entity_target']
                
                # Verificar si las tablas coinciden con las entidades
                if (entity_source in source_table_norm or source_table_norm in entity_source) and \
                   (entity_target in target_table_norm or target_table_norm in entity_target):
                    
                    # Aumentar confianza levemente (+0.05 por hint débil)
                    confidence_boost = suggested.get('confidence_hint', 0.05)
                    relationship_data['confidence'] = min(1.0, relationship_data['confidence'] + confidence_boost)
                    relationship_data['logic_interpreter_hint'] = True
                    enriched = True
                    break
        
        # 2. Verificar si las tablas están en las entidades conocidas
        if not enriched:
            entities = logic_context.get('entities', [])
            source_in_entities = any(ent in source_table_norm for ent in entities)
            target_in_entities = any(ent in target_table_norm for ent in entities)
            
            if source_in_entities and target_in_entities:
                # Ambas tablas son entidades conocidas del negocio
                # Leve aumento de confianza (+0.03)
                relationship_data['confidence'] = min(1.0, relationship_data['confidence'] + 0.03)
                enriched = True
        
        return enriched

