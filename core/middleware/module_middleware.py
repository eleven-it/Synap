"""
Middleware para verificar acceso a módulos activos
Controla el acceso a URLs de módulos inactivos
"""

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from core.module_manager import module_manager
from core.module_registry import MODULE_CONFIGS


class ModuleMiddleware:
    """Middleware para verificar acceso a módulos activos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verificar si la URL pertenece a un módulo inactivo
        path = request.path_info.lstrip('/')
        
        # Lista de URLs que siempre están permitidas
        allowed_paths = [
            'admin/',
            'login/',
            'logout/',
            'static/',
            'media/',
            'api/',
            'core/dashboard/',
            'core/modules/',
        ]
        
        # Verificar si la ruta está en la lista de permitidas
        if any(path.startswith(allowed_path) for allowed_path in allowed_paths):
            response = self.get_response(request)
            return response
        
        # Permitir rutas de API dentro de módulos (ej: finance/api/, sales/api/, etc.)
        if '/api/' in path:
            response = self.get_response(request)
            return response
        
        # Verificar módulos inactivos
        for module_name in MODULE_CONFIGS.keys():
            if path.startswith(f'{module_name}/') and not module_manager.is_module_active(module_name):
                # Módulo inactivo - redirigir con mensaje
                messages.error(
                    request, 
                    _('The module "{module}" is not active. Please contact your administrator.').format(
                        module=MODULE_CONFIGS[module_name]['display_name']
                    )
                )
                return redirect('core:dashboard')
        
        response = self.get_response(request)
        return response


class ModulePermissionMiddleware:
    """Middleware para verificar permisos de módulos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        path = request.path_info.lstrip('/')
        
        # Permitir acceso a login y logout sin verificar permisos
        if path.startswith('login/') or path.startswith('logout/'):
            response = self.get_response(request)
            return response
        
        # Verificar sesión directamente además de request.user.is_authenticated
        has_session = "user" in request.session
        is_authenticated = hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False)
        
        if not has_session and not is_authenticated:
            response = self.get_response(request)
            return response
        
        # Permitir acceso al dashboard sin verificar permisos de módulo
        if path.startswith('core/dashboard/'):
            response = self.get_response(request)
            return response
        
        # Verificar permisos por módulo
        for module_name in MODULE_CONFIGS.keys():
            if path.startswith(f'{module_name}/'):
                # Verificar si el usuario tiene acceso al módulo
                has_access = self.user_has_module_access(request.user, module_name)
                
                # Logging para diagnóstico
                import logging
                logger = logging.getLogger(__name__)
                if hasattr(request.user, 'get_permisos_totales'):
                    permisos = request.user.get_permisos_totales()
                    logger.debug(f"Usuario {getattr(request.user, 'cod_usuario', 'unknown')} intentando acceder a {module_name}. Permisos: {permisos}. Acceso: {has_access}")
                
                if not has_access:
                    messages.error(
                        request,
                        _('You do not have permission to access the "{module}" module.').format(
                            module=MODULE_CONFIGS[module_name]['display_name']
                        )
                    )
                    return redirect('core:dashboard')
                break
        
        response = self.get_response(request)
        return response
    
    def user_has_module_access(self, user, module_name):
        """Verifica si el usuario tiene acceso al módulo"""
        # Solo el usuario 'supervisor' (por cod_usuario) tiene acceso total
        # NOTA: El puesto/rol "Supervisor" NO otorga acceso total, solo permisos específicos
        if user.is_superuser or user.is_admin():
            return True
        
        # Verificar permisos específicos del módulo
        config = MODULE_CONFIGS.get(module_name, {})
        permissions = config.get('permissions', [])
        
        if not permissions:
            # Si no hay permisos definidos, permitir acceso
            return True
        
        # Obtener todos los permisos del usuario
        user_permissions = set()
        if hasattr(user, 'get_permisos_totales'):
            user_permissions = user.get_permisos_totales()
        elif hasattr(user, 'tiene_permiso') and callable(user.tiene_permiso):
            # Si no tiene get_permisos_totales pero tiene tiene_permiso, verificar directamente
            for permission in permissions:
                if user.tiene_permiso(permission):
                    return True
            # Verificar comodín del módulo
            module_wildcard = f"{module_name}.*"
            if user.tiene_permiso(module_wildcard):
                return True
            return False
        
        # Verificar si el usuario tiene acceso total
        if "*" in user_permissions:
            return True
        
        # Verificar si el usuario tiene permiso con comodín para el módulo (ej: "reports.*")
        module_wildcard = f"{module_name}.*"
        if module_wildcard in user_permissions:
            return True
        
        # Verificar si el usuario tiene al menos un permiso del módulo
        for permission in permissions:
            if permission in user_permissions:
                return True
            # También verificar usando tiene_permiso si está disponible
            if hasattr(user, 'tiene_permiso') and callable(user.tiene_permiso):
                if user.tiene_permiso(permission):
                    return True
        
        return False


class ModuleContextMiddleware:
    """Middleware para agregar contexto de módulos a las respuestas"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Agregar información de módulos activos al contexto
        if hasattr(request, 'resolver_match') and request.resolver_match:
            current_module = self.get_current_module(request.path_info)
            if current_module:
                # Solo agregar si context_data existe y no es None
                if hasattr(response, 'context_data') and response.context_data is not None:
                    response.context_data['current_module'] = current_module
                    response.context_data['module_config'] = MODULE_CONFIGS.get(current_module, {})
        
        return response
    
    def get_current_module(self, path):
        """Obtiene el módulo actual basado en la URL"""
        path = path.lstrip('/')
        
        for module_name in MODULE_CONFIGS.keys():
            if path.startswith(f'{module_name}/'):
                return module_name
        
        return None


class ModuleCacheMiddleware:
    """Middleware para cachear información de módulos"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verificar cache de módulos activos
        from django.core.cache import cache
        
        cache_key = 'active_modules'
        active_modules = cache.get(cache_key)
        
        if active_modules is None:
            # Cache expirado, recargar
            active_modules = module_manager.get_active_modules()
            cache.set(cache_key, active_modules, 300)  # Cache por 5 minutos
        
        # Agregar a request para uso posterior
        request.active_modules = active_modules
        
        response = self.get_response(request)
        return response 