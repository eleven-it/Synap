"""
Template tags para renderizar menús dinámicos del sistema
"""

from django import template
from django.urls import reverse, NoReverseMatch
from core.utils import apps_visibles_para_usuario, obtener_submenus_por_app
from core.models import UsuarioExtendido

register = template.Library()

@register.simple_tag(takes_context=True)
def get_dynamic_menu(context):
    """
    Obtiene el menú dinámico basado en los módulos activos y permisos del usuario
    """
    request = context.get('request')
    user = getattr(request, 'user', None) if request else None
    
    if not user or not getattr(user, 'is_authenticated', False):
        return []
    
    return apps_visibles_para_usuario(user, request)

@register.simple_tag(takes_context=True)
def get_current_module(context):
    """
    Determina el módulo actual basado en la URL
    """
    request = context.get('request')
    if not request or not request.resolver_match:
        return None
    
    app_name = request.resolver_match.app_name
    if app_name == 'core':
        return 'settings'
    elif app_name == 'factura_compra_captura_web':
        return 'compras'
    elif app_name == 'compras':
        return 'compras'
    elif app_name == 'stock':
        return app_name
    elif app_name == 'ia':
        return 'ia'
    elif app_name == 'mpr':
        return 'mpr'

    return None

@register.simple_tag(takes_context=True)
def is_module_active(context, module_id):
    """
    Verifica si un módulo está activo en la URL actual
    """
    current_module = get_current_module(context)
    return current_module == module_id

@register.simple_tag(takes_context=True)
def get_module_sidebar(context, module_id):
    """
    Obtiene los elementos del sidebar para un módulo específico
    """
    request = context.get('request')
    user = getattr(request, 'user', None) if request else None
    
    if not user or not getattr(user, 'is_authenticated', False):
        return []
    
    if isinstance(user, UsuarioExtendido):
        permisos_usuario = user.get_permisos_totales()
    else:
        permisos_usuario = set()
    
    return obtener_submenus_por_app(module_id, permisos_usuario)

@register.filter
def has_module_permission(user, module_id):
    """
    Verifica si el usuario tiene permisos para acceder a un módulo
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    
    if isinstance(user, UsuarioExtendido):
        permisos_usuario = user.get_permisos_totales()
    else:
        permisos_usuario = set()
    
    # Mapeo de módulos a permisos
    module_permissions = {
        'stock': 'stock.ver',
        'ia': 'ia.ver',
        'settings': 'core.admin_access',
    }
    
    required_permission = module_permissions.get(module_id)
    if not required_permission:
        return False
    
    return "*" in permisos_usuario or required_permission in permisos_usuario

@register.simple_tag
def get_module_stats():
    """
    Obtiene estadísticas de los módulos (para mostrar en el menú)
    """
    from core.models import ModuleConfig
    
    stats = {}
    modules = ModuleConfig.objects.all()
    
    for module in modules:
        stats[module.name] = {
            'active': module.is_active,
            'version': module.version,
            'dependencies': module.dependencies.count() if hasattr(module, 'dependencies') else 0,
        }
    
    return stats

@register.inclusion_tag('core/partials/module_menu_item.html')
def render_module_menu_item(module, is_active=False):
    """
    Renderiza un elemento del menú de módulos
    """
    return {
        'module': module,
        'is_active': is_active,
    }

@register.inclusion_tag('core/partials/module_dropdown.html')
def render_module_dropdown(module):
    """
    Renderiza el dropdown de un módulo
    """
    return {
        'module': module,
    }

@register.inclusion_tag('core/partials/user_menu.html')
def render_user_menu():
    """
    Renderiza el menú de usuario para el sidebar de administración
    """
    return {}

@register.simple_tag
def get_administranet_logo():
    """
    Obtiene la ruta del logo más reciente de administraNET
    Busca archivos que contengan 'Logo_Signo_administraNET' en el nombre
    """
    import os
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    logos_dir = os.path.join(settings.MEDIA_ROOT, 'empresas', 'logos')
    if not os.path.exists(logos_dir):
        logger.debug(f"get_administranet_logo: Directorio no existe: {logos_dir}")
        return None
    
    # Buscar todos los archivos que contengan 'Logo_Signo_administraNET'
    logo_files = []
    try:
        for filename in os.listdir(logos_dir):
            if 'Logo_Signo_administraNET' in filename and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.svg')):
                filepath = os.path.join(logos_dir, filename)
                if os.path.isfile(filepath):
                    # Obtener fecha de modificación
                    mtime = os.path.getmtime(filepath)
                    logo_files.append((mtime, filename))
                    logger.debug(f"get_administranet_logo: Encontrado {filename} (mtime: {mtime})")
    except Exception as e:
        logger.error(f"get_administranet_logo: Error al listar directorio: {e}")
        return None
    
    if not logo_files:
        logger.debug("get_administranet_logo: No se encontraron archivos de logo")
        return None
    
    # Ordenar por fecha de modificación (más reciente primero)
    logo_files.sort(reverse=True)
    most_recent_logo = logo_files[0][1]
    result = f"empresas/logos/{most_recent_logo}"
    logger.debug(f"get_administranet_logo: Retornando {result}")
    
    return result 