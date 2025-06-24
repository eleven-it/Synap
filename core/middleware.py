import logging
from django.utils import translation
from django.utils.functional import SimpleLazyObject
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.utils.http import urlencode
from django.conf import settings
from core.models import UsuarioExtendido
from core.views.views_auth import redireccionar_segun_rol
from core.constantes_permisos import PERMISOS_AUDITABLES
import time
import json

logger = logging.getLogger(__name__)


def get_usuario_extendiendo_desde_sesion(request):
    session_user = request.session.get("user")
    
    if not session_user:
        from django.contrib.auth.models import AnonymousUser
        return AnonymousUser()

    # Usar cache para mejorar rendimiento
    cache_key = f"user_session_{session_user.get('uid', '')}"
    user = cache.get(cache_key)
    
    if user is None:
        try:
            user = UsuarioExtendido.objects.get(uid=session_user["uid"])
            # Cache por 5 minutos
            cache.set(cache_key, user, 300)
        except UsuarioExtendido.DoesNotExist:
            logger.warning(f"Usuario no encontrado con UID: {session_user.get('uid')}")
            from django.contrib.auth.models import AnonymousUser
            return AnonymousUser()

    return user


class RateLimitMiddleware:
    """Middleware para limitar requests por IP"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit = getattr(settings, 'RATE_LIMIT', 100)  # requests por minuto
        self.rate_limit_window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)  # segundos

    def __call__(self, request):
        client_ip = self.get_client_ip(request)
        cache_key = f"rate_limit_{client_ip}"
        
        # Obtener requests actuales
        requests = cache.get(cache_key, [])
        now = time.time()
        
        # Limpiar requests antiguos
        requests = [req for req in requests if now - req < self.rate_limit_window]
        
        if len(requests) >= self.rate_limit:
            logger.warning(f"Rate limit excedido para IP: {client_ip}")
            from django.http import HttpResponseTooManyRequests
            return HttpResponseTooManyRequests("Demasiadas requests. Intente más tarde.")
        
        # Agregar request actual
        requests.append(now)
        cache.set(cache_key, requests, self.rate_limit_window)
        
        return self.get_response(request)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        if path.startswith("/admin/") and not path.startswith("/admin/login"):
            session_user = request.session.get("user")
            if not session_user:
                logger.warning(f"Intento de acceso a admin sin autenticación: {path}")
                login_url = "/login/"
                params = urlencode({"next": path})
                return redirect(f"{login_url}?{params}")

            user = get_usuario_extendiendo_desde_sesion(request)
            if not user.roles.filter(nombre__iexact="administrador", activo=True).exists():
                logger.warning(f"Intento de acceso a admin sin permisos: {user.email} - {path}")
                raise PermissionDenied()

        return self.get_response(request)


class IdiomaUsuarioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_user = request.session.get("user")
        
        idioma = session_user.get("idioma") if session_user else None
        if idioma in ["es", "en", "pt"]:
            translation.activate(idioma)
            request.LANGUAGE_CODE = idioma

        request.user = SimpleLazyObject(lambda: get_usuario_extendiendo_desde_sesion(request))

        response = self.get_response(request)
        translation.deactivate()
        return response


class AuditoriaMiddleware:
    """Middleware para auditar acciones críticas"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Procesar request
        response = self.get_response(request)
        
        # Auditar acciones críticas
        self.auditar_accion_critica(request, response)
        
        return response
    
    def auditar_accion_critica(self, request, response):
        """Audita acciones que requieren seguimiento especial"""
        if request.method not in ['POST', 'PUT', 'DELETE']:
            return
            
        user = getattr(request, 'user', None)
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            return
            
        # Verificar si la acción es auditable
        path = request.path
        metodo = request.method
        
        # Lista de patrones de URL auditable
        patrones_auditables = [
            '/usuarios/eliminar/',
            '/clientes/eliminar/',
            '/proveedores/eliminar/',
            '/inventario/ajustar/',
            '/ventas/anular/',
            '/compras/anular/',
            '/finance/pagos/',
            '/admin/backup/',
        ]
        
        if any(patron in path for patron in patrones_auditables):
            self.registrar_auditoria(request, response)
    
    def registrar_auditoria(self, request, response):
        """Registra la acción en el log de auditoría"""
        try:
            user = request.user
            datos_auditoria = {
                'timestamp': time.time(),
                'usuario': user.email if hasattr(user, 'email') else 'anonymous',
                'uid': user.uid if hasattr(user, 'uid') else None,
                'ip': self.get_client_ip(request),
                'metodo': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'referer': request.META.get('HTTP_REFERER', ''),
            }
            
            # Log específico para auditoría
            logger.info(f"AUDITORIA: {json.dumps(datos_auditoria)}")
            
        except Exception as e:
            logger.error(f"Error al registrar auditoría: {e}")
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PerformanceMiddleware:
    """Middleware para monitorear performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Calcular tiempo de respuesta
        duration = time.time() - start_time
        
        # Log requests lentos (> 1 segundo)
        if duration > 1.0:
            logger.warning(f"Request lento: {request.path} - {duration:.2f}s")
        
        # Agregar header de performance
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response


class SeguridadMiddleware:
    """Middleware para headers de seguridad"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # CSP básico
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        
        return response
