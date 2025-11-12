"""
Synonym Dictionary Service
Mapea términos de negocio a nombres técnicos de columnas
"""
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
from django.db import connection

from ..models import SynonymMapping, BusinessRule, GlossaryTerm
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService


class SynonymService:
    """
    Servicio para resolver sinónimos: negocio ↔ columnas técnicas
    """
    
    # Patrones comunes de prefijos/sufijos
    PREFIXES = ['ID', 'Cod', 'FK', 'Num', 'Nro']
    SUFFIXES = ['ID', 'Cod', 'Code', 'Key', 'Num']
    
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
    
    def build_synonym_catalog(self):
        """
        Construye el catálogo inicial de sinónimos desde múltiples fuentes:
        - Glosario de términos
        - Business Rules
        - Nombres de columnas del schema
        """
        print("\n📚 Construyendo catálogo de sinónimos...")
        
        # 1. Desde glosario de términos
        self._build_from_glossary()
        
        # 2. Desde business rules (entidades mencionadas)
        self._build_from_business_rules()
        
        # 3. Desde nombres de columnas (auto-descubrimiento)
        self._build_from_schema()
        
        total = SynonymMapping.objects.count()
        print(f"   ✅ Catálogo construido: {total} mapeos")
    
    def _build_from_glossary(self):
        """Construye desde GlossaryTerm"""
        terms = GlossaryTerm.objects.all()
        
        for term in terms:
            # Buscar columnas que coincidan con el término
            patterns = self._generate_column_patterns(term.term)
            
            for pattern in patterns:
                matching_columns = self._find_matching_columns(pattern)
                
                for table, column in matching_columns:
                    SynonymMapping.objects.get_or_create(
                        business_term=term.term.lower(),
                        column_pattern=f"{table}.{column}",
                        defaults={
                            'source': 'glossary',
                            'confidence': 0.7
                        }
                    )
    
    def _build_from_business_rules(self):
        """Extrae entidades mencionadas en Business Rules"""
        rules = BusinessRule.objects.all()
        
        # Entidades comunes de Administranet
        common_entities = [
            'cliente', 'proveedor', 'artículo', 'articulo', 'producto',
            'factura', 'pedido', 'orden', 'compra', 'venta',
            'stock', 'inventario', 'deposito', 'sucursal',
            'provincia', 'localidad', 'ciudad',
            'usuario', 'vendedor', 'cobrador',
            'precio', 'costo', 'total', 'subtotal',
            'fecha', 'estado', 'tipo', 'categoria'
        ]
        
        for entity in common_entities:
            patterns = self._generate_column_patterns(entity)
            
            for pattern in patterns:
                matching_columns = self._find_matching_columns(pattern)
                
                for table, column in matching_columns:
                    SynonymMapping.objects.get_or_create(
                        business_term=entity.lower(),
                        column_pattern=f"{table}.{column}",
                        defaults={
                            'source': 'discovered',
                            'confidence': 0.5
                        }
                    )
    
    def _build_from_schema(self):
        """Auto-descubre sinónimos desde nombres de columnas"""
        conn = self._get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(f"""
                SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{self.db_name}'
            """)
            
            for row in cursor.fetchall():
                table = row['TABLE_NAME']
                column = row['COLUMN_NAME']
                comment = row['COLUMN_COMMENT']
                
                # Extraer término de negocio del nombre de columna
                business_term = self._extract_business_term(column)
                
                if business_term:
                    SynonymMapping.objects.get_or_create(
                        business_term=business_term.lower(),
                        column_pattern=f"{table}.{column}",
                        defaults={
                            'source': 'discovered',
                            'confidence': 0.6
                        }
                    )
                
                # Si hay comentario, también úsalo
                if comment:
                    comment_term = comment.strip().lower()
                    if comment_term and len(comment_term) > 2:
                        SynonymMapping.objects.get_or_create(
                            business_term=comment_term,
                            column_pattern=f"{table}.{column}",
                            defaults={
                                'source': 'discovered',
                                'confidence': 0.8  # Alta confianza por comentario explícito
                            }
                        )
        
        finally:
            cursor.close()
            conn.close()
    
    def _generate_column_patterns(self, term: str) -> List[str]:
        """
        Genera posibles nombres de columnas para un término de negocio
        Ej: 'provincia' -> ['Provincia', 'IDProvincia', 'CodProvincia', 'ProvinciaID', ...]
        """
        patterns = []
        
        # Normalizar término
        term_clean = term.strip()
        term_cap = term_clean.capitalize()
        
        # Patrón base
        patterns.append(term_cap)
        
        # Con prefijos
        for prefix in self.PREFIXES:
            patterns.append(f"{prefix}{term_cap}")
            patterns.append(f"{prefix}_{term_cap}")
        
        # Con sufijos
        for suffix in self.SUFFIXES:
            patterns.append(f"{term_cap}{suffix}")
            patterns.append(f"{term_cap}_{suffix}")
        
        return patterns
    
    def _find_matching_columns(self, pattern: str) -> List[Tuple[str, str]]:
        """
        Busca columnas que coincidan con el patrón
        Retorna lista de (tabla, columna)
        """
        matches = []
        
        conn = self._get_mysql_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Búsqueda exacta
            cursor.execute(f"""
                SELECT TABLE_NAME, COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{self.db_name}'
                AND COLUMN_NAME = '{pattern}'
            """)
            matches.extend([(row['TABLE_NAME'], row['COLUMN_NAME']) for row in cursor.fetchall()])
            
            # Búsqueda con LIKE (case insensitive)
            cursor.execute(f"""
                SELECT TABLE_NAME, COLUMN_NAME
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = '{self.db_name}'
                AND COLUMN_NAME LIKE '%{pattern}%'
            """)
            matches.extend([(row['TABLE_NAME'], row['COLUMN_NAME']) for row in cursor.fetchall()])
            
            # Remover duplicados
            return list(set(matches))
        
        finally:
            cursor.close()
            conn.close()
    
    def _extract_business_term(self, column_name: str) -> Optional[str]:
        """
        Extrae el término de negocio de un nombre de columna
        Ej: 'IDCliente' -> 'cliente'
             'CodProvincia' -> 'provincia'
        """
        # Remover prefijos comunes
        term = re.sub(r'^(ID|Cod|FK|Num|Nro)_?', '', column_name, flags=re.IGNORECASE)
        
        # Remover sufijos comunes
        term = re.sub(r'_?(ID|Cod|Code|Key|Num)$', '', term, flags=re.IGNORECASE)
        
        # Si quedó algo significativo (>2 chars), retornar
        if term and len(term) > 2 and term != column_name:
            return term
        
        return None
    
    def resolve_business_term(
        self,
        term: str,
        context_table: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict]:
        """
        Resuelve un término de negocio a columnas técnicas
        
        Args:
            term: Término de negocio (ej: 'provincia', 'cliente')
            context_table: Tabla de contexto para priorizar
            min_confidence: Confianza mínima
        
        Returns:
            Lista de mapeos ordenados por confianza
        """
        term_lower = term.lower()
        
        # Buscar en catálogo
        mappings = SynonymMapping.objects.filter(
            business_term__icontains=term_lower,
            confidence__gte=min_confidence
        ).order_by('-confidence', '-times_successful')
        
        results = []
        for mapping in mappings:
            # Extraer tabla.columna
            if '.' in mapping.column_pattern:
                table, column = mapping.column_pattern.split('.', 1)
            else:
                table, column = '', mapping.column_pattern
            
            # Priorizar si coincide con tabla de contexto
            score = mapping.confidence
            if context_table and table.lower() == context_table.lower():
                score += 0.2
            
            results.append({
                'table': table,
                'column': column,
                'confidence': min(score, 1.0),
                'times_used': mapping.times_used,
                'source': mapping.source
            })
        
        # Ordenar por confianza final
        results.sort(key=lambda x: (-x['confidence'], -x['times_used']))
        
        return results
    
    def update_success(self, term: str, table: str, column: str):
        """
        Marca un mapeo como exitoso (active learning)
        Aumenta su confianza
        """
        pattern = f"{table}.{column}"
        
        mapping, created = SynonymMapping.objects.get_or_create(
            business_term=term.lower(),
            column_pattern=pattern,
            defaults={
                'source': 'validated',
                'confidence': 0.8
            }
        )
        
        if not created:
            mapping.times_used += 1
            mapping.times_successful += 1
            
            # Aumentar confianza basada en tasa de éxito
            if mapping.times_used > 0:
                success_rate = mapping.times_successful / mapping.times_used
                mapping.confidence = min(0.95, 0.5 + success_rate * 0.4)
            
            mapping.save()
    
    def update_failure(self, term: str, table: str, column: str):
        """
        Marca un mapeo como fallido
        Reduce su confianza
        """
        pattern = f"{table}.{column}"
        
        try:
            mapping = SynonymMapping.objects.get(
                business_term=term.lower(),
                column_pattern=pattern
            )
            
            mapping.times_used += 1
            # No incrementar times_successful
            
            # Reducir confianza
            if mapping.times_used > 0:
                success_rate = mapping.times_successful / mapping.times_used
                mapping.confidence = max(0.1, 0.5 + success_rate * 0.4 - 0.1)
            
            mapping.save()
        
        except SynonymMapping.DoesNotExist:
            # No existe, no hacer nada
            pass
    
    def find_similar_terms(self, term: str, threshold: float = 0.7) -> List[str]:
        """
        Encuentra términos similares en el catálogo
        Útil para sugerencias cuando no hay match exacto
        """
        all_terms = SynonymMapping.objects.values_list('business_term', flat=True).distinct()
        
        similar = []
        for existing_term in all_terms:
            similarity = SequenceMatcher(None, term.lower(), existing_term.lower()).ratio()
            if similarity >= threshold:
                similar.append((existing_term, similarity))
        
        # Ordenar por similitud
        similar.sort(key=lambda x: -x[1])
        
        return [t for t, _ in similar[:5]]  # Top 5

