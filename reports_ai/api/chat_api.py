"""
APIs para el sistema de Chat Conversacional
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from ..services.chat_service import ChatService
from ..models import ChatConversation, ChatMessage

# Instancia global del servicio
chat_service = ChatService()


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def send_message(request):
    """
    Envía un mensaje y recibe respuesta del asistente
    
    POST /api/chat/send/
    Body: {
        "message": "Cómo crear un pedido?",
        "conversation_id": "uuid" // opcional
    }
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        message_text = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not message_text:
            return JsonResponse({
                'success': False,
                'error': 'El mensaje no puede estar vacío'
            }, status=400)
        
        # Procesar mensaje
        result = chat_service.process_message(
            user=request.user,
            message_text=message_text,
            conversation_id=conversation_id
        )
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def get_conversation(request, conversation_id):
    """
    Obtiene el historial de una conversación
    
    GET /api/chat/conversation/<conversation_id>/
    """
    try:
        conversation = ChatConversation.objects.get(
            conversation_id=conversation_id,
            user=request.user
        )
        
        # Obtener mensajes
        messages = chat_service.get_conversation_history(conversation)
        
        return JsonResponse({
            'success': True,
            'conversation_id': str(conversation.conversation_id),
            'title': conversation.title,
            'message_count': len(messages),
            'messages': messages,
            'is_active': conversation.is_active
        })
    
    except ChatConversation.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Conversación no encontrada'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def list_conversations(request):
    """
    Lista todas las conversaciones del usuario
    
    GET /api/chat/conversations/
    Query params:
        - active_only: true/false
        - limit: int
    """
    try:
        active_only = request.GET.get('active_only', 'true').lower() == 'true'
        limit = int(request.GET.get('limit', 20))
        
        conversations = ChatConversation.objects.filter(user=request.user)
        
        if active_only:
            conversations = conversations.filter(is_active=True)
        
        conversations = conversations.order_by('-updated_at')[:limit]
        
        conversations_data = [{
            'conversation_id': str(conv.conversation_id),
            'title': conv.title,
            'message_count': conv.get_message_count(),
            'is_active': conv.is_active,
            'created_at': conv.created_at.isoformat(),
            'updated_at': conv.updated_at.isoformat(),
            'last_message': chat_service._serialize_message(conv.get_last_message()) if conv.get_last_message() else None
        } for conv in conversations]
        
        return JsonResponse({
            'success': True,
            'conversations': conversations_data,
            'total': len(conversations_data)
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def new_conversation(request):
    """
    Crea una nueva conversación
    
    POST /api/chat/new/
    """
    try:
        conversation = ChatConversation.objects.create(
            user=request.user,
            title="Nueva conversación",
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'conversation_id': str(conversation.conversation_id),
            'message': 'Conversación creada exitosamente'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def archive_conversation(request, conversation_id):
    """
    Archiva una conversación
    
    POST /api/chat/archive/<conversation_id>/
    """
    try:
        conversation = ChatConversation.objects.get(
            conversation_id=conversation_id,
            user=request.user
        )
        
        chat_service.conversation_manager.archive_conversation(conversation)
        
        return JsonResponse({
            'success': True,
            'message': 'Conversación archivada'
        })
    
    except ChatConversation.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Conversación no encontrada'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

