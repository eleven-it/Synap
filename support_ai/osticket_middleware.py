"""
Middleware personalizado para manejar autenticación de osTicket
"""

import logging
from django.contrib.auth import get_user
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from .osticket_auth import get_osticket_auth

logger = logging.getLogger(__name__)


class OsTicketAuthMiddleware(MiddlewareMixin):
    """
    Middleware para manejar autenticación de osTicket en el chat
    """
    
    def process_request(self, request):
        """
        Procesa cada request para verificar autenticación de osTicket
        """
        # Solo aplicar a endpoints del chat
        if not request.path.startswith('/support/auth/'):
            return None
        
        # Obtener usuario de Django
        user = get_user(request)
        
        # Si no hay usuario autenticado en Django, continuar
        if isinstance(user, AnonymousUser):
            return None
        
        # Verificar si la sesión de osTicket está válida
        osticket_user_id = request.session.get('osticket_user_id')
        if not osticket_user_id:
            # Limpiar sesión de Django si no hay sesión de osTicket
            from django.contrib.auth import logout
            logout(request)
            return None
        
        # Verificar que el usuario de osTicket siga siendo válido
        try:
            auth = get_osticket_auth()
            user_info = auth.get_user_info(osticket_user_id)
            
            if not user_info.get('success'):
                # Usuario de osTicket ya no válido, limpiar sesión
                logger.warning(f"Usuario osTicket {osticket_user_id} ya no válido")
                from django.contrib.auth import logout
                logout(request)
                
                # Limpiar variables de sesión
                for key in ['osticket_user_id', 'osticket_username', 'osticket_email', 'osticket_roles']:
                    if key in request.session:
                        del request.session[key]
                
                return None
                
        except Exception as e:
            logger.error(f"Error verificando usuario osTicket: {e}")
            return None
        
        return None
    
    def process_response(self, request, response):
        """
        Procesa la respuesta para agregar headers de autenticación
        """
        # Solo aplicar a endpoints del chat
        if not request.path.startswith('/support/auth/'):
            return response
        
        # Agregar headers de autenticación si el usuario está autenticado
        if hasattr(request, 'user') and request.user.is_authenticated:
            osticket_user_id = request.session.get('osticket_user_id')
            if osticket_user_id:
                response['X-OsTicket-User-ID'] = str(osticket_user_id)
                response['X-OsTicket-Username'] = request.session.get('osticket_username', '')
        
        return response


class ChatSessionMiddleware(MiddlewareMixin):
    """
    Middleware para manejar sesiones del chat
    """
    
    def process_request(self, request):
        """
        Inicializa la sesión del chat si no existe
        """
        # Solo aplicar a endpoints del chat
        if not request.path.startswith('/support/auth/'):
            return None
        
        # Inicializar historial del chat si no existe
        if 'chat_history' not in request.session:
            request.session['chat_history'] = []
        
        return None
    
    def process_response(self, request, response):
        """
        Limpia sesiones del chat expiradas
        """
        # Solo aplicar a endpoints del chat
        if not request.path.startswith('/support/auth/'):
            return response
        
        # Limpiar historial del chat si es muy largo
        chat_history = request.session.get('chat_history', [])
        if len(chat_history) > 50:  # Mantener solo los últimos 50 mensajes
            request.session['chat_history'] = chat_history[-50:]
        
        return response
