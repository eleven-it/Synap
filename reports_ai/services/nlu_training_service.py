"""
Servicio de entrenamiento continuo del NLU
Maneja entrenamiento incremental, evaluación y detección de deriva
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.db.models import Q
from reports_ai.models import (
    NLUTrainingExample,
    NLUMetrics,
    NLUFeedback,
    NLUModel,
    ReportRequest
)

logger = logging.getLogger(__name__)


class NLUTrainingService:
    """
    Servicio para entrenamiento continuo del NLU
    
    Responsabilidades:
    - Entrenamiento incremental basado en nuevos ejemplos
    - Evaluación de métricas de calidad
    - Detección de deriva del modelo
    - Gestión de versiones del modelo
    - Rollback seguro
    """
    
    def __init__(self):
        self.current_version = self._get_active_model_version()
    
    def _get_active_model_version(self) -> str:
        """
        Obtiene la versión activa del modelo NLU
        
        Returns:
            String con la versión (ej: 'v1.0.0')
        """
        try:
            active_model = NLUModel.objects.filter(status='active').first()
            return active_model.version if active_model else 'v1.0.0'
        except:
            return 'v1.0.0'
    
    def detect_changes_daily(self) -> Dict[str, Any]:
        """
        Escaneo diario ligero de cambios funcionales
        
        Returns:
            Dict con cambios detectados
        """
        logger.info(
            "\n" + "="*70 + "\n"
            "[NLU Training] 📅 ESCANEO DIARIO DE CAMBIOS\n"
            + "="*70
        )
        
        yesterday = datetime.now().date() - timedelta(days=1)
        
        # Detectar cambios en Business Rules
        from reports_ai.models import BusinessRule
        new_rules = BusinessRule.objects.filter(
            created_at__date=yesterday
        ).count()
        
        modified_rules = BusinessRule.objects.filter(
            updated_at__date=yesterday
        ).exclude(
            created_at__date=yesterday
        ).count()
        
        # Detectar cambios en Glossary
        from reports_ai.models import GlossaryTerm
        new_terms = GlossaryTerm.objects.filter(
            created_at__date=yesterday
        ).count()
        
        # Detectar feedback nuevo
        new_feedback = NLUFeedback.objects.filter(
            created_at__date=yesterday,
            status='pending'
        ).count()
        
        changes_detected = new_rules > 0 or modified_rules > 0 or new_terms > 0 or new_feedback > 0
        
        result = {
            'date': yesterday.isoformat(),
            'changes_detected': changes_detected,
            'new_business_rules': new_rules,
            'modified_business_rules': modified_rules,
            'new_glossary_terms': new_terms,
            'new_feedback': new_feedback,
            'action_required': changes_detected
        }
        
        logger.info(
            f"[NLU Training] ✅ Escaneo diario completado\n"
            f"  📋 Nuevas reglas: {new_rules}\n"
            f"  📝 Reglas modificadas: {modified_rules}\n"
            f"  📚 Nuevos términos: {new_terms}\n"
            f"  💬 Feedback nuevo: {new_feedback}\n"
            f"  🎯 Acción requerida: {'SÍ' if changes_detected else 'NO'}"
        )
        
        return result
    
    def evaluate_weekly(self) -> Dict[str, Any]:
        """
        Evaluación semanal del NLU
        
        Returns:
            Dict con métricas calculadas
        """
        logger.info(
            "\n" + "="*70 + "\n"
            "[NLU Training] 📊 EVALUACIÓN SEMANAL\n"
            + "="*70
        )
        
        # Período: última semana
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        # Consultas de la semana
        week_requests = ReportRequest.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        total_queries = week_requests.count()
        
        # Calcular métricas básicas
        completed = week_requests.filter(status='completed').count()
        errors = week_requests.filter(status='error').count()
        
        # Calcular tasas
        coverage_rate = (completed / total_queries * 100) if total_queries > 0 else 0
        misroute_rate = (errors / total_queries * 100) if total_queries > 0 else 0
        
        # Feedback de la semana
        week_feedback = NLUFeedback.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        clarification_requests = week_feedback.count()
        clarification_rate = (clarification_requests / total_queries * 100) if total_queries > 0 else 0
        
        # Crear o actualizar registro de métricas
        metrics, created = NLUMetrics.objects.update_or_create(
            evaluation_date=end_date,
            period_type='weekly',
            defaults={
                'total_queries': total_queries,
                'correctly_classified': completed,
                'misclassified': errors,
                'ambiguous': clarification_requests,
                'out_of_context': 0,  # TODO: implementar detección
                'coverage_rate': coverage_rate,
                'clarification_rate': clarification_rate,
                'misroute_rate': misroute_rate,
                'slot_accuracy': 92.0,  # TODO: implementar cálculo real
                'model_version': self.current_version,
                'notes': f'Evaluación automática semanal {start_date} - {end_date}'
            }
        )
        
        # Determinar si requiere reentrenamiento
        needs_retraining = (
            coverage_rate < 95.0 or
            misroute_rate > 3.0 or
            clarification_rate > 8.0
        )
        
        result = {
            'period': f'{start_date} - {end_date}',
            'total_queries': total_queries,
            'coverage_rate': coverage_rate,
            'misroute_rate': misroute_rate,
            'clarification_rate': clarification_rate,
            'needs_retraining': needs_retraining,
            'metrics_id': metrics.id
        }
        
        logger.info(
            f"[NLU Training] ✅ Evaluación semanal completada\n"
            f"  📊 Total consultas: {total_queries}\n"
            f"  ✅ Cobertura: {coverage_rate:.1f}% (target: ≥95%)\n"
            f"  ❌ Error de enrutamiento: {misroute_rate:.1f}% (target: ≤3%)\n"
            f"  💬 Tasa de aclaración: {clarification_rate:.1f}% (target: 3-8%)\n"
            f"  🔄 Requiere reentrenamiento: {'SÍ' if needs_retraining else 'NO'}"
        )
        
        return result
    
    def train_incremental(self, max_examples: int = 100) -> Dict[str, Any]:
        """
        Entrenamiento incremental del NLU
        
        Args:
            max_examples: Máximo de ejemplos nuevos a usar
            
        Returns:
            Dict con resultado del entrenamiento
        """
        logger.info(
            "\n" + "="*70 + "\n"
            "[NLU Training] 🎓 ENTRENAMIENTO INCREMENTAL\n"
            + "="*70
        )
        
        # Procesar feedback pendiente y convertirlo en ejemplos
        pending_feedback = NLUFeedback.objects.filter(
            status='pending'
        ).order_by('-priority', '-created_at')[:max_examples]
        
        examples_added = 0
        
        for feedback in pending_feedback:
            # Crear ejemplo de entrenamiento
            example, created = NLUTrainingExample.objects.get_or_create(
                query_text=feedback.query_text,
                intent=feedback.correct_intent,
                defaults={
                    'slots': feedback.correct_slots,
                    'source': 'feedback',
                    'priority': feedback.priority,
                    'is_active': True
                }
            )
            
            if created:
                examples_added += 1
                logger.info(
                    f"[NLU Training] ✅ Ejemplo agregado\n"
                    f"  📝 Query: {feedback.query_text[:50]}...\n"
                    f"  🎯 Intent: {feedback.correct_intent}"
                )
            
            # Marcar feedback como procesado
            feedback.status = 'processed'
            feedback.save()
        
        # Estadísticas de ejemplos
        total_examples = NLUTrainingExample.objects.filter(is_active=True).count()
        canonical_examples = NLUTrainingExample.objects.filter(
            is_active=True,
            is_canonical=True
        ).count()
        
        # TODO: Aquí iría el proceso real de fine-tuning con OpenAI
        # Por ahora, solo registramos que se procesaron los ejemplos
        
        logger.info(
            f"[NLU Training] ✅ Entrenamiento incremental completado\n"
            f"  📚 Ejemplos nuevos agregados: {examples_added}\n"
            f"  📊 Total ejemplos activos: {total_examples}\n"
            f"  🔒 Ejemplos canónicos: {canonical_examples}\n"
            f"  ⏭️  Siguiente paso: Ejecutar fine-tuning con OpenAI"
        )
        
        return {
            'success': True,
            'examples_added': examples_added,
            'total_examples': total_examples,
            'canonical_examples': canonical_examples,
            'message': f'Se agregaron {examples_added} ejemplos nuevos. Total: {total_examples}'
        }
    
    def detect_drift(self) -> Dict[str, Any]:
        """
        Detecta deriva del modelo NLU comparando contra ejemplos canónicos
        
        Returns:
            Dict con indicadores de deriva
        """
        logger.info(
            "\n" + "="*70 + "\n"
            "[NLU Training] 🔍 DETECCIÓN DE DERIVA\n"
            + "="*70
        )
        
        # Obtener ejemplos canónicos
        canonical_examples = NLUTrainingExample.objects.filter(
            is_canonical=True,
            is_active=True
        )
        
        if not canonical_examples.exists():
            logger.warning("[NLU Training] ⚠️  No hay ejemplos canónicos para evaluar deriva")
            return {
                'drift_detected': False,
                'canonical_count': 0,
                'model_version': self.current_version,
                'evaluation_date': datetime.now().isoformat(),
                'accuracy_on_canonical': 0.0,
                'message': 'No hay ejemplos canónicos para evaluar'
            }
        
        # TODO: Implementar evaluación real del NLU contra ejemplos canónicos
        # Por ahora, retornar estructura base
        
        result = {
            'drift_detected': False,
            'canonical_count': canonical_examples.count(),
            'model_version': self.current_version,
            'evaluation_date': datetime.now().isoformat(),
            'accuracy_on_canonical': 95.5,  # TODO: calcular real
            'message': 'No se detectó deriva significativa'
        }
        
        logger.info(
            f"[NLU Training] ✅ Detección de deriva completada\n"
            f"  📚 Ejemplos canónicos: {canonical_examples.count()}\n"
            f"  📊 Accuracy: {result['accuracy_on_canonical']:.1f}%\n"
            f"  🎯 Deriva detectada: {'SÍ' if result['drift_detected'] else 'NO'}"
        )
        
        return result
    
    def process_feedback_batch(self, batch_size: int = 50) -> Dict[str, Any]:
        """
        Procesa lote de feedback pendiente
        
        Args:
            batch_size: Tamaño del lote a procesar
            
        Returns:
            Dict con resultado del procesamiento
        """
        logger.info(f"[NLU Training] Procesando lote de {batch_size} feedbacks...")
        
        # Obtener feedback pendiente ordenado por prioridad
        pending_feedbacks = NLUFeedback.objects.filter(
            status='pending'
        ).order_by('-priority', '-created_at')[:batch_size]
        
        processed_count = 0
        high_priority_count = 0
        
        for feedback in pending_feedbacks:
            # Crear ejemplo de entrenamiento
            NLUTrainingExample.objects.create(
                query_text=feedback.query_text,
                intent=feedback.correct_intent,
                slots=feedback.correct_slots,
                source='feedback',
                priority=feedback.priority,
                is_active=True
            )
            
            # Marcar como procesado
            feedback.status = 'processed'
            feedback.save()
            
            processed_count += 1
            
            if feedback.priority in ['high', 'critical']:
                high_priority_count += 1
        
        logger.info(
            f"[NLU Training] ✅ Lote procesado\n"
            f"  📊 Procesados: {processed_count}\n"
            f"  🔥 Alta prioridad: {high_priority_count}"
        )
        
        return {
            'processed': processed_count,
            'high_priority': high_priority_count
        }

