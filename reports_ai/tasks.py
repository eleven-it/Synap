"""
Tareas Celery para el sistema de actualización continua del NLU
"""
from celery import shared_task
import logging
from reports_ai.services.nlu_training_service import NLUTrainingService

logger = logging.getLogger(__name__)


@shared_task(name='reports_ai.check_nlu_changes_daily')
def check_nlu_changes_daily():
    """
    Tarea diaria: Escaneo ligero de cambios funcionales
    
    Programada para ejecutarse diariamente a las 02:00 AM
    """
    logger.info("[Celery] Ejecutando check_nlu_changes_daily")
    
    service = NLUTrainingService()
    result = service.detect_changes_daily()
    
    if result['action_required']:
        logger.info(
            f"[Celery] ⚠️  Cambios detectados en NLU\n"
            f"  📋 Nuevas reglas: {result['new_business_rules']}\n"
            f"  📝 Reglas modificadas: {result['modified_business_rules']}\n"
            f"  📚 Nuevos términos: {result['new_glossary_terms']}\n"
            f"  💬 Feedback: {result['new_feedback']}\n"
            f"  🎯 Acción: Actualizar ejemplos de entrenamiento"
        )
        
        # Si hay feedback crítico, procesarlo inmediatamente
        if result['new_feedback'] > 0:
            service.process_feedback_batch(batch_size=10)
    else:
        logger.info("[Celery] ✅ No se detectaron cambios relevantes en NLU")
    
    return result


@shared_task(name='reports_ai.evaluate_nlu_weekly')
def evaluate_nlu_weekly():
    """
    Tarea semanal: Evaluación integral + regresión
    
    Programada para ejecutarse semanalmente los domingos a las 03:00 AM
    """
    logger.info("[Celery] Ejecutando evaluate_nlu_weekly")
    
    service = NLUTrainingService()
    result = service.evaluate_weekly()
    
    if result['needs_retraining']:
        logger.warning(
            f"[Celery] ⚠️  El NLU requiere reentrenamiento\n"
            f"  📊 Cobertura: {result['coverage_rate']:.1f}% (target: ≥95%)\n"
            f"  ❌ Error: {result['misroute_rate']:.1f}% (target: ≤3%)\n"
            f"  💬 Aclaración: {result['clarification_rate']:.1f}% (target: 3-8%)\n"
            f"  🎯 Acción: Ejecutar train_nlu_incremental"
        )
        
        # Trigger reentrenamiento automático si las métricas son críticas
        if result['misroute_rate'] > 5.0 or result['coverage_rate'] < 90.0:
            logger.error("[Celery] 🚨 Métricas críticas, ejecutando reentrenamiento automático")
            service.train_incremental(max_examples=100)
    else:
        logger.info(
            f"[Celery] ✅ Métricas del NLU saludables\n"
            f"  📊 Cobertura: {result['coverage_rate']:.1f}%\n"
            f"  ❌ Error: {result['misroute_rate']:.1f}%\n"
            f"  💬 Aclaración: {result['clarification_rate']:.1f}%"
        )
    
    return result


@shared_task(name='reports_ai.retrain_nlu_monthly')
def retrain_nlu_monthly():
    """
    Tarea mensual: Reentrenamiento completo
    
    Programada para ejecutarse el primer domingo de cada mes a las 04:00 AM
    """
    logger.info("[Celery] Ejecutando retrain_nlu_monthly")
    
    service = NLUTrainingService()
    
    # 1. Detectar deriva
    drift_result = service.detect_drift()
    
    # 2. Evaluar métricas
    eval_result = service.evaluate_weekly()
    
    # 3. Reentrenar si hay deriva o métricas bajas
    if drift_result['drift_detected'] or eval_result['needs_retraining']:
        logger.info("[Celery] 🎓 Ejecutando reentrenamiento mensual completo")
        train_result = service.train_incremental(max_examples=500)
        
        return {
            'drift_detected': drift_result['drift_detected'],
            'needs_retraining': eval_result['needs_retraining'],
            'examples_added': train_result['examples_added'],
            'status': 'retrained'
        }
    else:
        logger.info("[Celery] ✅ No se requiere reentrenamiento este mes")
        return {
            'drift_detected': False,
            'needs_retraining': False,
            'status': 'skipped'
        }


@shared_task(name='reports_ai.process_nlu_feedback')
def process_nlu_feedback(batch_size=50):
    """
    Tarea para procesar feedback pendiente
    
    Puede ejecutarse manualmente o automáticamente cuando se acumula feedback
    """
    logger.info(f"[Celery] Procesando lote de feedback NLU (size={batch_size})")
    
    service = NLUTrainingService()
    result = service.process_feedback_batch(batch_size=batch_size)
    
    logger.info(
        f"[Celery] ✅ Feedback procesado\n"
        f"  📊 Total: {result['processed']}\n"
        f"  🔥 Alta prioridad: {result['high_priority']}"
    )
    
    return result

