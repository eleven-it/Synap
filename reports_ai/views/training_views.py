"""
Vistas para entrenamiento interactivo del Logic Interpreter
"""
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from reports_ai.models import LogicTrainingSession, FunctionalCatalog

logger = logging.getLogger(__name__)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def logic_interpreter_training(request):
    """
    Vista principal para entrenamiento interactivo del Logic Interpreter
    
    GET /reports-ai/train/logic-interpreter/
    """
    # Obtener sesiones recientes
    recent_sessions = LogicTrainingSession.objects.all().order_by('-start_time')[:10]
    
    # Obtener entradas activas del catálogo funcional ordenadas por prioridad
    catalog_entries = FunctionalCatalog.objects.filter(
        is_active=True
    ).order_by('-priority', 'module', 'procedure')
    
    context = {
        'page_title': 'Train Logic Interpreter',
        'active_tab': 'training',
        'recent_sessions': recent_sessions,
        'catalog_entries': catalog_entries,
        'categories': [
            {'id': 'inventario', 'name': 'Inventario', 'icon': '📦'},
            {'id': 'ventas', 'name': 'Ventas', 'icon': '💰'},
            {'id': 'clientes', 'name': 'Clientes', 'icon': '👥'},
            {'id': 'cobranzas', 'name': 'Cobranzas', 'icon': '💵'},
            {'id': 'compras', 'name': 'Compras', 'icon': '🛒'},
            {'id': 'general', 'name': 'General', 'icon': '⚙️'},
        ]
    }
    
    return render(request, 'reports_ai/training/logic_interpreter.html', context)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def training_session_detail(request, session_id):
    """
    Vista de detalle de una sesión de entrenamiento
    
    GET /reports-ai/train/logic-interpreter/session/<session_id>/
    """
    try:
        session = LogicTrainingSession.objects.get(session_id=session_id)
        
        # Calcular estadísticas
        total_fields = sum(
            len(f.get('suggested_fields', [])) 
            for f in session.fields_validated.values()
        )
        matched_fields = sum(
            len(f.get('matched_fields', [])) 
            for f in session.fields_validated.values()
        )
        
        context = {
            'page_title': f'Training Session {session_id}',
            'active_tab': 'training',
            'session': session,
            'stats': {
                'total_fields': total_fields,
                'matched_fields': matched_fields,
            }
        }
        
        return render(request, 'reports_ai/training/session_detail.html', context)
        
    except LogicTrainingSession.DoesNotExist:
        context = {
            'page_title': 'Session Not Found',
            'error': 'Training session not found'
        }
        return render(request, 'reports_ai/training/session_detail.html', context, status=404)

