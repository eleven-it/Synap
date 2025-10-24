from django.urls import path, include
from django.http import HttpResponse
from .views import (
    placeholder_view, SupportSettingsView, PortalHomeView, TicketListView, TicketCreateView,
    TicketDetailView, ChatView, ticket_status_update, ticket_priority_update, ticket_assign, 
    send_message, satisfaction_rating, api_upload_file, api_voice_input,
    ai_config_endpoint, AIDashboardView, ai_metrics_endpoint, ai_model_test_endpoint, 
    ai_settings_endpoint, ai_analytics_endpoint, user_settings_endpoint
)
from . import auth_views

app_name = 'support_ai'

urlpatterns = [
    # Portal principal
    path('portal/', PortalHomeView.as_view(), name='portal_home'),
    path('portal/my-tickets/', placeholder_view, name='portal_my_tickets'),  # Usar placeholder por ahora
    path('portal/knowledge-base/', placeholder_view, name='portal_knowledge_base'),
    path('portal/profile/', placeholder_view, name='portal_profile'),
    
    # Gestión de tickets
    path('tickets/', TicketListView.as_view(), name='ticket_list'),
    path('tickets/create/', TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<uuid:ticket_id>/', TicketDetailView.as_view(), name='ticket_detail'),
    
    # Acciones de tickets
    path('tickets/<uuid:ticket_id>/status/', ticket_status_update, name='ticket_status_update'),
    path('tickets/<uuid:ticket_id>/priority/', ticket_priority_update, name='ticket_priority_update'),
    path('tickets/<uuid:ticket_id>/assign/', ticket_assign, name='ticket_assign'),
    path('tickets/<uuid:ticket_id>/satisfaction/', satisfaction_rating, name='satisfaction_rating'),
    
    # Chat y mensajes
    path('chat/', ChatView.as_view(), name='chat'),
    path('tickets/<uuid:ticket_id>/chat/', placeholder_view, name='chat_ticket'),  # Usar placeholder por ahora
    path('tickets/<uuid:ticket_id>/send-message/', send_message, name='send_message'),
    
    # API endpoints para chat
    path('api/upload-file/', api_upload_file, name='api_upload_file'),
    path('api/voice-input/', api_voice_input, name='api_voice_input'),
    path('api/ai-config/', ai_config_endpoint, name='ai_config'),
    path('api/ai-metrics/', ai_metrics_endpoint, name='ai_metrics'),
    path('api/ai-model-test/', ai_model_test_endpoint, name='ai_model_test'),
    path('api/ai-settings/', ai_settings_endpoint, name='ai_settings'),
    path('api/ai-analytics/', ai_analytics_endpoint, name='ai_analytics'),
    path('api/user-settings/', user_settings_endpoint, name='user_settings'),
    path('ai-dashboard/', AIDashboardView.as_view(), name='ai_dashboard'),
    
    # Sistema de autenticación unificado del chat (vistas reales)
    path('auth/login/', auth_views.chat_login, name='auth_login'),
    path('auth/logout/', auth_views.chat_logout, name='auth_logout'),
    path('auth/user-info/', auth_views.chat_user_info, name='auth_user_info'),
    path('auth/change-password/', auth_views.chat_change_password, name='auth_change_password'),
    path('auth/send-message/', auth_views.chat_send_message, name='auth_send_message'),
    path('auth/get-history/', auth_views.chat_get_history, name='auth_get_history'),
    path('auth/user-tickets/', auth_views.chat_user_tickets, name='auth_user_tickets'),
    path('auth/login-page/', auth_views.chat_login_page, name='auth_login_page'),
    path('auth/chat/', auth_views.chat_interface, name='auth_chat'),
    path('auth/profile/', auth_views.chat_profile, name='auth_profile'),
    
    # Vistas temporales (pendientes de implementar)
    path('', placeholder_view, name='chat_main'),
    path('chat/old/', placeholder_view, name='chat_old'),
    path('support-dashboard/', placeholder_view, name='support_dashboard'),
    path('settings/', SupportSettingsView.as_view(), name='settings'),
    path('knowledge/', placeholder_view, name='knowledge_base'),
    
    # Gestión de agentes
    path('agents/', placeholder_view, name='agent_management'),
    
    # Agentes dinámicos
    path('dynamic-agents/', placeholder_view, name='dynamic_agents'),
] 