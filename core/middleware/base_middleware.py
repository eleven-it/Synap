import logging
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
import re
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


def get_usuario_extendiendo_desde_sesion(request):
    """
    Obtiene el usuario desde la sesión.
    Compatible con ambos sistemas: Firebase (uid) y administraNET (id_usuario/cod_usuario)
    """
    session_user = request.session.get("user")
    
    if not session_user:
        from django.contrib.auth.models import AnonymousUser
        return AnonymousUser()

    # Sistema administraNET Analytics (nuevo)
    if 'id_usuario' in session_user or 'cod_usuario' in session_user:
        # Crear un objeto usuario mock compatible con el sistema existente
        # Esto permite que el código existente funcione sin cambios mayores
        from django.contrib.auth.models import AnonymousUser
        
        class AdministraNETUser(AnonymousUser):
            """Usuario mock para compatibilidad con administraNET Analytics"""
            def __init__(self, session_data):
                super().__init__()
                self.id_usuario = session_data.get('id_usuario')
                self.cod_usuario = session_data.get('cod_usuario')
                self.nombre_usuario = session_data.get('nombre_usuario', '')
                self.apellido_usuario = session_data.get('apellido_usuario', '')
                self.nombre_completo = session_data.get('nombre_completo', '')
                self.id_empresa = session_data.get('id_empresa')
                self.id_sucursal = session_data.get('id_sucursal')
                self.id_puesto = session_data.get('id_puesto')
                self.nombre_puesto = session_data.get('nombre_puesto')
                self.base_empresa = session_data.get('base_empresa')
                self.idioma = session_data.get('idioma', 'es')
                self.email = session_data.get('email', f"{self.cod_usuario}@administranet.local")
                self.uid = session_data.get('uid', f"adminet_{self.id_usuario}")
                self.pk = self.id_usuario  # Para compatibilidad con is_admin()
                
                # Mock de roles y permisos_extra para compatibilidad con código existente
                self._roles_manager = RolesManager(self)
                self._permisos_extra_manager = PermisosExtraManager(self)
                
            @property
            def is_authenticated(self):
                return True
                
            @property
            def is_active(self):
                return True
                
            @property
            def is_staff(self):
                return False
                
            @property
            def is_superuser(self):
                # Por defecto, supervisor en administraNET tiene permisos de superuser
                return self.is_admin()
                
            def is_admin(self):
                """
                Verifica si el usuario es superuser (solo el usuario 'supervisor' por cod_usuario)
                NOTA: El puesto/rol "Supervisor" NO otorga permisos de admin, solo permisos específicos
                """
                if not self.pk:
                    return False
                # Solo el usuario con cod_usuario == 'supervisor' es superuser
                cod_usuario_lower = (self.cod_usuario or '').lower()
                if cod_usuario_lower == 'supervisor':
                    return True
                # El puesto/rol "Supervisor" NO otorga permisos de admin
                return False
                
            def tiene_permiso(self, codigo):
                """
                Verifica si el usuario tiene un permiso específico
                """
                # Si es admin (usuario supervisor), tiene todos los permisos
                if self.is_admin():
                    return True
                
                # Obtener permisos del usuario
                permisos = self.get_permisos_totales()
                
                # Si tiene acceso total, tiene todos los permisos
                if "*" in permisos:
                    return True
                
                # Verificar si tiene el permiso específico
                if codigo in permisos:
                    return True
                
                # Verificar si tiene permisos con wildcard (ej: "reports.*" para "reports.ver")
                for permiso in permisos:
                    if permiso.endswith(".*"):
                        modulo = permiso[:-2]  # Remover ".*"
                        if codigo.startswith(modulo + "."):
                            return True
                
                return False
                
            def get_permisos_totales(self):
                """Obtiene todos los permisos del usuario basado en puesto/rol de administraNET"""
                # Solo el usuario 'supervisor' (por cod_usuario) tiene acceso total
                if self.is_admin():
                    return {"*"}
                
                # Consultar permisos desde la base de datos de administraNET
                permisos = set()
                
                # Obtener base_empresa de la sesión o del usuario
                base_empresa = getattr(self, 'base_empresa', None)
                id_puesto = getattr(self, 'id_puesto', None)
                
                if base_empresa and id_puesto:
                    try:
                        # Usar conexión MySQL directa (compatible con MySQL 5.7+)
                        import MySQLdb
                        from django.conf import settings
                        mysql_config = settings.DATABASES['mysql']
                        
                        conn = MySQLdb.connect(
                            host=mysql_config['HOST'],
                            port=int(mysql_config['PORT']),
                            user=mysql_config['USER'],
                            passwd=mysql_config['PASSWORD'],
                            db=base_empresa,
                            charset='latin1'
                        )
                        cursor = conn.cursor()
                        
                        # Consultar permisos desde permiso_sistema_puesto
                        # Obtener el valor_permiso más reciente para cada permiso del puesto
                        cursor.execute("""
                            SELECT ps.key_permiso, psp.valor_permiso
                            FROM permiso_sistema ps
                            INNER JOIN (
                                SELECT psp1.id_permiso_sistema, psp1.valor_permiso
                                FROM permiso_sistema_puesto psp1
                                INNER JOIN (
                                    SELECT id_permiso_sistema, MAX(id_permiso_sistema_puesto) as max_id
                                    FROM permiso_sistema_puesto
                                    WHERE id_puesto = %s
                                    GROUP BY id_permiso_sistema
                                ) psp2 ON psp1.id_permiso_sistema = psp2.id_permiso_sistema 
                                       AND psp1.id_permiso_sistema_puesto = psp2.max_id
                                WHERE psp1.id_puesto = %s
                            ) psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
                            WHERE psp.valor_permiso = 'Si'
                        """, [id_puesto, id_puesto])
                        
                        results = cursor.fetchall()
                        for row in results:
                            key_permiso = row[0]
                            if key_permiso:
                                permisos.add(key_permiso)
                        
                        cursor.close()
                        conn.close()
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Error al obtener permisos desde MySQL para puesto {id_puesto}: {e}")
                
                # Si el puesto es "Supervisor", agregar permisos de Synap (Reports) incluso si ya hay permisos de administraNET
                if hasattr(self, 'nombre_puesto') and self.nombre_puesto:
                    if self.nombre_puesto.lower() == 'supervisor':
                        # Agregar permisos de Synap al set existente (no reemplazar)
                        permisos.update({
                            "reports.ver",
                            "reports.*",
                            "reports.view_operational",
                            "reports.view_managerial",
                            "reports.dashboard",
                        })
                
                return permisos
                
            def tiene_permiso_modulo(self, modulo):
                """Verifica si el usuario tiene algún permiso de un módulo específico"""
                permisos = self.get_permisos_totales()
                if "*" in permisos:
                    return True
                return any(perm.startswith(f"{modulo}.") for perm in permisos)
                
            def has_module_perms(self, app_label):
                """Verifica permisos de módulo para Django admin"""
                return self.is_admin() or self.tiene_permiso_modulo(app_label)
                
            def __str__(self):
                return self.nombre_completo or self.cod_usuario
                
            def get_username(self):
                return self.cod_usuario
                
            def has_perm(self, perm, obj=None):
                """Verifica permisos de Django"""
                return self.is_admin() or self.tiene_permiso(perm)
            
            @property
            def roles(self):
                """Retorna un manager mock de roles para compatibilidad"""
                return self._roles_manager
            
            @property
            def permisos_extra(self):
                """Retorna un manager mock de permisos_extra para compatibilidad"""
                return self._permisos_extra_manager
        
        # Clase helper para mock de roles
        class RolesManager:
            """Manager mock para roles, compatible con ManyToMany de Django"""
            def __init__(self, user):
                self.user = user
                
            def all(self):
                """Retorna lista vacía de roles (se puede expandir si es necesario)"""
                return []
                
            def filter(self, **kwargs):
                """Filtro mock de roles"""
                return self
                
            def exists(self):
                """Verifica si existe algún rol"""
                # Si es supervisor, retornar True para compatibilidad
                if self.user.is_admin():
                    return True
                # Verificar también por cod_usuario directamente
                if hasattr(self.user, 'cod_usuario'):
                    cod_usuario_lower = (self.user.cod_usuario or '').lower()
                    if cod_usuario_lower == 'supervisor':
                        return True
                return False
        
        # Clase helper para mock de permisos_extra
        class PermisosExtraManager:
            """Manager mock para permisos_extra, compatible con ManyToMany de Django"""
            def __init__(self, user):
                self.user = user
                
            def all(self):
                """Retorna lista vacía de permisos (se puede expandir si es necesario)"""
                return []
                
            def filter(self, **kwargs):
                """Filtro mock de permisos"""
                return self
                
            def values_list(self, *args, **kwargs):
                """Retorna lista vacía de valores (para compatibilidad con .values_list('codigo', flat=True))"""
                return []
                
            def exists(self):
                """Verifica si existe algún permiso"""
                return False
        
        return AdministraNETUser(session_user)
    
    # Sistema Firebase (legacy - mantener por compatibilidad)
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


# IdiomaUsuarioMiddleware eliminado - no se usa internacionalización, solo español


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


class CDNCacheMiddleware:
    """
    Middleware para agregar headers de cache apropiados para CDN
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Solo aplicar a archivos estáticos y media
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            from django.conf import settings
            # Determinar el tipo de archivo
            if request.path.startswith('/static/'):
                cache_headers = settings.CDN_CACHE_HEADERS.get('static', {})
            elif request.path.startswith('/media/'):
                # Para imágenes, usar headers específicos
                if any(ext in request.path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    cache_headers = settings.CDN_CACHE_HEADERS.get('images', {})
                else:
                    cache_headers = settings.CDN_CACHE_HEADERS.get('media', {})
            else:
                cache_headers = {}
            # Aplicar headers de cache
            for header, value in cache_headers.items():
                response[header] = value
        return response


class RequestUserMiddleware:
    """
    Middleware para establecer request.user desde la sesión de administraNET
    Reemplaza el sistema de autenticación de Django con sesiones personalizadas
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Establecer request.user desde la sesión antes de que los decoradores lo verifiquen
        request.user = get_usuario_extendiendo_desde_sesion(request)
        
        # Si el usuario ya estaba autenticado, mantener referencia al request
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.user._request = request
            
        return self.get_response(request)


class DeviceDetectionMiddleware(MiddlewareMixin):
    """
    Middleware para detectar si el dispositivo es móvil o desktop
    y agregar esta información al request
    """
    
    def process_request(self, request):
        # Obtener el User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Patrones para detectar dispositivos móviles
        mobile_patterns = [
            r'Android',
            r'iPhone',
            r'iPad',
            r'iPod',
            r'BlackBerry',
            r'Windows Phone',
            r'Mobile',
            r'Opera Mini',
            r'IEMobile',
            r'webOS',
            r'Kindle',
            r'Silk',
            r'PlayBook',
            r'BB10',
            r'RIM Tablet OS'
        ]
        
        # Verificar si es móvil
        is_mobile = any(re.search(pattern, user_agent, re.IGNORECASE) for pattern in mobile_patterns)
        
        # Agregar información al request
        request.is_mobile = is_mobile
        request.is_desktop = not is_mobile
        
        # Detectar tipo específico de dispositivo
        if 'Android' in user_agent:
            request.device_type = 'android'
        elif 'iPhone' in user_agent:
            request.device_type = 'iphone'
        elif 'iPad' in user_agent:
            request.device_type = 'ipad'
        elif 'Windows Phone' in user_agent:
            request.device_type = 'windows_phone'
        else:
            request.device_type = 'desktop' if not is_mobile else 'mobile'
        
        return None
