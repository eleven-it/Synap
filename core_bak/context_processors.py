from core.utils import permisos_contextuales, modulos_visibles_para_usuario, ADMIN_SIDEBAR_MENU, INVENTORY_SIDEBAR_MENU

def usuario_y_permisos(request):
    user = getattr(request, "user", None)

    if not user or not getattr(user, "is_authenticated", False):
        return {
            "user": None,
            "permisos_usuario": [],
            "modulos_menu": [],
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

    return {
        "user": user,
        "permisos_usuario": sorted(permisos_totales),
        "modulos_menu": modulos_visibles_para_usuario(user),  
        **permisos_contextuales_resultado
    }

def menu_context(request):
    """
    Procesa el contexto para añadir menús dinámicos basados en permisos.
    """
    user = getattr(request, "user", None)
    
    # Menú principal de módulos (el que ya existía)
    modulos_menu = modulos_visibles_para_usuario(user)

    # Menú lateral de administración (el nuevo)
    admin_sidebar_items = []
    show_admin_sidebar = False
    
    if user and getattr(user, "is_authenticated", False):
        if request.resolver_match and request.resolver_match.app_name == 'core':
            show_admin_sidebar = True
            
            for section, items in ADMIN_SIDEBAR_MENU.items():
                visible_items = []
                for item in items:
                    if user.tiene_permiso(item['permission']):
                        visible_items.append(item)
                
                if visible_items:
                    admin_sidebar_items.append({
                        "section": section,
                        "items": visible_items
                    })

    return {
        "modulos_menu": modulos_menu,
        "admin_sidebar_items": admin_sidebar_items,
        "show_admin_sidebar": show_admin_sidebar,
    }

def inventory_menu_context(request):
    """
    Procesa el contexto para el menú lateral del módulo de inventario.
    """
    user = getattr(request, "user", None)
    inventory_sidebar_items = []
    
    if user and getattr(user, "is_authenticated", False):
        if request.resolver_match and request.resolver_match.app_name == 'inventory':
            for section, items in INVENTORY_SIDEBAR_MENU.items():
                visible_items = []
                for item in items:
                    if user.tiene_permiso(item['permission']):
                        visible_items.append(item)
                
                if visible_items:
                    inventory_sidebar_items.append({
                        "section": section,
                        "items": visible_items
                    })

    return {
        "inventory_sidebar_items": inventory_sidebar_items
    }
