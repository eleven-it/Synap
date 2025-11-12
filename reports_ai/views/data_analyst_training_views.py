"""
Vistas para entrenamiento del Data Analyst Agent
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from ..services.data_analyst_training_service import DataAnalystTrainingService


# Instancia global del servicio
training_service = DataAnalystTrainingService()


@login_required
def data_analyst_training(request):
    """
    Vista principal para entrenamiento interactivo del Data Analyst
    """
    context = {
        'page_title': 'Train Data Analyst Agent',
    }
    
    return render(request, 'reports_ai/training/data_analyst.html', context)


@login_required
def data_analyst_training_session_detail(request, session_id):
    """
    Detalle de una sesión de entrenamiento completada
    """
    session = training_service.get_session(session_id)
    
    if not session:
        context = {
            'error': 'Session not found',
            'session_id': session_id
        }
    else:
        context = {
            'session': session.to_dict(),
            'session_id': session_id
        }
    
    return render(request, 'reports_ai/training/data_analyst_session_detail.html', context)

