"""
Vistas para el Chat Conversacional
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from ..models import ChatConversation


@login_required
def ai_assistant(request):
    """
    Vista principal del asistente conversacional
    """
    # Obtener conversación activa si existe
    active_conversation = ChatConversation.objects.filter(
        user=request.user,
        is_active=True
    ).first()
    
    context = {
        'conversation_id': str(active_conversation.conversation_id) if active_conversation else None,
        'page_title': 'AI Assistant',
    }
    
    return render(request, 'reports_ai/chat/assistant.html', context)

