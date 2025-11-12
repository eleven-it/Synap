"""
Webhooks para sistema de actualización continua del NLU
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from reports_ai.models import NLUFeedback, ReportRequest
import json

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_feedback_nlu(request):
    """
    Recibe feedback sobre interpretación incorrecta del NLU
    
    POST /reports-ai/webhook/feedback-nlu/
    
    Body:
    {
        "consulta": "Quiero los pedidos en tránsito de septiembre",
        "interpretacion_sistema": {
            "intent": "reporte_pedidos",
            "slots": {"estado": "pendiente"}
        },
        "interpretacion_correcta": {
            "intent": "reporte_pedidos",
            "slots": {"estado": "en_transito", "periodo": "2025-09"}
        },
        "comentario": "Se confundió 'pendiente' con 'en tránsito'.",
        "request_id": "REQ-ABC123" (opcional)
    }
    
    Returns:
        JSON con confirmación y ID del feedback
    """
    try:
        data = json.loads(request.body)
        
        # Validar datos requeridos
        required_fields = ['consulta', 'interpretacion_sistema', 'interpretacion_correcta']
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Campos requeridos faltantes: {", ".join(missing_fields)}'
            }, status=400)
        
        # Extraer datos
        query_text = data['consulta']
        system_interp = data['interpretacion_sistema']
        correct_interp = data['interpretacion_correcta']
        comment = data.get('comentario', '')
        request_id = data.get('request_id')
        
        # Buscar report request si existe
        report_request = None
        if request_id:
            try:
                report_request = ReportRequest.objects.get(request_id=request_id)
            except ReportRequest.DoesNotExist:
                logger.warning(f"Request ID {request_id} not found")
        
        # Determinar prioridad automáticamente
        priority = 'normal'
        
        # Si el intent está completamente errado → alta prioridad
        if system_interp.get('intent') != correct_interp.get('intent'):
            priority = 'high'
        
        # Si es un intent frecuente → crítica
        frequent_intents = ['reporte_ventas', 'reporte_inventario', 'reporte_pedidos']
        if correct_interp.get('intent') in frequent_intents:
            priority = 'critical'
        
        # Crear feedback
        feedback = NLUFeedback.objects.create(
            query_text=query_text,
            system_intent=system_interp.get('intent', ''),
            system_slots=system_interp.get('slots', {}),
            correct_intent=correct_interp.get('intent', ''),
            correct_slots=correct_interp.get('slots', {}),
            user_comment=comment,
            priority=priority,
            status='pending',
            report_request=report_request
        )
        
        logger.info(
            f"[NLU Feedback] Feedback creado ID: {feedback.id}\n"
            f"  📝 Query: {query_text[:50]}...\n"
            f"  ❌ Intent errado: {system_interp.get('intent')}\n"
            f"  ✅ Intent correcto: {correct_interp.get('intent')}\n"
            f"  🎯 Prioridad: {priority}"
        )
        
        return JsonResponse({
            'success': True,
            'feedback_id': feedback.id,
            'priority': priority,
            'message': 'Feedback recibido correctamente. Será procesado en el siguiente ciclo de actualización.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"[NLU Feedback] Error procesando feedback: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def nlu_feedback_list(request):
    """
    Lista feedbacks pendientes del NLU
    
    GET /reports-ai/api/nlu-feedback/?status=pending&priority=high
    """
    status = request.GET.get('status', 'pending')
    priority = request.GET.get('priority')
    
    feedbacks = NLUFeedback.objects.filter(status=status)
    
    if priority:
        feedbacks = feedbacks.filter(priority=priority)
    
    feedbacks = feedbacks.order_by('-priority', '-created_at')[:50]
    
    data = []
    for fb in feedbacks:
        data.append({
            'id': fb.id,
            'query': fb.query_text,
            'system_intent': fb.system_intent,
            'correct_intent': fb.correct_intent,
            'priority': fb.priority,
            'created_at': fb.created_at.isoformat(),
            'comment': fb.user_comment
        })
    
    return JsonResponse({
        'success': True,
        'count': len(data),
        'feedbacks': data
    })


@require_http_methods(["GET"])
def nlu_metrics_summary(request):
    """
    Resumen de métricas del NLU
    
    GET /reports-ai/api/nlu-metrics/?period=weekly
    """
    from datetime import datetime, timedelta
    from django.db.models import Avg
    from reports_ai.models import NLUMetrics
    
    period = request.GET.get('period', 'weekly')
    
    # Últimas métricas
    recent_metrics = NLUMetrics.objects.filter(
        period_type=period
    ).order_by('-evaluation_date')[:4]
    
    if not recent_metrics.exists():
        return JsonResponse({
            'success': True,
            'message': 'No hay métricas disponibles aún',
            'metrics': []
        })
    
    # Calcular promedios
    avg_metrics = recent_metrics.aggregate(
        avg_coverage=Avg('coverage_rate'),
        avg_clarification=Avg('clarification_rate'),
        avg_misroute=Avg('misroute_rate'),
        avg_slot_accuracy=Avg('slot_accuracy')
    )
    
    # Preparar respuesta
    metrics_data = []
    for metric in recent_metrics:
        metrics_data.append({
            'date': metric.evaluation_date.isoformat(),
            'total_queries': metric.total_queries,
            'correctly_classified': metric.correctly_classified,
            'coverage_rate': metric.coverage_rate,
            'clarification_rate': metric.clarification_rate,
            'misroute_rate': metric.misroute_rate,
            'slot_accuracy': metric.slot_accuracy,
            'model_version': metric.model_version
        })
    
    return JsonResponse({
        'success': True,
        'period': period,
        'averages': avg_metrics,
        'recent_metrics': metrics_data,
        'health_status': _get_health_status(avg_metrics)
    })


def _get_health_status(avg_metrics):
    """Determina el estado de salud del NLU basado en métricas"""
    coverage = avg_metrics.get('avg_coverage', 0) or 0
    misroute = avg_metrics.get('avg_misroute', 0) or 0
    slot_acc = avg_metrics.get('avg_slot_accuracy', 0) or 0
    
    issues = []
    
    if coverage < 95.0:
        issues.append(f'Cobertura baja: {coverage:.1f}% (target: ≥95%)')
    
    if misroute > 3.0:
        issues.append(f'Tasa de error alta: {misroute:.1f}% (target: ≤3%)')
    
    if slot_acc < 90.0:
        issues.append(f'Exactitud de slots baja: {slot_acc:.1f}% (target: ≥90%)')
    
    if not issues:
        return {
            'status': 'healthy',
            'message': 'Todas las métricas dentro de los umbrales esperados'
        }
    else:
        return {
            'status': 'needs_attention',
            'issues': issues,
            'action_required': 'Considerar reentrenamiento incremental'
        }

