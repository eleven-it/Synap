"""
URLs para el sistema de autenticación del chat
"""

from django.urls import path
from . import auth_views

app_name = 'chat_auth'

urlpatterns = [
    # Endpoints de autenticación
    path('login/', auth_views.chat_login, name='chat_login'),
    path('logout/', auth_views.chat_logout, name='chat_logout'),
    path('user-info/', auth_views.chat_user_info, name='chat_user_info'),
    path('change-password/', auth_views.chat_change_password, name='chat_change_password'),
    
    # Endpoints del chat
    path('send-message/', auth_views.chat_send_message, name='chat_send_message'),
    path('get-history/', auth_views.chat_get_history, name='chat_get_history'),
    path('user-tickets/', auth_views.chat_user_tickets, name='chat_user_tickets'),
    
    # Páginas HTML
    path('login-page/', auth_views.chat_login_page, name='chat_login_page'),
    path('chat/', auth_views.chat_interface, name='chat_interface'),
    path('profile/', auth_views.chat_profile, name='chat_profile'),
]
