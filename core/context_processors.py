from core.utils import permisos_contextuales, apps_visibles_para_usuario, obtener_app_por_id, obtener_submenus_por_app
from core.utils.permissions import get_user_permission_set, user_has_full_access
from core.models import UsuarioExtendido
import logging

logger = logging.getLogger(__name__)

def usuario_y_permisos(request):
    user = getattr(request, "user", None)

    if not user or not getattr(user, "is_authenticated", False):
        # Si no hay usuario autenticado, intentar obtener logo de empresa Django activa para el login
        logo_default = None
        try:
            from core.models import Empresa
            empresa_django = Empresa.objects.filter(activa=True).order_by('-fecha_modificacion').first()
            if empresa_django and empresa_django.logo:
                # Crear wrapper para el logo
                class LogoWrapper:
                    def __init__(self, file_field):
                        self.file_field = file_field
                    def url(self):
                        import time
                        return f"{self.file_field.url}?v={int(time.time())}"
                logo_default = LogoWrapper(empresa_django.logo)
        except Exception as e:
            logger.debug(f"No se pudo obtener logo por defecto: {e}")
        
        # Crear empresa mock con logo si existe
        empresa_activa_default = None
        if logo_default:
            class EmpresaMockDefault:
                def __init__(self, logo):
                    self.nombre = "Synap"
                    self.logo = logo
            empresa_activa_default = EmpresaMockDefault(logo_default)
        
        return {
            "user": None,
            "permisos_usuario": [],
            "apps_menu": [],
            "empresa_activa": empresa_activa_default,
            "branch_activa": None,
            "empresas_disponibles": [],
            "sucursales_disponibles": [],
        }

    permisos_totales = set()
    es_admin = user_has_full_access(user)

    # Para usuarios de administraNET (AdministraNETUser), usar get_permisos_totales()
    if hasattr(user, 'get_permisos_totales'):
        permisos_totales = get_user_permission_set(user)
    # Para usuarios de Synap (UsuarioExtendido), usar el sistema antiguo
    elif isinstance(user, UsuarioExtendido):
        permisos_roles = set()
        if hasattr(user, "roles"):
            for rol in user.roles.all():
                permisos_roles.update(rol.permisos.values_list("codigo", flat=True))
        permisos_directos = set(user.permisos_extra.values_list("codigo", flat=True))
        permisos_totales = permisos_roles | permisos_directos
        if es_admin:
            permisos_totales = {"*"}

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

    # Empresa y sucursal activa desde administraNET
    empresa_activa = None
    branch_activa = None
    empresas_disponibles = []
    sucursales_disponibles = []
    
    # Obtener datos desde la sesión de administraNET
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_empresa = session_user.get("id_empresa")
    id_sucursal = session_user.get("id_sucursal")
    
    if base_empresa:
        try:
            from core.services.administranet_empresas import AdministraNETEmpresaService
            from core.services.administranet_sucursales import AdministraNETSucursalesService
            
            # Obtener empresa activa
            empresa_service = AdministraNETEmpresaService()
            empresa_data = empresa_service.obtener_empresa(base_empresa)
            if empresa_data:
                # Intentar obtener el logo del modelo Django Empresa si existe
                logo_django = None
                try:
                    from core.models import Empresa
                    # Buscar empresa Django por nombre o identificador fiscal
                    nombre_empresa = empresa_data.get('Nombre', '')
                    cuit_empresa = empresa_data.get('CUIT', '').replace('-', '').replace(' ', '')  # Limpiar formato CUIT
                    
                    empresa_django = None
                    
                    # Primero intentar por CUIT (más confiable)
                    if cuit_empresa:
                        try:
                            # Buscar con CUIT limpio
                            empresa_django = Empresa.objects.filter(identificador_fiscal__icontains=cuit_empresa, activa=True).first()
                            if not empresa_django:
                                # Intentar con formato con guiones
                                cuit_formateado = f"{cuit_empresa[:2]}-{cuit_empresa[2:10]}-{cuit_empresa[10:]}" if len(cuit_empresa) == 11 else cuit_empresa
                                empresa_django = Empresa.objects.filter(identificador_fiscal__icontains=cuit_formateado, activa=True).first()
                        except Exception as e:
                            logger.warning(f"Error al buscar por CUIT: {e}")
                    
                    # Si no se encontró por CUIT, intentar por nombre
                    if not empresa_django and nombre_empresa:
                        try:
                            empresa_django = Empresa.objects.filter(nombre__iexact=nombre_empresa, activa=True).first()
                            if not empresa_django:
                                # Intentar búsqueda parcial
                                empresa_django = Empresa.objects.filter(nombre__icontains=nombre_empresa, activa=True).first()
                        except Exception as e:
                            logger.warning(f"Error al buscar por nombre: {e}")
                    
                    # Si se encontró, usar su logo
                    if empresa_django and empresa_django.logo:
                        logo_django = empresa_django.logo
                        logger.info(f"✅ Logo encontrado para empresa Django: {empresa_django.nombre} - {logo_django.url if logo_django else 'None'}")
                    else:
                        logger.debug(f"ℹ️ No se encontró logo para empresa Django (nombre: {nombre_empresa}, CUIT: {cuit_empresa})")
                except Exception as e:
                    logger.warning(f"No se pudo obtener logo de Django Empresa: {e}")
                
                # Crear objeto mock para compatibilidad
                class EmpresaMock:
                    def __init__(self, data, logo=None):
                        self.nombre = data.get('Nombre', '')
                        self.id_empresa = data.get('id_empresa', id_empresa)
                        # Si hay logo, crear un objeto que tenga el método .url
                        if logo:
                            # Crear un objeto wrapper que tenga el método .url
                            class LogoWrapper:
                                def __init__(self, file_field):
                                    self.file_field = file_field
                                def url(self):
                                    # Agregar timestamp para evitar caché
                                    import time
                                    return f"{self.file_field.url}?v={int(time.time())}"
                            self.logo = LogoWrapper(logo)
                        else:
                            self.logo = None
                        self.activa = True
                empresa_activa = EmpresaMock(empresa_data, logo_django)
                empresas_disponibles = [empresa_activa]
            
            # Obtener sucursal activa
            if id_sucursal and id_sucursal > 0:
                sucursales_service = AdministraNETSucursalesService()
                sucursal_data = sucursales_service.obtener_sucursal(base_empresa, id_sucursal)
                if sucursal_data:
                    # Crear objeto mock para compatibilidad
                    class SucursalMock:
                        def __init__(self, data):
                            self.name = data.get('nombre_sucursal', '')
                            self.id = data.get('id_sucursal')
                            self.active = data.get('activa', True)
                            self.city = data.get('domicilio_sucursal', '')
                    branch_activa = SucursalMock(sucursal_data)
                    sucursales_disponibles = [branch_activa]
            
            # Obtener todas las sucursales disponibles para el dropdown
            if empresa_activa:
                sucursales_service = AdministraNETSucursalesService()
                todas_sucursales = sucursales_service.listar_sucursales(base_empresa)
                # Crear lista de sucursales mock
                sucursales_list = []
                for s in todas_sucursales:
                    if s.get('activa'):
                        class SucursalMock:
                            def __init__(self, data):
                                self.id = data.get('id_sucursal')
                                self.name = data.get('nombre_sucursal', '')
                                self.active = data.get('activa', True)
                                self.city = data.get('domicilio_sucursal', '')
                        sucursales_list.append(SucursalMock(s))
                sucursales_disponibles = sucursales_list
                
                # Si no hay sucursal activa pero hay sucursales disponibles, usar la primera
                if not branch_activa and sucursales_disponibles:
                    branch_activa = sucursales_disponibles[0]
        except Exception as e:
            logger.error(f"Error al obtener empresa/sucursal desde administraNET: {e}")

    # Nombre del login (tabla empresas) para identificar la DB en el pie; no exponer base_empresa.
    # Siempre re-resolver si falta en sesión (sesiones anteriores al cambio).
    nombre_empresa_login = (session_user.get("nombre_empresa") or "").strip()
    if base_empresa and not nombre_empresa_login:
        try:
            from login.administranet_auth import AdministraNETAuth
            nombre_empresa_login = (AdministraNETAuth().nombre_empresa_por_base(base_empresa) or "").strip()
            if nombre_empresa_login:
                session_user["nombre_empresa"] = nombre_empresa_login
                request.session["user"] = session_user
                request.session.modified = True
        except Exception as e:
            logger.warning("No se pudo resolver nombre_empresa de login: %s", e)
    if base_empresa and not nombre_empresa_login:
        logger.warning(
            "Pie sin nombre_empresa para base_empresa=%s (tabla empresas sin match)",
            base_empresa,
        )

    # Fecha/hora servidor para barra de estado (Principal, paridad VB6 Control_Fecha)
    from django.utils import timezone
    now = timezone.now()
    fecha_servidor = {
        "fecha": now.strftime("%Y-%m-%d"),
        "hora": now.strftime("%H:%M:%S"),
        "iso": now.isoformat(),
    }

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
        "session_user": session_user,
        "nombre_empresa_login": nombre_empresa_login,
        "fecha_servidor": fecha_servidor,
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
        # Módulos deshabilitados para administraNET Analytics
        # elif app_name == 'inventory':
        #     current_app_id = 'inventory'
        # elif app_name == 'tiendanube':
        #     current_app_id = 'tiendanube'
        # elif app_name == 'purchases':
        #     current_app_id = 'purchases'
        elif app_name == 'reports':
            current_app_id = 'reports'
        elif app_name == 'ventas':
            current_app_id = 'ventas'
        elif app_name == 'self_checkout':
            current_app_id = 'self_checkout'
        elif app_name == 'ecom':
            current_app_id = 'ecom'
    
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

    # Móvil/PWA: no mostrar sidebar de módulos no incluidos en Nivel A
    from core.pwa_nivel_a import sidebar_visible_en_pwa, tpv_visible_en_movil

    tpv_visible_movil = False
    if request and getattr(request, "is_mobile", False):
        tpv_visible_movil = tpv_visible_en_movil(user, request)
        if not sidebar_visible_en_pwa(current_app_id, request, user):
            current_sidebar_items = []
        elif current_app_id == "ecom":
            from core.pwa_nivel_a import filtrar_submenus_ecom_para_pwa_movil

            current_sidebar_items = filtrar_submenus_ecom_para_pwa_movil(current_sidebar_items)

    return {
        "apps_menu": apps_menu,
        "modulos_menu": apps_menu,
        "current_app_id": current_app_id,
        "current_sidebar_items": current_sidebar_items,
        "show_sidebar": bool(current_sidebar_items),
        "tpv_visible_movil": tpv_visible_movil,
    }

# Funciones de contexto de menú deshabilitadas para administraNET Analytics
# def inventory_menu_context(request):
#     """Módulo inventory deshabilitado"""
#     return {"inventory_sidebar_items": []}

# def tiendanube_menu_context(request):
#     """Módulo tiendanube deshabilitado"""
#     return {"tiendanube_sidebar_items": []}

# def purchases_menu_context(request):
#     """Módulo purchases deshabilitado"""
#     return {"purchases_sidebar_items": []}

def administraNET_integration_menu_context(request):
    """Módulo administraNET_integration eliminado; se mantiene por compatibilidad con templates."""
    return {"administraNET_integration_sidebar_items": []}
