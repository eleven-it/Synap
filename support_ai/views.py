from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.http import HttpResponse, JsonResponse
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import logging
from datetime import datetime
import time # Added for ai_model_test_endpoint

logger = logging.getLogger(__name__)

from .models import (
    SupportTicket, Conversation, CustomerSatisfaction, 
    SupportMetrics, AIAgent, SupportConfiguration,
    KnowledgeBase, TicketTemplate, UserSettings, SystemSettings
)
from .utils import analyze_sentiment, extract_keywords, generate_contextual_response, categorize_message
from .ai_clients import ai_orchestrator
from .ai_config import ai_service_manager
from .ai_metrics import ai_metrics
from .analytics import ai_analytics
from .ai_config import ai_prompt_manager


def placeholder_view(request):
    """Vista temporal para evitar errores de importación"""
    return HttpResponse("Endpoint not implemented yet")


class SupportSettingsView(LoginRequiredMixin, TemplateView):
    """
    Vista de configuraciones del sistema de soporte
    """
    template_name = 'support_ai/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Verificar permisos de administrador
        context['is_admin'] = user.is_superuser or user.groups.filter(name__in=['supervisor', 'admin']).exists()
        context['is_agent'] = user.groups.filter(name='agent').exists()
        
        # Obtener configuración actual
        try:
            context['ai_config'] = SupportConfiguration.objects.first()
            context['system_settings'] = SystemSettings.get_settings()
        except Exception as e:
            logger.error(f"Error obteniendo configuraciones del sistema: {str(e)}")
            context['ai_config'] = None
            context['system_settings'] = None
        
        # Configuraciones de usuario
        try:
            user_settings_obj, created = UserSettings.objects.get_or_create(
                user=user,
                defaults={
                    'notifications_enabled': True,
                    'push_notifications': True,
                    'language': 'es',
                    'theme': 'light',
                }
            )
            context['user_settings'] = {
                'notifications_enabled': user_settings_obj.notifications_enabled,
                'push_notifications': user_settings_obj.push_notifications,
                'language': user_settings_obj.language,
                'theme': user_settings_obj.theme,
            }
        except Exception as e:
            logger.error(f"Error obteniendo configuraciones de usuario: {str(e)}")
            context['user_settings'] = {
                'notifications_enabled': True,
                'push_notifications': True,
                'language': 'es',
                'theme': 'light',
            }
        
        return context


class PortalHomeView(LoginRequiredMixin, TemplateView):
    """
    Vista del portal principal del cliente
    """
    template_name = 'support_ai/portal_home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Obtener estadísticas del usuario
        user_tickets = SupportTicket.objects.filter(customer=user)
        context['total_tickets'] = user_tickets.count()
        context['open_tickets'] = user_tickets.filter(status='open').count()
        context['resolved_tickets'] = user_tickets.filter(status='resolved').count()
        context['in_progress_tickets'] = user_tickets.filter(status='in_progress').count()
        
        # Tickets recientes
        context['recent_tickets'] = user_tickets.order_by('-created_at')[:5]
        
        return context


class TicketListView(LoginRequiredMixin, ListView):
    """
    Vista para listar tickets con filtros y búsqueda
    """
    model = SupportTicket
    template_name = 'support_ai/ticket_list.html'
    context_object_name = 'tickets'
    paginate_by = 20
    
    def get_queryset(self):
        user = self.request.user
        queryset = SupportTicket.objects.all()
        
        # Filtrar por rol del usuario
        if user.groups.filter(name='client').exists():
            queryset = queryset.filter(customer=user)
        elif user.groups.filter(name='agent').exists():
            queryset = queryset.filter(assigned_agent=user)
        elif user.groups.filter(name='supervisor').exists():
            # Supervisores ven todos los tickets
            pass
        else:
            # Usuarios sin rol específico ven solo sus tickets
            queryset = queryset.filter(customer=user)
        
        # Filtros
        status = self.request.GET.get('status')
        priority = self.request.GET.get('priority')
        search = self.request.GET.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search) |
                Q(description__icontains=search) |
                Q(ticket_number__icontains=search)
            )
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Estadísticas para filtros
        if user.groups.filter(name='client').exists():
            user_tickets = SupportTicket.objects.filter(customer=user)
        else:
            user_tickets = SupportTicket.objects.all()
        
        context['status_counts'] = dict(user_tickets.values('status').annotate(count=Count('id')).values_list('status', 'count'))
        context['priority_counts'] = dict(user_tickets.values('priority').annotate(count=Count('id')).values_list('priority', 'count'))
        
        # Filtros aplicados
        context['current_status'] = self.request.GET.get('status', '')
        context['current_priority'] = self.request.GET.get('priority', '')
        context['current_search'] = self.request.GET.get('search', '')
        
        return context


class TicketCreateView(LoginRequiredMixin, CreateView):
    """
    Vista para crear nuevos tickets
    """
    model = SupportTicket
    template_name = 'support_ai/ticket_create.html'
    fields = ['subject', 'description', 'priority', 'channel']
    success_url = reverse_lazy('support_ai:ticket_list')
    
    def form_valid(self, form):
        form.instance.customer = self.request.user
        response = super().form_valid(form)
        
        # Crear mensaje inicial
        Conversation.objects.create(
            ticket=form.instance,
            message_type='user',
            content=form.instance.description
        )
        
        messages.success(self.request, f'Ticket #{form.instance.ticket_number} creado exitosamente.')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['templates'] = TicketTemplate.objects.filter(is_active=True)
        return context


class TicketDetailView(LoginRequiredMixin, DetailView):
    """
    Vista detallada de un ticket específico
    """
    model = SupportTicket
    template_name = 'support_ai/ticket_detail.html'
    context_object_name = 'ticket'
    
    def get_queryset(self):
        user = self.request.user
        queryset = SupportTicket.objects.all()
        
        # Filtrar por rol del usuario
        if user.groups.filter(name='client').exists():
            queryset = queryset.filter(customer=user)
        elif user.groups.filter(name='agent').exists():
            queryset = queryset.filter(assigned_agent=user)
        elif user.groups.filter(name='supervisor').exists():
            # Supervisores ven todos los tickets
            pass
        else:
            # Usuarios sin rol específico ven solo sus tickets
            queryset = queryset.filter(customer=user)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ticket = self.object
        
        # Obtener conversaciones
        context['conversations'] = ticket.conversations.all().order_by('created_at')
        
        # Obtener satisfacción si existe
        try:
            context['satisfaction'] = ticket.satisfaction_ratings.get(customer=self.request.user)
        except CustomerSatisfaction.DoesNotExist:
            context['satisfaction'] = None
        
        # Verificar permisos
        context['can_edit'] = self.request.user == ticket.customer or self.request.user.groups.filter(name__in=['agent', 'supervisor']).exists()
        context['can_assign'] = self.request.user.groups.filter(name__in=['agent', 'supervisor']).exists()
        context['can_close'] = self.request.user.groups.filter(name__in=['agent', 'supervisor']).exists() or self.request.user == ticket.customer
        
        return context


class ChatView(LoginRequiredMixin, TemplateView):
    """
    Vista del chat de soporte
    """
    template_name = 'support_ai/chat.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Obtener tickets activos del usuario
        context['active_tickets'] = SupportTicket.objects.filter(
            customer=user,
            status__in=['open', 'in_progress', 'waiting_customer']
        ).order_by('-created_at')
        
        # Obtener configuración de IA
        try:
            context['ai_config'] = SupportConfiguration.objects.first()
        except SupportConfiguration.DoesNotExist:
            context['ai_config'] = None
        
        return context


@login_required
def ticket_status_update(request, ticket_id):
    """
    Actualizar el estado de un ticket
    """
    if request.method == 'POST':
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        new_status = request.POST.get('status')
        
        # Verificar permisos
        if not (request.user == ticket.customer or request.user.groups.filter(name__in=['agent', 'supervisor']).exists()):
            messages.error(request, 'No tienes permisos para actualizar este ticket.')
            return redirect('support_ai:ticket_detail', ticket_id=ticket_id)
        
        if new_status in dict(SupportTicket.STATUS_CHOICES):
            old_status = ticket.status
            ticket.status = new_status
            
            # Actualizar fecha de resolución si es necesario
            if new_status == 'resolved' and not ticket.resolved_at:
                ticket.resolved_at = timezone.now()
            elif new_status != 'resolved':
                ticket.resolved_at = None
            
            ticket.save()
            
            # Crear mensaje del sistema
            Conversation.objects.create(
            ticket=ticket,
                message_type='system',
                content=f'Estado del ticket cambiado de {dict(SupportTicket.STATUS_CHOICES)[old_status]} a {dict(SupportTicket.STATUS_CHOICES)[new_status]}'
            )
            
            messages.success(request, f'Estado del ticket actualizado a {dict(SupportTicket.STATUS_CHOICES)[new_status]}')
        
    return redirect('support_ai:ticket_detail', ticket_id=ticket_id)


@login_required
def ticket_priority_update(request, ticket_id):
    """
    Actualizar la prioridad de un ticket
    """
    if request.method == 'POST':
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        new_priority = request.POST.get('priority')
        
        # Verificar permisos
        if not request.user.groups.filter(name__in=['agent', 'supervisor']).exists():
            messages.error(request, 'No tienes permisos para actualizar la prioridad de este ticket.')
            return redirect('support_ai:ticket_detail', ticket_id=ticket_id)
        
        if new_priority in dict(SupportTicket.PRIORITY_CHOICES):
            old_priority = ticket.priority
            ticket.priority = new_priority
            ticket.save()
            
            # Crear mensaje del sistema
            Conversation.objects.create(
                ticket=ticket,
                message_type='system',
                content=f'Prioridad del ticket cambiada de {dict(SupportTicket.PRIORITY_CHOICES)[old_priority]} a {dict(SupportTicket.PRIORITY_CHOICES)[new_priority]}'
            )
            
            messages.success(request, f'Prioridad del ticket actualizada a {dict(SupportTicket.PRIORITY_CHOICES)[new_priority]}')
        
    return redirect('support_ai:ticket_detail', ticket_id=ticket_id)


@login_required
def ticket_assign(request, ticket_id):
    """
    Asignar un ticket a un agente
    """
    if request.method == 'POST':
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        agent_id = request.POST.get('agent_id')
        
        # Verificar permisos
        if not request.user.groups.filter(name__in=['agent', 'supervisor']).exists():
            messages.error(request, 'No tienes permisos para asignar tickets.')
            return redirect('support_ai:ticket_detail', ticket_id=ticket_id)
        
        if agent_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                agent = User.objects.get(id=agent_id, groups__name='agent')
                old_agent = ticket.assigned_agent
                ticket.assigned_agent = agent
                ticket.save()
                
                # Crear mensaje del sistema
                if old_agent:
                    Conversation.objects.create(
                        ticket=ticket,
                        message_type='system',
                        content=f'Ticket reasignado de {old_agent.get_full_name()} a {agent.get_full_name()}'
                    )
                else:
                    Conversation.objects.create(
                        ticket=ticket,
                        message_type='system',
                        content=f'Ticket asignado a {agent.get_full_name()}'
                    )
                
                messages.success(request, f'Ticket asignado a {agent.get_full_name()}')
            except User.DoesNotExist:
                messages.error(request, 'Agente no encontrado.')
        else:
            # Desasignar ticket
            old_agent = ticket.assigned_agent
            ticket.assigned_agent = None
            ticket.save()
            
            if old_agent:
                Conversation.objects.create(
                    ticket=ticket,
                    message_type='system',
                    content=f'Ticket desasignado de {old_agent.get_full_name()}'
                )
                messages.success(request, 'Ticket desasignado.')
        
    return redirect('support_ai:ticket_detail', ticket_id=ticket_id)


def generate_ai_response(message_content, ticket=None):
    """
    Genera una respuesta de IA avanzada usando APIs externas
    """
    try:
        # Análisis de sentimientos avanzado con IA
        sentiment_context = {
            'ticket_type': ticket.category if ticket else 'general',
            'time_elapsed': 'unknown',
            'interaction_history': 'new_user'
        }
        
        # Intentar análisis de sentimientos con IA avanzada
        ai_sentiment_result = ai_orchestrator.analyze_sentiment(message_content, sentiment_context)
        
        if ai_sentiment_result.get('success'):
            # Usar análisis de IA avanzada
            sentiment_data = ai_sentiment_result['data']
            ai_confidence = 0.9
        else:
            # Fallback al análisis básico
            sentiment_data = analyze_sentiment(message_content)
            ai_confidence = 0.6
        
        # Extraer palabras clave
        keywords = extract_keywords(message_content)
        
        # Categorizar el mensaje
        category = categorize_message(message_content)
        
        # Preparar contexto para la IA
        context = {
            'message': message_content,
            'sentiment': sentiment_data.get('sentiment', 'neutral'),
            'category': category,
            'experience_level': 'intermediate',  # Se puede mejorar con perfil del usuario
            'ticket_history': '0 tickets',  # Se puede mejorar con historial real
            'task_type': 'text',
            'prompt_type': f'support_{category}' if category != 'general_help' else 'support_general'
        }
        
        # Generar respuesta con IA avanzada
        ai_response = ai_orchestrator.generate_support_response(message_content, context)
        
        # Si la IA avanzada falla, usar respuesta contextual básica
        if ai_response.get('error') or not ai_response.get('content'):
            contextual_response = generate_contextual_response(message_content, sentiment_data, ticket)
            response_content = contextual_response['response']
            ai_confidence = 0.5
        else:
            response_content = ai_response['content']
            ai_confidence = 0.9
        
        # Personalizar sugerencias según la categoría
        category_suggestions = {
            'billing': [
                "¿Cómo cambiar mi método de pago?",
                "¿Dónde puedo ver mis facturas?",
                "¿Cómo cancelar mi suscripción?"
            ],
            'technical': [
                "¿Cuándo empezó el problema?",
                "¿Has intentado reiniciar el sistema?",
                "¿Puedes compartir una captura de pantalla?"
            ],
            'configuration': [
                "Configurar notificaciones",
                "Personalizar el dashboard",
                "Configurar integraciones"
            ],
            'feature_request': [
                "¿Qué funcionalidad específica necesitas?",
                "¿Te gustaría ver ejemplos similares?",
                "¿Es para uso personal o empresarial?"
            ],
            'general_help': [
                "¿Puedes ser más específico?",
                "¿Has revisado la documentación?",
                "¿Te gustaría hablar con un agente?"
            ]
        }
        
        # Combinar sugerencias
        suggestions = category_suggestions.get(category, [])
        
        # Agregar información adicional para el frontend
        response_data = {
            'response': response_content,
            'suggestions': suggestions[:3],
            'confidence': ai_confidence,
            'sentiment': sentiment_data.get('sentiment', 'neutral'),
            'priority': sentiment_data.get('priority', 'low'),
            'emotions': sentiment_data.get('emotions', []),
            'category': category,
            'keywords': keywords[:5],
            'tone': 'professional_friendly',
            'ai_model': ai_response.get('model', 'fallback'),
            'ai_provider': ai_response.get('provider', 'none'),
            'response_time': ai_response.get('response_time', 0.0),
            'cost': ai_response.get('cost', 0.0)
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error en generate_ai_response: {str(e)}")
        # Fallback completo en caso de error
        return {
            'response': "Lo siento, estoy teniendo dificultades técnicas. ¿Podrías reformular tu pregunta?",
            'suggestions': ["Contactar soporte humano", "Intentar más tarde", "Revisar la documentación"],
            'confidence': 0.3,
            'sentiment': 'neutral',
            'priority': 'low',
            'emotions': [],
            'category': 'general_help',
            'keywords': [],
            'tone': 'apologetic',
            'ai_model': 'fallback',
            'ai_provider': 'none',
            'response_time': 0.0,
            'cost': 0.0,
            'error': str(e)
        }


@csrf_exempt
@require_http_methods(["POST"])
def send_message(request, ticket_id):
    """
    Enviar mensaje en un ticket (API endpoint)
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    try:
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        
        # Verificar permisos
        if not (request.user == ticket.customer or 
                request.user == ticket.assigned_agent or 
                request.user.groups.filter(name__in=['agent', 'supervisor']).exists()):
            return JsonResponse({'error': 'No tienes permisos para enviar mensajes en este ticket'}, status=403)
        
        data = json.loads(request.body)
        message_content = data.get('message', '').strip()
        
        if not message_content:
            return JsonResponse({'error': 'El mensaje no puede estar vacío'}, status=400)
        
        # Crear mensaje del usuario
        user_conversation = Conversation.objects.create(
            ticket=ticket,
            message_type='user' if request.user == ticket.customer else 'agent',
            content=message_content
        )
        
        # Generar respuesta automática de IA
        ai_response_data = generate_ai_response(message_content, ticket)
        
        # Crear respuesta de IA
        ai_conversation = Conversation.objects.create(
            ticket=ticket,
            message_type='ai',
            content=ai_response_data['response']
        )
        
        # Actualizar estado del ticket si es necesario
        if ticket.status == 'waiting_agent' and request.user == ticket.customer:
            ticket.status = 'in_progress'
            ticket.save()
        elif ticket.status == 'waiting_customer' and request.user != ticket.customer:
            ticket.status = 'in_progress'
            ticket.save()
        
        return JsonResponse({
            'success': True,
            'user_message_id': user_conversation.id,
            'ai_message_id': ai_conversation.id,
            'response': ai_response_data['response'],
            'suggestions': ai_response_data['suggestions'],
            'timestamp': user_conversation.created_at.isoformat(),
            'message_type': user_conversation.message_type
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def satisfaction_rating(request, ticket_id):
    """
    Calificar la satisfacción de un ticket
    """
    if request.method == 'POST':
        ticket = get_object_or_404(SupportTicket, id=ticket_id)
        
        # Verificar que el usuario es el cliente del ticket
        if request.user != ticket.customer:
            messages.error(request, 'Solo el cliente puede calificar este ticket.')
            return redirect('support_ai:ticket_detail', ticket_id=ticket_id)
        
        # Verificar que el ticket está resuelto
        if ticket.status != 'resolved':
            messages.error(request, 'Solo puedes calificar tickets resueltos.')
            return redirect('support_ai:ticket_detail', ticket_id=ticket_id)
        
        # Obtener datos del formulario
        overall_rating = request.POST.get('overall_rating')
        response_time_rating = request.POST.get('response_time_rating')
        solution_quality_rating = request.POST.get('solution_quality_rating')
        agent_helpfulness_rating = request.POST.get('agent_helpfulness_rating')
        comment = request.POST.get('comment', '')
        
        try:
            # Crear o actualizar calificación
            satisfaction, created = CustomerSatisfaction.objects.get_or_create(
                ticket=ticket,
                customer=request.user,
                defaults={
                    'overall_rating': overall_rating,
                    'response_time_rating': response_time_rating,
                    'solution_quality_rating': solution_quality_rating,
                    'agent_helpfulness_rating': agent_helpfulness_rating,
                    'comment': comment,
                    'sentiment_label': 'neutral'  # Por defecto, se puede mejorar con análisis de IA
                }
            )
            
            if not created:
                # Actualizar calificación existente
                satisfaction.overall_rating = overall_rating
                satisfaction.response_time_rating = response_time_rating
                satisfaction.solution_quality_rating = solution_quality_rating
                satisfaction.agent_helpfulness_rating = agent_helpfulness_rating
                satisfaction.comment = comment
                satisfaction.save()
            
            messages.success(request, '¡Gracias por tu calificación!')
            
        except Exception as e:
            messages.error(request, f'Error al guardar la calificación: {str(e)}')
    
    return redirect('support_ai:ticket_detail', ticket_id=ticket_id) 


@csrf_exempt
@require_http_methods(["POST"])
def api_upload_file(request):
    """
    Endpoint para subir archivos en el chat
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    try:
        # Obtener archivo del request
        uploaded_file = request.FILES.get('file')
        ticket_id = request.POST.get('ticket_id')
        
        if not uploaded_file:
            return JsonResponse({'error': 'No se proporcionó ningún archivo'}, status=400)
        
        # Validar tipo de archivo
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf', 
                        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Tipo de archivo no permitido'}, status=400)
        
        # Validar tamaño (10MB máximo)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'El archivo es demasiado grande (máximo 10MB)'}, status=400)
        
        # Si hay ticket_id, asociar con el ticket
        ticket = None
        if ticket_id:
            try:
                ticket = SupportTicket.objects.get(id=ticket_id)
                # Verificar permisos
                if not (request.user == ticket.customer or 
                        request.user == ticket.assigned_agent or 
                        request.user.groups.filter(name__in=['agent', 'supervisor']).exists()):
                    return JsonResponse({'error': 'No tienes permisos para subir archivos en este ticket'}, status=403)
            except SupportTicket.DoesNotExist:
                return JsonResponse({'error': 'Ticket no encontrado'}, status=404)
        
        # Guardar archivo
        file_path = f'support_attachments/{request.user.id}/{uploaded_file.name}'
        
        # Crear conversación con el archivo
        if ticket:
            conversation = Conversation.objects.create(
                ticket=ticket,
                message_type='user' if request.user == ticket.customer else 'agent',
                content=f"Archivo adjunto: {uploaded_file.name}",
                attachments=[{
                    'name': uploaded_file.name,
                    'size': uploaded_file.size,
                    'type': uploaded_file.content_type,
                    'path': file_path
                }]
            )
        
        # Análisis básico del archivo (placeholder para IA)
        analysis = f"Archivo '{uploaded_file.name}' recibido correctamente. "
        if uploaded_file.content_type.startswith('image/'):
            analysis += "Es una imagen que será procesada por nuestro sistema de IA."
        elif uploaded_file.content_type == 'application/pdf':
            analysis += "Es un documento PDF que será analizado para extraer información relevante."
        else:
            analysis += "Es un documento que será revisado por nuestro equipo."
        
        return JsonResponse({
            'success': True,
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'file_type': uploaded_file.content_type,
            'analysis': analysis,
            'message_id': conversation.id if ticket else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_voice_input(request):
    """
    Endpoint para procesar entrada de voz
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    try:
        # Obtener archivo de audio del request
        audio_file = request.FILES.get('audio')
        ticket_id = request.POST.get('ticket_id')
        
        if not audio_file:
            return JsonResponse({'error': 'No se proporcionó ningún archivo de audio'}, status=400)
        
        # Validar tipo de archivo
        if not audio_file.content_type.startswith('audio/'):
            return JsonResponse({'error': 'El archivo debe ser de audio'}, status=400)
        
        # Validar tamaño (5MB máximo para audio)
        if audio_file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'El archivo de audio es demasiado grande (máximo 5MB)'}, status=400)
        
        # Si hay ticket_id, asociar con el ticket
        ticket = None
        if ticket_id:
            try:
                ticket = SupportTicket.objects.get(id=ticket_id)
                # Verificar permisos
                if not (request.user == ticket.customer or 
                        request.user == ticket.assigned_agent or 
                        request.user.groups.filter(name__in=['agent', 'supervisor']).exists()):
                    return JsonResponse({'error': 'No tienes permisos para enviar audio en este ticket'}, status=403)
            except SupportTicket.DoesNotExist:
                return JsonResponse({'error': 'Ticket no encontrado'}, status=404)
        
        # TODO: Implementar transcripción de audio con IA
        # Por ahora, simulamos la transcripción
        transcription = "Mensaje de voz transcrito (funcionalidad en desarrollo)"
        
        # Crear conversación con el audio
        if ticket:
            conversation = Conversation.objects.create(
                ticket=ticket,
                message_type='user' if request.user == ticket.customer else 'agent',
                content=transcription,
                attachments=[{
                    'name': audio_file.name,
                    'size': audio_file.size,
                    'type': audio_file.content_type,
                    'path': f'support_audio/{request.user.id}/{audio_file.name}'
                }]
            )
        
        # Respuesta simulada de IA
        response = "He recibido tu mensaje de voz. La funcionalidad de transcripción automática estará disponible próximamente."
        
        return JsonResponse({
            'success': True,
            'transcription': transcription,
            'response': response,
            'message_id': conversation.id if ticket else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 


@csrf_exempt
@require_http_methods(["GET", "POST"])
def ai_config_endpoint(request):
    """
    Endpoint para gestionar configuración de IA
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    if request.method == 'GET':
        # Obtener configuración actual
        available_models = ai_service_manager.get_available_models()
        models_data = []
        
        for model in available_models:
            models_data.append({
                'id': model.model_id,
                'name': model.name,
                'provider': model.provider,
                'features': model.features,
                'cost_per_1k_tokens': model.cost_per_1k_tokens,
                'max_tokens': model.max_tokens,
                'temperature': model.temperature
            })
        
        return JsonResponse({
            'success': True,
            'models': models_data,
            'available_providers': list(ai_orchestrator.clients.keys()),
            'default_model': 'gpt-4o-mini'
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'test_model':
                model_id = data.get('model_id', 'gpt-4o-mini')
                test_message = data.get('message', 'Hola, ¿cómo estás?')
                
                # Probar el modelo
                messages = [
                    {'role': 'system', 'content': 'Eres un asistente de prueba. Responde brevemente.'},
                    {'role': 'user', 'content': test_message}
                ]
                
                result = ai_orchestrator.generate_response(model_id, messages)
                
                return JsonResponse({
                    'success': True,
                    'test_result': result,
                    'model_tested': model_id
                })
            
            elif action == 'get_cost_estimate':
                model_id = data.get('model_id', 'gpt-4o-mini')
                message_length = data.get('message_length', 100)
                
                # Estimar costo
                estimated_cost = ai_service_manager.estimate_cost(model_id, message_length, message_length // 2)
                
                return JsonResponse({
                    'success': True,
                    'estimated_cost': estimated_cost,
                    'model_id': model_id,
                    'input_tokens': message_length,
                    'output_tokens': message_length // 2
                })
            
            else:
                return JsonResponse({'error': 'Acción no válida'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405) 


class AIDashboardView(LoginRequiredMixin, TemplateView):
    """
    Dashboard para métricas y configuración de IA
    """
    template_name = 'support_ai/ai_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener métricas básicas
        try:
            # Métricas del día actual
            daily_metrics = ai_metrics.get_daily_metrics()
            
            # Análisis de costos de los últimos 7 días
            cost_analysis = ai_metrics.get_cost_analysis(days=7)
            
            # Métricas de rendimiento de las últimas 24 horas
            performance_metrics = ai_metrics.get_performance_metrics(hours=24)
            
            # Modelos disponibles
            available_models = ai_service_manager.get_available_models()
            
            context.update({
                'daily_metrics': daily_metrics,
                'cost_analysis': cost_analysis,
                'performance_metrics': performance_metrics,
                'available_models': available_models,
                'providers': list(ai_orchestrator.clients.keys()),
                'current_date': datetime.now().strftime('%Y-%m-%d'),
                'error': None
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas de IA: {str(e)}")
            context.update({
                'daily_metrics': {},
                'cost_analysis': {},
                'performance_metrics': {},
                'available_models': [],
                'providers': [],
                'current_date': datetime.now().strftime('%Y-%m-%d'),
                'error': f"Error cargando métricas: {str(e)}"
            })
        
        return context 


@csrf_exempt
@require_http_methods(["GET"])
def ai_metrics_endpoint(request):
    """
    Endpoint para obtener métricas de IA en tiempo real
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    try:
        metric_type = request.GET.get('type', 'daily')
        date = request.GET.get('date')
        hours = int(request.GET.get('hours', 24))
        days = int(request.GET.get('days', 7))
        
        if metric_type == 'daily':
            data = ai_metrics.get_daily_metrics(date)
        elif metric_type == 'hourly':
            data = ai_metrics.get_hourly_metrics(date)
        elif metric_type == 'cost_analysis':
            data = ai_metrics.get_cost_analysis(days)
        elif metric_type == 'performance':
            data = ai_metrics.get_performance_metrics(hours)
        else:
            return JsonResponse({'error': 'Tipo de métrica no válido'}, status=400)
        
        return JsonResponse({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ai_model_test_endpoint(request):
    """
    Endpoint para probar modelos de IA
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    try:
        data = json.loads(request.body)
        model_id = data.get('model_id', 'gpt-4o-mini')
        test_message = data.get('message', 'Hola, ¿cómo estás?')
        prompt_type = data.get('prompt_type', 'support_general')
        
        # Obtener prompt
        context = {
            'message': test_message,
            'sentiment': 'neutral',
            'category': 'general_help'
        }
        
        prompt = ai_prompt_manager.get_prompt(prompt_type, **context)
        
        # Construir mensajes
        messages = [
            {'role': 'system', 'content': prompt['system']},
            {'role': 'user', 'content': prompt['user']}
        ]
        
        # Probar el modelo
        start_time = time.time()
        result = ai_orchestrator.generate_response(model_id, messages, temperature=0.7)
        test_time = time.time() - start_time
        
        # Registrar métricas de prueba
        ai_metrics.record_request(
            provider=result.get('provider', 'unknown'),
            model_id=model_id,
            input_tokens=result.get('usage', {}).get('prompt_tokens', 0),
            output_tokens=result.get('usage', {}).get('completion_tokens', 0),
            cost=result.get('cost', 0.0),
            response_time=test_time,
            success=not result.get('error'),
            error_message=result.get('error')
        )
        
        return JsonResponse({
            'success': True,
            'test_result': result,
            'model_tested': model_id,
            'test_time': test_time,
            'prompt_type': prompt_type
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f"Error probando modelo: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def ai_settings_endpoint(request):
    """
    Endpoint para gestionar configuraciones de IA
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    if request.method == 'GET':
        # Obtener configuración actual
        try:
            # Obtener modelos disponibles
            available_models = ai_service_manager.get_available_models()
            models_data = []
            
            for model in available_models:
                models_data.append({
                    'id': model.model_id,
                    'name': model.name,
                    'provider': model.provider,
                    'features': model.features,
                    'cost_per_1k_tokens': model.cost_per_1k_tokens,
                    'max_tokens': model.max_tokens,
                    'temperature': model.temperature,
                    'is_available': model.is_available
                })
            
            # Obtener configuración de proveedores
            providers_config = {}
            for provider, config in ai_service_manager.providers.items():
                providers_config[provider] = {
                    'has_api_key': bool(config.get('api_key')),
                    'base_url': config.get('base_url'),
                    'timeout': config.get('timeout'),
                    'max_retries': config.get('max_retries')
                }
            
            return JsonResponse({
                'success': True,
                'models': models_data,
                'providers': providers_config,
                'available_clients': list(ai_orchestrator.clients.keys()),
                'default_model': 'gpt-4o-mini'
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo configuración: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            # Obtener datos del formulario
            ai_model = request.POST.get('ai_model', 'gpt-4o-mini')
            daily_cost_limit = float(request.POST.get('daily_cost_limit', 10.0))
            auto_assignment = request.POST.get('auto_assignment', 'false').lower() == 'true'
            max_response_time = int(request.POST.get('max_response_time', 24))
            
            # Validar datos
            valid_models = ['gpt-4o-mini', 'gpt-4o', 'claude-3-haiku', 'claude-3-sonnet']
            if ai_model not in valid_models:
                return JsonResponse({'error': 'Modelo de IA no válido'}, status=400)
            
            if daily_cost_limit < 0:
                return JsonResponse({'error': 'El límite de costos debe ser positivo'}, status=400)
            
            if max_response_time < 1 or max_response_time > 168:
                return JsonResponse({'error': 'El tiempo de respuesta debe estar entre 1 y 168 horas'}, status=400)
            
            # Obtener o crear configuraciones del sistema
            system_settings = SystemSettings.get_settings()
            
            # Actualizar configuraciones
            system_settings.ai_model = ai_model
            system_settings.daily_cost_limit = daily_cost_limit
            system_settings.auto_assignment = auto_assignment
            system_settings.max_response_time = max_response_time
            system_settings.save()
            
            logger.info(f"Configuraciones del sistema guardadas: model={ai_model}, cost_limit={daily_cost_limit}, auto_assignment={auto_assignment}, max_response_time={max_response_time}")
            
            return JsonResponse({
                'success': True,
                'message': 'Configuraciones del sistema guardadas exitosamente',
                'settings': {
                    'ai_model': ai_model,
                    'daily_cost_limit': daily_cost_limit,
                    'auto_assignment': auto_assignment,
                    'max_response_time': max_response_time
                }
            })
            
        except ValueError as e:
            return JsonResponse({'error': 'Datos inválidos en el formulario'}, status=400)
        except Exception as e:
            logger.error(f"Error guardando configuraciones del sistema: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405) 


@csrf_exempt
@require_http_methods(["GET"])
def ai_analytics_endpoint(request):
    """
    Endpoint para obtener analytics avanzados
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    try:
        analytics_type = request.GET.get('type', 'comprehensive')
        days = int(request.GET.get('days', 30))
        
        if analytics_type == 'comprehensive':
            data = ai_analytics.get_comprehensive_metrics(days)
        elif analytics_type == 'realtime':
            data = ai_analytics.get_realtime_dashboard_data()
        else:
            return JsonResponse({'error': 'Tipo de analytics no válido'}, status=400)
        
        return JsonResponse({
            'success': True,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo analytics: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500) 


@csrf_exempt
@require_http_methods(["GET", "POST"])
def user_settings_endpoint(request):
    """
    Endpoint para gestionar configuraciones de usuario
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
    
    if request.method == 'GET':
        # Obtener configuraciones actuales del usuario
        try:
            # Obtener o crear configuraciones del usuario
            user_settings_obj, created = UserSettings.objects.get_or_create(
                user=request.user,
                defaults={
                    'notifications_enabled': True,
                    'push_notifications': True,
                    'language': 'es',
                    'theme': 'light',
                }
            )
            
            user_settings = {
                'notifications_enabled': user_settings_obj.notifications_enabled,
                'push_notifications': user_settings_obj.push_notifications,
                'language': user_settings_obj.language,
                'theme': user_settings_obj.theme,
            }
            
            return JsonResponse({
                'success': True,
                'settings': user_settings
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo configuraciones de usuario: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            # Obtener datos del formulario (soporta tanto POST como JSON)
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                notifications_enabled = data.get('notifications_enabled', False)
                push_notifications = data.get('push_notifications', False)
                language = data.get('language', 'es')
                theme = data.get('theme', 'light')
            else:
                notifications_enabled = request.POST.get('notifications_enabled', 'false').lower() == 'true'
                push_notifications = request.POST.get('push_notifications', 'false').lower() == 'true'
                language = request.POST.get('language', 'es')
                theme = request.POST.get('theme', 'light')
            
            # Validar datos
            if language not in ['es', 'en', 'fr']:
                return JsonResponse({'error': 'Idioma no válido'}, status=400)
            
            if theme not in ['light', 'dark', 'auto']:
                return JsonResponse({'error': 'Tema no válido'}, status=400)
            
            # Obtener o crear configuraciones del usuario
            user_settings_obj, created = UserSettings.objects.get_or_create(
                user=request.user,
                defaults={
                    'notifications_enabled': notifications_enabled,
                    'push_notifications': push_notifications,
                    'language': language,
                    'theme': theme,
                }
            )
            
            # Actualizar configuraciones existentes
            if not created:
                user_settings_obj.notifications_enabled = notifications_enabled
                user_settings_obj.push_notifications = push_notifications
                user_settings_obj.language = language
                user_settings_obj.theme = theme
                user_settings_obj.save()
            
            logger.info(f"Configuraciones guardadas para usuario {request.user.id}: notifications={notifications_enabled}, push={push_notifications}, language={language}, theme={theme}")
            
            return JsonResponse({
                'success': True,
                'message': 'Configuraciones guardadas exitosamente',
                'settings': {
                    'notifications_enabled': notifications_enabled,
                    'push_notifications': push_notifications,
                    'language': language,
                    'theme': theme
                }
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando JSON: {str(e)}")
            return JsonResponse({'error': 'Datos JSON inválidos'}, status=400)
        except Exception as e:
            logger.error(f"Error guardando configuraciones de usuario: {str(e)}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405) 


@csrf_exempt
@require_http_methods(["GET"])
def debug_tables_endpoint(request):
    """
    Endpoint temporal para diagnosticar problemas con las tablas
    """
    try:
        from django.db import connection
        cursor = connection.cursor()
        
        # Verificar si las tablas existen
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('support_ai_systemsettings', 'support_ai_usersettings')
        """)
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        # Intentar importar los modelos
        try:
            from .models import UserSettings, SystemSettings
            models_imported = True
        except Exception as e:
            models_imported = False
            import_error = str(e)
        
        # Intentar hacer una consulta simple
        try:
            if models_imported:
                us_count = UserSettings.objects.count()
                ss_count = SystemSettings.objects.count()
                query_success = True
            else:
                us_count = None
                ss_count = None
                query_success = False
        except Exception as e:
            us_count = None
            ss_count = None
            query_success = False
            query_error = str(e)
        
        return JsonResponse({
            'tables_exist': table_names,
            'models_imported': models_imported,
            'query_success': query_success,
            'user_settings_count': us_count,
            'system_settings_count': ss_count,
            'import_error': import_error if not models_imported else None,
            'query_error': query_error if not query_success else None,
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'type': type(e).__name__
        }, status=500) 