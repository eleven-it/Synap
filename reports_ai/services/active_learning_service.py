"""
Active Learning Service para Data Analyst V2

Lee correcciones marcadas como "applied" y entrena el agente
con patrones correctos de generación de SQL.
"""
import logging
import json
from typing import Dict, List, Any, Optional
from django.utils import timezone
from datetime import timedelta

from reports_ai.models import QueryCorrection

logger = logging.getLogger(__name__)


class ActiveLearningService:
    """
    Servicio para active learning basado en correcciones humanas
    """
    
    def __init__(self):
        self.learnings = {}
        self.last_training = None
    
    def load_applied_corrections(self) -> List[QueryCorrection]:
        """
        Carga todas las correcciones marcadas como aplicadas
        
        Returns:
            Lista de correcciones aplicadas
        """
        corrections = QueryCorrection.objects.filter(
            applied_to_catalog=True
        ).order_by('-corrected_at')
        
        logger.info(f"[ActiveLearning] 📚 Cargadas {len(corrections)} correcciones aplicadas")
        
        return corrections
    
    def extract_learnings(self, corrections: List[QueryCorrection]) -> Dict[str, Any]:
        """
        Extrae patrones de aprendizaje de las correcciones
        
        Returns:
            Dict con diferentes tipos de learnings
        """
        learnings = {
            'keyword_to_table': {},  # "cliente" -> "cliente"
            'table_relationships': [],  # "cliente" -> "comp_ped" (via Codigo)
            'column_avoid': [],  # Columnas que NO usar
            'column_prefer': [],  # Columnas preferidas
            'join_patterns': [],  # Patrones de JOIN
            'filter_patterns': [],  # Patrones de filtros
        }
        
        for correction in corrections:
            if correction.correction_notes:
                # Analizar notas para extraer patrones
                self._extract_from_notes(correction, learnings)
            
            if correction.original_sql and correction.corrected_sql:
                # Comparar SQL incorrecto vs correcto
                self._extract_from_sql_comparison(correction, learnings)
            
            # Extraer keywords de la query original
            self._extract_keywords(correction.original_query, learnings)
        
        logger.info(
            f"[ActiveLearning] ✅ Learnings extraídos\n"
            f"  📝 Keywords → Tabla: {len(learnings['keyword_to_table'])}\n"
            f"  🔗 Relaciones: {len(learnings['table_relationships'])}\n"
            f"  ❌ Columnas a evitar: {len(learnings['column_avoid'])}\n"
            f"  ✓ Columnas preferidas: {len(learnings['column_prefer'])}"
        )
        
        return learnings
    
    def _extract_from_notes(self, correction: QueryCorrection, learnings: Dict):
        """
        Extrae patrones de las notas de corrección
        """
        notes = correction.correction_notes.lower()
        
        # Buscar referencias a tablas
        if 'no existe' in notes or 'tabla incorrecta' in notes:
            # Extraer nombre de tabla mencionada
            # Patrón simple: buscar mayúsculas o palabras después de "tabla"
            pass
        
        # Buscar columnas a evitar
        if 'columna' in notes and ('no existe' in notes or 'incorrecta' in notes):
            learnings['column_avoid'].append({
                'table': None,  # Se infiere del SQL
                'column': None,
                'reason': notes,
                'correction_id': correction.id
            })
        
        # Buscar JOINs faltantes
        if 'join' in notes or 'relacion' in notes:
            learnings['join_patterns'].append({
                'type': correction.correction_type,
                'notes': notes,
                'correction_id': correction.id
            })
    
    def _extract_from_sql_comparison(self, correction: QueryCorrection, learnings: Dict):
        """
        Compara SQL incorrecto vs correcto para extraer patrones
        """
        original = correction.original_sql.lower()
        corrected = correction.corrected_sql.lower()
        
        # Detectar si se cambió una tabla
        # Patrón simple: buscar FROM en ambos
        import re
        
        original_from = re.search(r'from\s+(\w+)', original)
        corrected_from = re.search(r'from\s+(\w+)', corrected)
        
        if original_from and corrected_from:
            orig_table = original_from.group(1)
            corr_table = corrected_from.group(1)
            
            if orig_table != corr_table:
                learnings['table_relationships'].append({
                    'wrong_table': orig_table,
                    'correct_table': corr_table,
                    'correction_id': correction.id
                })
        
        # Detectar si se agregaron JOINs
        if 'join' in corrected and 'join' not in original:
            learnings['join_patterns'].append({
                'added': True,
                'sql': corrected,
                'correction_id': correction.id
            })
    
    def _extract_keywords(self, query: str, learnings: Dict):
        """
        Extrae keywords de la query y mapea a tablas
        """
        query_lower = query.lower()
        
        # Mapeo básico de keywords
        keyword_table_map = {
            'cliente': 'cliente',
            'client': 'cliente',
            'articulo': 'articulo',
            'article': 'articulo',
            'producto': 'articulo',
            'product': 'articulo',
            'pedido': 'comp_ped',
            'order': 'comp_ped',
            'venta': 'comp_ped',
            'sale': 'comp_ped',
            'factura': 'comprobante',
            'invoice': 'comprobante',
            'stock': 'stock',
            'inventario': 'stock',
            'inventory': 'stock'
        }
        
        for keyword, table in keyword_table_map.items():
            if keyword in query_lower:
                if table not in learnings['keyword_to_table']:
                    learnings['keyword_to_table'][keyword] = []
                learnings['keyword_to_table'][keyword].append({
                    'table': table,
                    'confidence': 1.0,
                    'source': 'active_learning'
                })
    
    def apply_learnings_to_agent(self, agent, learnings: Dict):
        """
        Aplica los learnings al Data Analyst V2
        
        Args:
            agent: Instancia de DataAnalystAgentV2
            learnings: Dict con los patrones aprendidos
        """
        # Guardar learnings en el agente
        if not hasattr(agent, 'active_learnings'):
            agent.active_learnings = learnings
        else:
            # Merge con learnings existentes
            agent.active_learnings['keyword_to_table'].update(learnings['keyword_to_table'])
            agent.active_learnings['table_relationships'].extend(learnings['table_relationships'])
            agent.active_learnings['column_avoid'].extend(learnings['column_avoid'])
            agent.active_learnings['column_prefer'].extend(learnings['column_prefer'])
            agent.active_learnings['join_patterns'].extend(learnings['join_patterns'])
        
        logger.info(f"[ActiveLearning] ✅ Learnings aplicados al agente")
    
    def get_suggestions_for_query(self, query: str, learnings: Dict) -> Dict[str, Any]:
        """
        Obtiene sugerencias para una query basándose en los learnings
        
        Returns:
            Dict con sugerencias de tablas, columnas, joins, etc.
        """
        suggestions = {
            'preferred_tables': [],
            'avoid_columns': [],
            'join_hints': [],
            'filter_hints': []
        }
        
        query_lower = query.lower()
        
        # Buscar tablas sugeridas por keywords
        for keyword, mappings in learnings.get('keyword_to_table', {}).items():
            if keyword in query_lower:
                for mapping in mappings:
                    if mapping['table'] not in suggestions['preferred_tables']:
                        suggestions['preferred_tables'].append({
                            'table': mapping['table'],
                            'confidence': mapping.get('confidence', 0.8),
                            'source': 'active_learning'
                        })
        
        # Cargar columnas a evitar
        suggestions['avoid_columns'] = learnings.get('column_avoid', [])
        
        # Cargar hints de JOIN
        suggestions['join_hints'] = learnings.get('join_patterns', [])
        
        return suggestions
    
    def generate_training_report(self) -> Dict[str, Any]:
        """
        Genera un reporte de training
        
        Returns:
            Dict con estadísticas del training
        """
        corrections = self.load_applied_corrections()
        
        report = {
            'total_corrections': len(corrections),
            'corrections_by_type': {},
            'total_keywords_learned': 0,
            'total_relationships_learned': 0,
            'last_training': self.last_training.isoformat() if self.last_training else None,
            'training_effectiveness': 'N/A'
        }
        
        # Agrupar por tipo
        for correction in corrections:
            corr_type = correction.correction_type
            report['corrections_by_type'][corr_type] = report['corrections_by_type'].get(corr_type, 0) + 1
        
        # Extract learnings para contar
        learnings = self.extract_learnings(corrections)
        report['total_keywords_learned'] = len(learnings['keyword_to_table'])
        report['total_relationships_learned'] = len(learnings['table_relationships'])
        
        return report
    
    def mark_training_complete(self):
        """
        Marca el training como completo
        """
        self.last_training = timezone.now()
        logger.info(f"[ActiveLearning] ✅ Training completado: {self.last_training}")


# Función helper
def get_active_learning_service() -> ActiveLearningService:
    """
    Obtiene una instancia del servicio de active learning
    """
    return ActiveLearningService()

