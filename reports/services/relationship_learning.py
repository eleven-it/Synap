"""
Servicio para aprendizaje de relaciones (JOINs) por uso.

El sistema aprende qué relaciones se usan y funcionan correctamente,
priorizándolas en el wizard de relaciones del Builder Visual.
"""

import logging
from typing import List, Dict, Optional, Any
from django.utils import timezone
from django.db import transaction

from ..models import LearnedRelationship

logger = logging.getLogger(__name__)


class RelationshipLearningService:
    """Servicio para gestionar el aprendizaje de relaciones por uso."""
    
    @classmethod
    def record_join_usage(
        cls,
        empresa: Optional[Any],
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        success: bool = True
    ) -> Optional[LearnedRelationship]:
        """
        Registra el uso de una relación (JOIN).
        
        Args:
            empresa: Instancia de Empresa o None (para relaciones globales)
            from_table: Tabla origen
            from_column: Columna origen
            to_table: Tabla destino
            to_column: Columna destino
            success: Si el uso fue exitoso (True) o falló (False)
            
        Returns:
            LearnedRelationship creada/actualizada o None si no se pudo registrar
        """
        # Validaciones
        if not from_table or not from_column or not to_table or not to_column:
            logger.warning("⚠️ Intento de registrar relación con campos vacíos")
            return None
        
        # Obtener ID de empresa si existe
        empresa_id = empresa.id if empresa and hasattr(empresa, 'id') else None
        
        try:
            with transaction.atomic():
                # Buscar o crear relación aprendida
                learned_rel, created = LearnedRelationship.objects.get_or_create(
                    empresa_id=empresa_id,
                    from_table=from_table,
                    from_column=from_column,
                    to_table=to_table,
                    to_column=to_column,
                    defaults={
                        'confidence': 0.5,
                        'source': 'usage',
                        'usage_count': 0,
                        'success_count': 0,
                        'status': LearnedRelationship.RelationshipStatus.PROPOSED,  # Por defecto, propuesta
                    }
                )
                
                # Si está bloqueada, no actualizar
                if learned_rel.is_blocked:
                    logger.debug(f"🔒 Relación bloqueada, no se actualiza: {from_table}.{from_column} → {to_table}.{to_column}")
                    return None
                
                # Actualizar estadísticas
                learned_rel.usage_count += 1
                if success:
                    learned_rel.success_count += 1
                    # Incrementar confidence (máximo 0.99)
                    learned_rel.confidence = min(0.99, learned_rel.confidence + 0.03)
                    
                    # Si la confianza es alta (>=0.9) y tiene varios éxitos, auto-aprobar
                    if learned_rel.confidence >= 0.9 and learned_rel.success_count >= 5:
                        if learned_rel.status == LearnedRelationship.RelationshipStatus.PROPOSED:
                            learned_rel.status = LearnedRelationship.RelationshipStatus.APPROVED
                            logger.info(f"✅ Relación auto-aprobada por alta confianza y uso exitoso: {from_table}.{from_column} → {to_table}.{to_column}")
                else:
                    # Decrementar confidence (mínimo 0.05)
                    learned_rel.confidence = max(0.05, learned_rel.confidence - 0.05)
                
                learned_rel.last_used_at = timezone.now()
                learned_rel.save()
                
                action = "Creada" if created else "Actualizada"
                logger.info(f"✅ {action} relación aprendida: {from_table}.{from_column} → {to_table}.{to_column} (conf: {learned_rel.confidence:.2f})")
                
                return learned_rel
                
        except Exception as e:
            logger.error(f"❌ Error registrando uso de relación: {e}", exc_info=True)
            return None
    
    @classmethod
    def get_learned_relationships(
        cls,
        empresa: Optional[Any],
        from_table: str,
        include_proposed: bool = False,
        min_confidence_proposed: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Obtiene relaciones aprendidas para una tabla origen.
        Filtra por estado: siempre incluye APPROVED, y opcionalmente PROPOSED si cumplen threshold.
        Ignora DEPRECATED y bloqueadas.
        
        Args:
            empresa: Instancia de Empresa o None
            from_table: Tabla origen
            include_proposed: Si True, incluye relaciones PROPOSED con confianza >= min_confidence_proposed
            min_confidence_proposed: Confianza mínima para incluir relaciones PROPOSED (default 0.8)
            
        Returns:
            Lista de diccionarios con relaciones aprendidas, ordenadas por ranking
        """
        from django.db.models import Q
        
        empresa_id = empresa.id if empresa and hasattr(empresa, 'id') else None
        
        try:
            # Construir filtro de status
            status_filter = Q(status=LearnedRelationship.RelationshipStatus.APPROVED)
            if include_proposed:
                status_filter |= Q(
                    status=LearnedRelationship.RelationshipStatus.PROPOSED,
                    confidence__gte=min_confidence_proposed
                )
            
            # Obtener relaciones empresa-specific
            empresa_rels = LearnedRelationship.objects.filter(
                empresa_id=empresa_id,
                from_table=from_table,
                is_blocked=False
            ).filter(status_filter).order_by('-confidence', '-last_used_at', '-success_count')
            
            # Obtener relaciones globales (empresa NULL) como fallback
            global_rels = LearnedRelationship.objects.filter(
                empresa_id__isnull=True,
                from_table=from_table,
                is_blocked=False
            ).filter(status_filter).order_by('-confidence', '-last_used_at', '-success_count')
            
            # Convertir a diccionarios
            result = []
            seen_keys = set()
            
            # Primero agregar relaciones empresa-specific (prioridad)
            for rel in empresa_rels:
                key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
                if key not in seen_keys:
                    seen_keys.add(key)
                    # Determinar badge según status
                    if rel.status == LearnedRelationship.RelationshipStatus.APPROVED:
                        badge = 'Recomendado'
                    elif rel.status == LearnedRelationship.RelationshipStatus.PROPOSED:
                        badge = 'Propuesta'
                    else:
                        badge = 'Recomendado'  # Fallback
                    
                    result.append({
                        'from_table': rel.from_table,
                        'from_column': rel.from_column,
                        'to_table': rel.to_table,
                        'to_column': rel.to_column,
                        'confidence': rel.confidence,
                        'source': rel.source or 'usage',
                        'status': rel.status,
                        'badge': badge,
                        'usage_count': rel.usage_count,
                        'success_count': rel.success_count,
                        'last_used_at': rel.last_used_at.isoformat() if rel.last_used_at else None,
                    })
            
            # Luego agregar relaciones globales (si no están ya incluidas)
            for rel in global_rels:
                key = (rel.from_table, rel.from_column, rel.to_table, rel.to_column)
                if key not in seen_keys:
                    seen_keys.add(key)
                    # Determinar badge según status
                    if rel.status == LearnedRelationship.RelationshipStatus.APPROVED:
                        badge = 'Recomendado'
                    elif rel.status == LearnedRelationship.RelationshipStatus.PROPOSED:
                        badge = 'Propuesta'
                    else:
                        badge = 'Recomendado'  # Fallback
                    
                    result.append({
                        'from_table': rel.from_table,
                        'from_column': rel.from_column,
                        'to_table': rel.to_table,
                        'to_column': rel.to_column,
                        'confidence': rel.confidence,
                        'source': rel.source or 'usage',
                        'status': rel.status,
                        'badge': badge,
                        'usage_count': rel.usage_count,
                        'success_count': rel.success_count,
                        'last_used_at': rel.last_used_at.isoformat() if rel.last_used_at else None,
                    })
            
            logger.debug(f"📚 {len(result)} relaciones aprendidas encontradas para {from_table}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo relaciones aprendidas: {e}", exc_info=True)
            return []
    
    @classmethod
    def merge_relationship_sources(
        cls,
        fk_or_heuristic_rels: List[Dict[str, Any]],
        learned_rels: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Une y ordena relaciones de diferentes fuentes (FK/heurística + aprendidas).
        
        Args:
            fk_or_heuristic_rels: Relaciones de foreign keys o heurísticas
            learned_rels: Relaciones aprendidas por uso
            
        Returns:
            Lista unificada y ordenada de relaciones
        """
        # Crear diccionario para merge por clave única
        merged = {}
        
        # Agregar relaciones aprendidas primero (mayor prioridad)
        for rel in learned_rels:
            key = (
                rel.get('from_table', ''),
                rel.get('from_column', ''),
                rel.get('to_table', ''),
                rel.get('to_column', '')
            )
            if all(key):  # Solo agregar si todos los campos están presentes
                merged[key] = {
                    'from_table': rel.get('from_table'),
                    'from_column': rel.get('from_column'),
                    'to_table': rel.get('to_table'),
                    'to_column': rel.get('to_column'),
                    'confidence': rel.get('confidence', 0.5),
                    'source': rel.get('source', 'usage'),
                    'badge': rel.get('badge', 'Recomendado'),
                    'label': rel.get('label'),
                    'description': rel.get('description'),
                    'cardinality': rel.get('cardinality'),
                }
        
        # Agregar relaciones FK/heurísticas (si no están ya incluidas)
        for rel in fk_or_heuristic_rels:
            key = (
                rel.get('from_table', ''),
                rel.get('from_column', ''),
                rel.get('to_table', ''),
                rel.get('to_column', '')
            )
            if all(key):
                if key not in merged:
                    # Nueva relación
                    source = rel.get('source', 'heuristic')
                    badge = 'Detectado' if source == 'foreign_key' else 'Sugerido'
                    merged[key] = {
                        'from_table': rel.get('from_table'),
                        'from_column': rel.get('from_column'),
                        'to_table': rel.get('to_table'),
                        'to_column': rel.get('to_column'),
                        'confidence': rel.get('confidence', 0.5),
                        'source': source,
                        'badge': badge,
                        'label': rel.get('label'),
                        'description': rel.get('description'),
                        'cardinality': rel.get('cardinality'),
                    }
                else:
                    # Ya existe (probablemente aprendida), mejorar metadata
                    existing = merged[key]
                    # Usar mayor confidence
                    existing['confidence'] = max(
                        existing.get('confidence', 0.5),
                        rel.get('confidence', 0.5)
                    )
                    # Agregar tags si es necesario
                    if existing.get('source') == 'usage' and source == 'foreign_key':
                        existing['badge'] = 'Recomendado'  # Mantener badge de aprendida
        
        # Convertir a lista y ordenar
        result = list(merged.values())
        
        # Ordenar por:
        # 1. Badge (Recomendado > Propuesta > Detectado > Sugerido)
        # 2. Confidence (mayor primero)
        badge_order = {'Recomendado': 0, 'Propuesta': 1, 'Detectado': 2, 'Sugerido': 3}
        result.sort(
            key=lambda x: (
                badge_order.get(x.get('badge', 'Sugerido'), 3),
                -x.get('confidence', 0.5)
            )
        )
        
        logger.debug(f"🔀 {len(result)} relaciones unificadas después de merge")
        return result
    
    @classmethod
    def block_relationship(
        cls,
        empresa: Optional[Any],
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str
    ) -> bool:
        """
        Bloquea una relación aprendida (no se sugerirá ni aprenderá).
        
        Args:
            empresa: Instancia de Empresa o None
            from_table: Tabla origen
            from_column: Columna origen
            to_table: Tabla destino
            to_column: Columna destino
            
        Returns:
            True si se bloqueó exitosamente, False en caso contrario
        """
        empresa_id = empresa.id if empresa and hasattr(empresa, 'id') else None
        
        try:
            learned_rel = LearnedRelationship.objects.get(
                empresa_id=empresa_id,
                from_table=from_table,
                from_column=from_column,
                to_table=to_table,
                to_column=to_column
            )
            learned_rel.is_blocked = True
            learned_rel.save()
            logger.info(f"🔒 Relación bloqueada: {from_table}.{from_column} → {to_table}.{to_column}")
            return True
        except LearnedRelationship.DoesNotExist:
            logger.warning(f"⚠️ Relación no encontrada para bloquear: {from_table}.{from_column} → {to_table}.{to_column}")
            return False
        except Exception as e:
            logger.error(f"❌ Error bloqueando relación: {e}", exc_info=True)
            return False





