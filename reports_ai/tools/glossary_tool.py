"""
Herramienta de Glosario Funcional de Administranet
Gestiona términos de negocio, definiciones y sinónimos
"""
import logging
from typing import Dict, List, Any, Optional
from django.core.cache import cache
from django.db import models
from reports_ai.models import GlossaryTerm

logger = logging.getLogger(__name__)


class GlossaryTool:
    """
    Gestiona el glosario de términos funcionales de Administranet
    Proporciona definiciones consistentes para los agentes
    """
    
    CACHE_PREFIX = 'glossary_term_'
    CACHE_TIMEOUT = 3600  # 1 hora
    
    def __init__(self):
        """Inicializa la herramienta de glosario"""
        self._ensure_base_glossary()
    
    def _ensure_base_glossary(self):
        """
        Asegura que existan términos básicos del glosario
        Se ejecuta en la inicialización
        """
        base_terms = [
            {
                'term': 'Venta Neta',
                'definition': 'Ventas registradas en el periodo menos notas de crédito y ajustes comerciales aplicables al mismo periodo de corte.',
                'synonyms': ['ventas netas', 'venta total ajustada'],
                'category': 'Ventas',
                'examples': ['Ventas netas de septiembre', 'Venta neta por sucursal']
            },
            {
                'term': 'Cliente Activo',
                'definition': 'Cliente con al menos una operación de compra registrada en los últimos 90 días.',
                'synonyms': ['cliente vigente', 'cliente con actividad'],
                'category': 'Clientes',
                'examples': ['Clientes activos del trimestre', 'Total de clientes activos']
            },
            {
                'term': 'Pedido Pendiente',
                'definition': 'Pedido emitido y no completamente entregado o facturado a la fecha de corte.',
                'synonyms': ['orden pendiente', 'pedido sin completar'],
                'category': 'Ventas',
                'examples': ['Pedidos pendientes por antigüedad', 'Total de pedidos sin facturar']
            },
            {
                'term': 'Margen Bruto',
                'definition': 'Diferencia entre el precio de venta y el costo de adquisición o producción, expresada en porcentaje.',
                'synonyms': ['margen de ganancia', 'rentabilidad bruta'],
                'category': 'Finanzas',
                'examples': ['Margen bruto por línea de producto', 'Margen promedio']
            },
            {
                'term': 'Stock Disponible',
                'definition': 'Cantidad de producto en inventario disponible para venta, excluyendo reservas y productos en tránsito.',
                'synonyms': ['inventario disponible', 'existencias disponibles'],
                'category': 'Inventario',
                'examples': ['Stock disponible por depósito', 'Productos sin stock']
            },
            {
                'term': 'Rotación de Stock',
                'definition': 'Medida de la velocidad con la que se vende y repone el inventario en un periodo determinado.',
                'synonyms': ['rotación de inventario', 'velocidad de venta'],
                'category': 'Inventario',
                'examples': ['Rotación mensual de productos', 'Artículos de baja rotación']
            },
        ]
        
        for term_data in base_terms:
            # Crear solo si no existe
            GlossaryTerm.objects.get_or_create(
                term=term_data['term'],
                defaults={
                    'definition': term_data['definition'],
                    'synonyms': term_data['synonyms'],
                    'category': term_data['category'],
                    'examples': term_data['examples'],
                    'is_active': True
                }
            )
    
    def get_definition(self, term: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene la definición de un término
        
        Args:
            term: Término a buscar
            
        Returns:
            Dict con definición y metadatos o None
        """
        # Buscar en cache
        cache_key = f"{self.CACHE_PREFIX}{term.lower()}"
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        # Buscar en base de datos (exacto o por sinónimo)
        try:
            # Búsqueda exacta
            glossary_term = GlossaryTerm.objects.filter(
                term__iexact=term,
                is_active=True
            ).first()
            
            if not glossary_term:
                # Búsqueda por sinónimo
                all_terms = GlossaryTerm.objects.filter(is_active=True)
                for gt in all_terms:
                    if term.lower() in [s.lower() for s in gt.synonyms]:
                        glossary_term = gt
                        break
            
            if glossary_term:
                result = {
                    'term': glossary_term.term,
                    'definition': glossary_term.definition,
                    'synonyms': glossary_term.synonyms,
                    'category': glossary_term.category,
                    'examples': glossary_term.examples
                }
                
                # Guardar en cache
                cache.set(cache_key, result, self.CACHE_TIMEOUT)
                
                return result
            
        except Exception as e:
            logger.error(f"Error buscando término en glosario: {e}")
        
        return None
    
    def search_terms(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Busca términos que coincidan con la consulta
        
        Args:
            query: Texto de búsqueda
            category: Filtrar por categoría (opcional)
            
        Returns:
            Lista de términos coincidentes
        """
        try:
            queryset = GlossaryTerm.objects.filter(is_active=True)
            
            if category:
                queryset = queryset.filter(category__iexact=category)
            
            # Búsqueda en término o definición
            queryset = queryset.filter(
                models.Q(term__icontains=query) |
                models.Q(definition__icontains=query)
            )
            
            results = []
            for term in queryset[:10]:  # Límite de 10 resultados
                results.append({
                    'term': term.term,
                    'definition': term.definition,
                    'category': term.category
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error buscando términos: {e}")
            return []
    
    def normalize_term(self, term: str) -> str:
        """
        Normaliza un término a su forma canónica del glosario
        
        Args:
            term: Término a normalizar
            
        Returns:
            Término normalizado o el original si no se encuentra
        """
        definition = self.get_definition(term)
        
        if definition:
            return definition['term']
        
        return term
    
    def get_all_categories(self) -> List[str]:
        """
        Obtiene todas las categorías del glosario
        
        Returns:
            Lista de categorías únicas
        """
        try:
            categories = GlossaryTerm.objects.filter(
                is_active=True
            ).values_list('category', flat=True).distinct()
            
            return list(categories)
            
        except Exception as e:
            logger.error(f"Error obteniendo categorías: {e}")
            return []
    
    def add_term(
        self,
        term: str,
        definition: str,
        category: str,
        synonyms: Optional[List[str]] = None,
        examples: Optional[List[str]] = None
    ) -> bool:
        """
        Agrega un nuevo término al glosario
        
        Args:
            term: Término a agregar
            definition: Definición en lenguaje de negocio
            category: Categoría del término
            synonyms: Lista de sinónimos
            examples: Lista de ejemplos de uso
            
        Returns:
            True si se agregó exitosamente
        """
        try:
            GlossaryTerm.objects.create(
                term=term,
                definition=definition,
                category=category,
                synonyms=synonyms or [],
                examples=examples or [],
                is_active=True
            )
            
            logger.info(f"Término agregado al glosario: {term}")
            return True
            
        except Exception as e:
            logger.error(f"Error agregando término al glosario: {e}")
            return False
    
    def get_terms_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los términos de una categoría
        
        Args:
            category: Nombre de la categoría
            
        Returns:
            Lista de términos
        """
        try:
            terms = GlossaryTerm.objects.filter(
                category__iexact=category,
                is_active=True
            ).order_by('term')
            
            return [
                {
                    'term': t.term,
                    'definition': t.definition,
                    'synonyms': t.synonyms
                }
                for t in terms
            ]
            
        except Exception as e:
            logger.error(f"Error obteniendo términos por categoría: {e}")
            return []

