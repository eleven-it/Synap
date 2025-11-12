"""
API para entrenamiento interactivo del Logic Interpreter
"""
import logging
import json
import time
import uuid
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from reports_ai.models import LogicTrainingSession, FunctionalCatalog
from reports_ai.services.logic_training_service import LogicInterpreterTrainingService
from reports_ai.services.guided_training_service import GuidedTrainingService
from threading import Thread

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def start_training(request):
    """
    Inicia una sesión de entrenamiento del Logic Interpreter
    
    POST /reports-ai/api/train/logic-interpreter/start/
    
    Body:
    {
        "categories": ["inventario", "ventas"],  // opcional
        "mode": "full"  // full o incremental
    }
    
    Returns:
        JSON con session_id y URL de progreso
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        categories = data.get('categories')
        mode = data.get('mode', 'full')
        
        # Generar session ID único
        session_id = f"TRAIN-{uuid.uuid4().hex[:12].upper()}"
        
        logger.info(
            f"[Training API] 🎓 Iniciando entrenamiento\n"
            f"  🆔 Session: {session_id}\n"
            f"  📂 Categorías: {categories or 'Todas'}\n"
            f"  🔧 Modo: {mode}"
        )
        
        # Crear sesión
        session = LogicTrainingSession.objects.create(
            session_id=session_id,
            categories=categories or [],
            mode=mode,
            status='running',
            created_by=request.user
        )
        
        # Iniciar entrenamiento en background thread
        service = LogicInterpreterTrainingService()
        
        def run_training():
            service.train_interactive(
                session_id=session_id,
                categories=categories,
                mode=mode
            )
        
        thread = Thread(target=run_training, daemon=True)
        thread.start()
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'status': 'running',
            'progress_url': f'/reports-ai/api/train/logic-interpreter/progress/{session_id}/',
            'status_url': f'/reports-ai/api/train/logic-interpreter/status/{session_id}/'
        })
        
    except Exception as e:
        logger.error(f"[Training API] ❌ Error iniciando entrenamiento: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
@login_required
def training_progress_stream(request, session_id):
    """
    SSE endpoint para streaming de progreso en tiempo real
    
    GET /reports-ai/api/train/logic-interpreter/progress/<session_id>/
    
    Returns:
        Server-Sent Events stream
    """
    service = LogicInterpreterTrainingService()
    
    def event_stream():
        """Generador de eventos SSE"""
        try:
            session = LogicTrainingSession.objects.get(session_id=session_id)
        except LogicTrainingSession.DoesNotExist:
            yield f"data: {json.dumps({'error': 'Session not found'})}\n\n"
            return
        
        logger.info(f"[Training API] 📡 SSE stream iniciado para {session_id}")
        
        last_progress = -1
        iterations = 0
        max_iterations = 600  # 5 minutos máximo (600 * 0.5s)
        
        while session.status == 'running' and iterations < max_iterations:
            session.refresh_from_db()
            
            # Solo enviar si hay cambio en progreso
            if session.progress_percentage != last_progress:
                progress_data = service.get_session_progress(session_id)
                
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                last_progress = session.progress_percentage
            
            time.sleep(0.5)  # Update cada 500ms
            iterations += 1
        
        # Enviar estado final
        session.refresh_from_db()
        final_data = service.get_session_progress(session_id)
        final_data['completed'] = True
        yield f"data: {json.dumps(final_data)}\n\n"
        
        logger.info(f"[Training API] ✅ SSE stream completado para {session_id}")
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    
    return response


@require_http_methods(["GET"])
@login_required
def training_status(request, session_id):
    """
    Obtiene el estado actual de una sesión
    
    GET /reports-ai/api/train/logic-interpreter/status/<session_id>/
    """
    service = LogicInterpreterTrainingService()
    progress_data = service.get_session_progress(session_id)
    
    if 'error' in progress_data:
        return JsonResponse(progress_data, status=404)
    
    return JsonResponse({
        'success': True,
        **progress_data
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def cancel_training(request, session_id):
    """
    Cancela una sesión de entrenamiento
    
    POST /reports-ai/api/train/logic-interpreter/cancel/<session_id>/
    """
    service = LogicInterpreterTrainingService()
    result = service.cancel_training(session_id)
    
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=400)


@require_http_methods(["GET"])
@login_required
def training_results(request, session_id):
    """
    Obtiene los resultados finales de una sesión
    
    GET /reports-ai/api/train/logic-interpreter/results/<session_id>/
    """
    try:
        session = LogicTrainingSession.objects.get(session_id=session_id)
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'status': session.status,
            'duration': session.duration_seconds,
            'results': {
                'entities': session.entities_discovered,
                'tables': session.tables_suggested,
                'fields': session.fields_validated,
                'relations': session.relations_found,
                'rules': session.rules_extracted
            },
            'metrics': {
                'success_rate': session.success_rate,
                'avg_confidence': session.avg_confidence,
                'tables_verified': session.tables_verified,
                'fields_match_rate': session.fields_match_rate
            },
            'stats': {
                'total_forms': session.total_forms,
                'analyzed_forms': session.analyzed_forms,
                'entities_count': len(session.entities_discovered),
                'tables_count': len(session.tables_suggested),
                'relations_count': len(session.relations_found),
                'rules_count': len(session.rules_extracted)
            }
        })
        
    except LogicTrainingSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Session not found'
        }, status=404)


@require_http_methods(["GET"])
@login_required
def training_history(request):
    """
    Lista de sesiones de entrenamiento anteriores
    
    GET /reports-ai/api/train/logic-interpreter/history/
    """
    sessions = LogicTrainingSession.objects.all().order_by('-start_time')[:20]
    
    data = []
    for session in sessions:
        data.append({
            'session_id': session.session_id,
            'status': session.status,
            'start_time': session.start_time.isoformat(),
            'duration': session.duration_seconds,
            'categories': session.categories,
            'stats': {
                'forms': session.analyzed_forms,
                'entities': len(session.entities_discovered),
                'tables': len(session.tables_suggested),
                'rules': len(session.rules_extracted)
            },
            'metrics': {
                'success_rate': session.success_rate,
                'avg_confidence': session.avg_confidence
            }
        })
    
    return JsonResponse({
        'success': True,
        'count': len(data),
        'sessions': data
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def start_guided_training(request):
    """
    Inicia entrenamiento GUIADO desde catálogo funcional
    
    POST /reports-ai/api/train/logic-interpreter/start-guided/
    
    Body:
    {
        "catalog_entries": [1, 2, 3],  // IDs de FunctionalCatalog
        "mode": "guided"
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        entry_ids = data.get('catalog_entries', [])
        
        if not entry_ids:
            return JsonResponse({
                'success': False,
                'error': 'Debes seleccionar al menos una entrada del catálogo'
            }, status=400)
        
        # Generar session ID
        session_id = f"GUIDED-{uuid.uuid4().hex[:12].upper()}"
        
        logger.info(
            f"[Guided Training API] 🎯 Iniciando entrenamiento guiado\n"
            f"  🆔 Session: {session_id}\n"
            f"  📚 Entradas: {len(entry_ids)}"
        )
        
        # Crear sesión de entrenamiento
        session = LogicTrainingSession.objects.create(
            session_id=session_id,
            status='running',
            categories=['guided'],
            created_by=request.user,
            mode='guided'
        )
        
        # Iniciar entrenamiento en background
        service = GuidedTrainingService()
        
        def run_training():
            try:
                total_rules = 0
                total_entries = len(entry_ids)
                
                for idx, entry_id in enumerate(entry_ids):
                    try:
                        catalog_entry = FunctionalCatalog.objects.get(id=entry_id)
                        
                        logger.info(f"[Guided Training] Entrenando: {catalog_entry.module} - {catalog_entry.procedure}")
                        
                        result = service.train_from_catalog_entry(catalog_entry)
                        
                        if result.get('success'):
                            total_rules += result['business_rules_created']
                        
                    except FunctionalCatalog.DoesNotExist:
                        logger.warning(f"[Guided Training] Entrada {entry_id} no encontrada")
                
                # Actualizar sesión
                session.status = 'completed'
                session.business_rules_created = total_rules
                session.forms_analyzed = total_entries
                session.save()
                
                logger.info(f"[Guided Training] ✅ Completado: {total_rules} Business Rules creadas")
                
            except Exception as e:
                logger.error(f"[Guided Training] ❌ Error: {e}", exc_info=True)
                session.status = 'error'
                session.error_message = str(e)
                session.save()
        
        # Ejecutar en thread
        thread = Thread(target=run_training)
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'message': f'Entrenamiento guiado iniciado para {len(entry_ids)} procedimiento(s)',
            'progress_url': f'/reports-ai/api/train/logic-interpreter/status/{session_id}/'
        })
    
    except Exception as e:
        logger.error(f"[Guided Training API] Error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

