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
    
    return apps_visibles_para_usuario(user)

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
    elif app_name in ['sales', 'purchases', 'inventory', 'accounting', 'tiendanube']:
        return app_name
    
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
        'sales': 'sales.ver',
        'purchases': 'purchases.ver',
        'inventory': 'inventory.ver',
        'accounting': 'accounting.ver',
        'tiendanube': 'tiendanube.access',
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

@register.inclusion_tag('core/partials/breadcrumb.html')
def render_breadcrumb(request):
    """
    Renderiza el breadcrumb dinámico
    """
    breadcrumbs = []
    
    if request and request.resolver_match:
        # Agregar página principal
        breadcrumbs.append({
            'label': 'Dashboard',
            'url': '/core/dashboard/',
            'active': False
        })
        
        # Agregar módulo actual
        app_name = request.resolver_match.app_name
        if app_name == 'core':
            breadcrumbs.append({
                'label': 'System',
                'url': '/core/modules/',
                'active': True
            })
        elif app_name in ['sales', 'purchases', 'inventory', 'accounting', 'tiendanube']:
            module_names = {
                'sales': 'Sales',
                'purchases': 'Purchases', 
                'inventory': 'Inventory',
                'accounting': 'Accounting',
                'tiendanube': 'TiendaNube'
            }
            breadcrumbs.append({
                'label': module_names.get(app_name, app_name.title()),
                'url': f'/{app_name}/',
                'active': True
            })
    
    return {
        'breadcrumbs': breadcrumbs
    } 