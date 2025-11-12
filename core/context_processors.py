from core.utils import permisos_contextuales, apps_visibles_para_usuario, obtener_app_por_id, obtener_submenus_por_app
from core.models import UsuarioExtendido

def usuario_y_permisos(request):
    user = getattr(request, "user", None)

    if not user or not getattr(user, "is_authenticated", False):
        return {
            "user": None,
            "permisos_usuario": [],
            "apps_menu": [],
            "empresa_activa": None,
            "branch_activa": None,
            "empresas_disponibles": [],
            "sucursales_disponibles": [],
        }

    permisos_roles = set()
    es_admin = False

    if hasattr(user, "roles"):
        for rol in user.roles.all():
            permisos_roles.update(rol.permisos.values_list("codigo", flat=True))
            if rol.nombre.lower() == "administrador":
                es_admin = True

    permisos_directos = set(user.permisos_extra.values_list("codigo", flat=True))
    permisos_totales = permisos_roles | permisos_directos

    if es_admin:
        permisos_totales = {"*"}
        permisos_contextuales_resultado = {
            "puede_usuarios_ver": True,
            "puede_usuarios_editar": True,
            "puede_usuarios_eliminar": True,
            "puede_usuarios_dashboard": True,
            "puede_crm_ver": True,
            "puede_ventas_ver": True,
            "puede_inventory_ver": True,
            "puede_reportes_ver": True,
            "puede_clientes_todos": True,
            "puede_ventas_todos": True,
            "rol_permitido": True,
            "permisos_usuario": ["*"],
            "permisos_faltantes": [],
        }
    else:
        permisos_contextuales_resultado = permisos_contextuales(
            request,
            "usuarios.ver",
            "usuarios.editar",
            "usuarios.eliminar",
            "usuarios.dashboard",
            "crm.ver",
            "ventas.ver",
            "inventory.ver",
            "reportes.ver",
            "clientes.*",
            "ventas.*",
            roles_permitidos=["Administrador", "Gerente"],
            debug=False
        )

    # Empresa y sucursal activa
    empresa_activa = getattr(user, 'empresa_activa', None)
    branch_activa = getattr(user, 'branch_activa', None)

    # Empresas y sucursales disponibles (por ahora, todas si es admin, si no solo la activa)
    from core.models import Empresa, Branch
    if user.is_admin():
        empresas_disponibles = list(Empresa.objects.filter(activa=True))
        sucursales_disponibles = list(Branch.objects.filter(active=True, empresa=empresa_activa)) if empresa_activa else []
    else:
        empresas_disponibles = [empresa_activa] if empresa_activa else []
        sucursales_disponibles = [branch_activa] if branch_activa else []

    return {
        "user": user,
        "permisos_usuario": sorted(permisos_totales),
        "apps_menu": apps_visibles_para_usuario(user),
        "modulos_menu": apps_visibles_para_usuario(user),
        **permisos_contextuales_resultado,
        "empresa_activa": empresa_activa,
        "branch_activa": branch_activa,
        "empresas_disponibles": empresas_disponibles,
        "sucursales_disponibles": sucursales_disponibles,
    }

def menu_context(request):
    """
    Procesa el contexto para añadir menús dinámicos basados en permisos.
    Usa la nueva estructura centralizada de apps.
    """
    user = getattr(request, "user", None)
    
    # Obtener apps visibles para el usuario
    apps_menu = apps_visibles_para_usuario(user, request)
    
    # Determinar qué sidebar mostrar según la app actual
    current_app_id = None
    if request.resolver_match:
        app_name = request.resolver_match.app_name
        if app_name == 'core':
            current_app_id = 'settings'
        elif app_name == 'inventory':
            current_app_id = 'inventory'
        elif app_name == 'tiendanube':
            current_app_id = 'tiendanube'
        elif app_name == 'purchases':
            current_app_id = 'purchases'
        elif app_name == 'sales':
            current_app_id = 'sales'
        elif app_name == 'accounting':
            current_app_id = 'accounting'
        elif app_name == 'administraNET_integration':
            current_app_id = 'administraNET_integration'
        elif app_name == 'reports':
            current_app_id = 'reports'
    
    # Obtener submenús de la app actual con permisos procesados
    current_sidebar_items = []
    if current_app_id and user and getattr(user, "is_authenticated", False):
        # Obtener permisos del usuario
        if isinstance(user, UsuarioExtendido):
            permisos_usuario = user.get_permisos_totales()
        else:
            permisos_usuario = set()
        
        # Obtener submenús filtrados por permisos
        current_sidebar_items = obtener_submenus_por_app(current_app_id, permisos_usuario, request)

    return {
        "apps_menu": apps_menu,
        "modulos_menu": apps_menu,
        "current_app_id": current_app_id,
        "current_sidebar_items": current_sidebar_items,
        "show_sidebar": bool(current_sidebar_items),
    }

def inventory_menu_context(request):
    """
    Procesa el contexto para el menú lateral del módulo de inventario.
    Mantenido para compatibilidad.
    """
    user = getattr(request, "user", None)
    inventory_sidebar_items = []
    
    if user and getattr(user, "is_authenticated", False):
        if request.resolver_match and request.resolver_match.app_name == 'inventory':
            app = obtener_app_por_id("inventory")
            if app and app.get("submenus"):
                inventory_sidebar_items = app["submenus"]

    return {
        "inventory_sidebar_items": inventory_sidebar_items
    }

def tiendanube_menu_context(request):
    """
    Procesa el contexto para el menú lateral del módulo de TiendaNube.
    Mantenido para compatibilidad.
    """
    user = getattr(request, "user", None)
    tiendanube_sidebar_items = []
    
    if user and getattr(user, "is_authenticated", False):
        if request.resolver_match and request.resolver_match.app_name == 'tiendanube':
            app = obtener_app_por_id("tiendanube")
            if app and app.get("submenus"):
                tiendanube_sidebar_items = app["submenus"]

    return {
        "tiendanube_sidebar_items": tiendanube_sidebar_items
    }

def purchases_menu_context(request):
    """
    Procesa el contexto para el menú lateral del módulo de Purchases.
    Mantenido para compatibilidad.
    """
    user = getattr(request, "user", None)
    purchases_sidebar_items = []
    
    if user and getattr(user, "is_authenticated", False):
        if request.resolver_match and request.resolver_match.app_name == 'purchases':
            app = obtener_app_por_id("purchases")
            if app and app.get("submenus"):
                purchases_sidebar_items = app["submenus"]

    return {
        "purchases_sidebar_items": purchases_sidebar_items
    }

def administraNET_integration_menu_context(request):
    """
    Procesa el contexto para el menú lateral del módulo de administraNET_integration.
    Mantenido para compatibilidad.
    """
    user = getattr(request, "user", None)
    administraNET_integration_sidebar_items = []
    
    if user and getattr(user, "is_authenticated", False):
        if request.resolver_match and request.resolver_match.app_name == 'administraNET_integration':
            app = obtener_app_por_id("administraNET_integration")
            if app and app.get("submenus"):
                administraNET_integration_sidebar_items = app["submenus"]

    return {
        "administraNET_integration_sidebar_items": administraNET_integration_sidebar_items
    }
