"""
APIs para entrenamiento del Data Analyst Agent
"""
import json
import time
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from ..services.data_analyst_training_service import DataAnalystTrainingService


# Instancia global del servicio
training_service = DataAnalystTrainingService()


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def start_data_analyst_training(request):
    """
    Inicia una sesión de entrenamiento del Data Analyst
    """
    try:
        # Parsear opciones desde el body
        data = json.loads(request.body) if request.body else {}
        
        options = {
            'discover_relationships': data.get('discover_relationships', True),
            'build_synonyms': data.get('build_synonyms', True),
            'min_confidence': float(data.get('min_confidence', 0.6)),
            'use_logic_interpreter': data.get('use_logic_interpreter', True),
            'clear_existing': data.get('clear_existing', False)
        }
        
        # Iniciar entrenamiento
        session_id = training_service.train_interactive(options=options)
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'message': 'Training started successfully'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def data_analyst_training_progress_stream(request, session_id):
    """
    Stream de progreso en tiempo real usando Server-Sent Events (SSE)
    """
    def event_stream():
        """Generador de eventos SSE"""
        last_progress = -1
        max_iterations = 300  # 5 minutos máximo (300 * 1s)
        iterations = 0
        
        while iterations < max_iterations:
            session = training_service.get_session(session_id)
            
            if not session:
                yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
                break
            
            current_data = session.to_dict()
            current_progress = current_data.get('progress', 0)
            
            # Enviar actualización si cambió el progreso o cada 2 segundos
            if current_progress != last_progress or iterations % 2 == 0:
                yield f"data: {json.dumps(current_data)}\n\n"
                last_progress = current_progress
            
            # Si terminó (completed, error, cancelled), enviar y salir
            if session.status in ['completed', 'error', 'cancelled']:
                yield f"data: {json.dumps(current_data)}\n\n"
                break
            
            time.sleep(1)
            iterations += 1
        
        # Evento de cierre
        yield "event: close\ndata: {}\n\n"
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    
    return response


@login_required
def data_analyst_training_status(request, session_id):
    """
    Obtiene el estado actual de una sesión (sin streaming)
    """
    session = training_service.get_session(session_id)
    
    if not session:
        return JsonResponse({
            'success': False,
            'error': 'Session not found'
        }, status=404)
    
    return JsonResponse({
        'success': True,
        'data': session.to_dict()
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def cancel_data_analyst_training(request, session_id):
    """
    Cancela una sesión de entrenamiento en ejecución
    """
    success = training_service.cancel_session(session_id)
    
    if success:
        return JsonResponse({
            'success': True,
            'message': 'Training cancelled successfully'
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Could not cancel session (not found or not running)'
        }, status=400)


@login_required
def data_analyst_training_results(request, session_id):
    """
    Obtiene los resultados finales de una sesión completada
    """
    session = training_service.get_session(session_id)
    
    if not session:
        return JsonResponse({
            'success': False,
            'error': 'Session not found'
        }, status=404)
    
    if session.status != 'completed':
        return JsonResponse({
            'success': False,
            'error': f'Session not completed yet (status: {session.status})'
        }, status=400)
    
    return JsonResponse({
        'success': True,
        'results': session.results,
        'session_data': session.to_dict()
    })


@login_required
def data_analyst_training_history(request):
    """
    Obtiene historial de sesiones de entrenamiento
    """
    sessions = list(training_service.active_sessions.values())
    
    # Ordenar por fecha de inicio (más reciente primero)
    sessions.sort(
        key=lambda s: s.start_time if s.start_time else timezone.now(),
        reverse=True
    )
    
    return JsonResponse({
        'success': True,
        'sessions': [s.to_dict() for s in sessions[:20]]  # Últimas 20
    })

