"""
Vistas de Autenticación para el Chat
Integra con el sistema de autenticación de osTicket
"""

import logging
import json
from typing import Dict, Any
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def chat_login(request):
    """
    Endpoint de login para el chat usando credenciales de osTicket
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return JsonResponse({
                'success': False,
                'error': 'Usuario y contraseña son requeridos'
            }, status=400)
        
        # Importar aquí para evitar problemas de importación circular
        from .osticket_auth import get_osticket_auth
        
        # Autenticar con osTicket
        auth = get_osticket_auth()
        auth_result = auth.authenticate_user(username, password)
        
        if auth_result['success']:
            user_data = auth_result['user']
            
            # Crear sesión en Django
            if user_data.get('django_user_id'):
                from django.contrib.auth.models import User
                django_user = User.objects.get(id=user_data['django_user_id'])
                login(request, django_user)
                
                # Guardar información del usuario en la sesión
                request.session['osticket_user_id'] = user_data['id']
                request.session['osticket_username'] = user_data['username']
                request.session['osticket_email'] = user_data['email']
                request.session['osticket_roles'] = user_data['roles']
                
                logger.info(f"Usuario autenticado: {user_data['username']}")
                
                return JsonResponse({
                    'success': True,
                    'user': {
                        'id': user_data['id'],
                        'username': user_data['username'],
                        'email': user_data['email'],
                        'full_name': user_data['full_name'],
                        'roles': user_data['roles']
                    },
                    'message': 'Autenticación exitosa'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Error sincronizando usuario con Django'
                }, status=500)
        else:
            return JsonResponse({
                'success': False,
                'error': auth_result['error']
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error en login del chat: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_logout(request):
    """
    Endpoint de logout para el chat
    """
    try:
        # Limpiar sesión de osTicket
        if 'osticket_user_id' in request.session:
            del request.session['osticket_user_id']
        if 'osticket_username' in request.session:
            del request.session['osticket_username']
        if 'osticket_email' in request.session:
            del request.session['osticket_email']
        if 'osticket_roles' in request.session:
            del request.session['osticket_roles']
        
        # Logout de Django
        logout(request)
        
        return JsonResponse({
            'success': True,
            'message': 'Logout exitoso'
        })
        
    except Exception as e:
        logger.error(f"Error en logout del chat: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def chat_user_info(request):
    """
    Obtiene información del usuario autenticado
    """
    try:
        # Verificar si el usuario está autenticado
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no autenticado'
            }, status=401)
        
        # Obtener información de la sesión
        osticket_user_id = request.session.get('osticket_user_id')
        if not osticket_user_id:
            return JsonResponse({
                'success': False,
                'error': 'Sesión de osTicket no encontrada'
            }, status=401)
        
        # Importar aquí para evitar problemas de importación circular
        from .osticket_auth import get_osticket_auth
        
        # Obtener información actualizada del usuario
        auth = get_osticket_auth()
        user_info = auth.get_user_info(osticket_user_id)
        
        if user_info.get('success'):
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user_info['user']['id'],
                    'username': user_info['user']['name'],
                    'email': user_info['user']['email'],
                    'status': user_info['user']['status'],
                    'roles': user_info['roles'],
                    'tickets': user_info['tickets']
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': user_info.get('error', 'Error obteniendo información del usuario')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error obteniendo información del usuario: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_change_password(request):
    """
    Cambia la contraseña del usuario autenticado
    """
    try:
        # Verificar autenticación
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no autenticado'
            }, status=401)
        
        data = json.loads(request.body)
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not old_password or not new_password:
            return JsonResponse({
                'success': False,
                'error': 'Contraseña actual y nueva son requeridas'
            }, status=400)
        
        if len(new_password) < 6:
            return JsonResponse({
                'success': False,
                'error': 'La nueva contraseña debe tener al menos 6 caracteres'
            }, status=400)
        
        # Cambiar contraseña en osTicket
        osticket_user_id = request.session.get('osticket_user_id')
        if not osticket_user_id:
            return JsonResponse({
                'success': False,
                'error': 'Sesión de osTicket no encontrada'
            }, status=401)
        
        # Importar aquí para evitar problemas de importación circular
        from .osticket_auth import get_osticket_auth
        
        auth = get_osticket_auth()
        change_result = auth.change_password(osticket_user_id, old_password, new_password)
        
        if change_result.get('success'):
            return JsonResponse({
                'success': True,
                'message': 'Contraseña actualizada exitosamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': change_result.get('error', 'Error cambiando contraseña')
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def chat_send_message(request):
    """
    Envía un mensaje al chat (requiere autenticación)
    """
    try:
        # Verificar autenticación básica
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Usuario no autenticado'
            }, status=401)
        
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'El mensaje es requerido'
            }, status=400)
        
        # Obtener información del usuario de la sesión
        osticket_user_id = request.session.get('osticket_user_id')
        osticket_email = request.session.get('osticket_email')
        
        if not osticket_user_id or not osticket_email:
            return JsonResponse({
                'success': False,
                'error': 'Sesión de osTicket no válida'
            }, status=401)
        
        # Obtener historial de conversación de la sesión
        conversation_history = request.session.get('chat_history', [])
        
        # Importar aquí para evitar problemas de importación circular
        from .chat_system_simple import get_chat_system_simple
        
        # Procesar mensaje con el sistema de chat
        chat_system = get_chat_system_simple()
        result = chat_system.process_message(
            message=message,
            user_id=str(osticket_user_id),
            user_email=osticket_email,
            conversation_history=conversation_history
        )
        
        if result['success']:
            # Actualizar historial en la sesión
            request.session['chat_history'] = result.get('conversation_history', [])
            
            return JsonResponse({
                'success': True,
                'response': result['response'],
                'ticket_created': result.get('ticket_created', False),
                'ticket_info': result.get('ticket_info'),
                'analysis': result.get('analysis', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Error procesando mensaje')
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Formato JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error enviando mensaje al chat: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def chat_get_history(request):
    """
    Obtiene el historial de conversación del usuario
    """
    try:
        # Obtener historial de la sesión
        conversation_history = request.session.get('chat_history', [])
        
        return JsonResponse({
            'success': True,
            'history': conversation_history
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo historial del chat: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


# Vistas de plantillas HTML

def chat_login_page(request):
    """
    Página de login del chat
    """
    return render(request, 'support_ai/chat_login.html')


def chat_interface(request):
    """
    Interfaz principal del chat (requiere autenticación)
    """
    if not request.user.is_authenticated:
        return redirect('support_ai:auth_login_page')
    
    return render(request, 'support_ai/chat_interface.html')


def chat_profile(request):
    """
    Página de perfil del usuario (requiere autenticación)
    """
    if not request.user.is_authenticated:
        return redirect('support_ai:auth_login_page')
    
    return render(request, 'support_ai/chat_profile.html')


# Vistas protegidas con permisos específicos

@csrf_exempt
@require_http_methods(["GET"])
def chat_user_tickets(request):
    """
    Obtiene los tickets del usuario autenticado
    """
    try:
        osticket_user_id = request.session.get('osticket_user_id')
        
        # Importar aquí para evitar problemas de importación circular
        from .osticket_auth import get_osticket_auth
        
        auth = get_osticket_auth()
        user_info = auth.get_user_info(osticket_user_id)
        
        if user_info.get('success'):
            return JsonResponse({
                'success': True,
                'tickets': user_info['tickets']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': user_info.get('error', 'Error obteniendo tickets')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error obteniendo tickets del usuario: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def chat_admin_dashboard(request):
    """
    Dashboard de administración del chat (solo administradores)
    """
    try:
        # Aquí se podrían agregar estadísticas del sistema
        stats = {
            'total_users': 0,  # Implementar contador real
            'active_chats': 0,
            'tickets_created': 0
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo dashboard de admin: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


# Vistas basadas en clases

class ChatAdminView(View):
    """
    Vista de administración del chat
    """
    
    def get(self, request):
        """GET: Mostrar dashboard de administración"""
        return chat_admin_dashboard(request)
    
    def post(self, request):
        """POST: Acciones de administración"""
        # Implementar acciones administrativas
        pass


class ChatStaffView(View):
    """
    Vista para staff del chat
    """
    
    def get(self, request):
        """GET: Mostrar vista de staff"""
        return JsonResponse({
            'success': True,
            'message': 'Vista de staff accedida'
        })
