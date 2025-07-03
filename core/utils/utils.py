from core.models import UsuarioExtendido, Rol
from django_project.firebase_config import get_firebase_app
import fnmatch
import logging
from django.core.cache import cache
from django.conf import settings
from typing import Dict, List, Set, Optional, Any
import json
from django.utils.translation import gettext_lazy as _
import firebase_admin
from firebase_admin import firestore
from django.http import HttpResponseForbidden
from functools import wraps

logger = logging.getLogger(__name__)

# core/utils.py

MODULOS_MENU = [
    {
        "nombre": _("Dashboard"),
        "permiso": "usuarios.dashboard",
        "url": "core:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
            <path stroke-linecap='round' stroke-linejoin='round' d='M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z'/>
            <path stroke-linecap='round' stroke-linejoin='round' d='M8 5a2 2 0 012-2h4a2 2 0 012 2v6H8V5z'/>
        </svg>""",
        "orden": 1
    },
    # {
    #     "nombre": "CRM",
    #     "permiso": "crm.ver",
    #     "url": "/crm/",
    #     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
    #         <path stroke-linecap='round' stroke-linejoin='round' d='M9.75 3.75h4.5m-9 3h13.5m-13.5 3h13.5M4.5 9.75v10.5a.75.75 0 00.75.75h13.5a.75.75 0 00.75-.75V9.75'/>
    #     </svg>""",
    #     "orden": 2
    # },
    # {
    #     "nombre": "Ventas",
    #     "permiso": "ventas.ver",
    #     "url": "/ventas/",
    #     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
    #         <path stroke-linecap='round' stroke-linejoin='round' d='M3 3h6v6H3V3zm0 12h6v6H3v-6zm12-12h6v6h-6V3zm0 12h6v6h-6v-6z'/>
    #     </svg>""",
    #     "orden": 3
    # },
    {
        "nombre": _("Inventory"),
        "permiso": "inventory.ver",
        "url": "/inventory/dashboard/",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
            <path stroke-linecap='round' stroke-linejoin='round' d='M4 6h16M4 12h16M4 18h16'/>
        </svg>""",
        "orden": 4
    },
    # {
    #     "nombre": "Compras",
    #     "permiso": "compras.ver",
    #     "url": "/compras/",
    #     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
    #         <path stroke-linecap='round' stroke-linejoin='round' d='M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z'/>
    #     </svg>""",
    #     "orden": 5
    # },
    # {
    #     "nombre": "Finance",
    #     "permiso": "finance.ver",
    #     "url": "/finance/",
    #     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
    #         <path stroke-linecap='round' stroke-linejoin='round' d='M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1'/>
    #     </svg>""",
    #     "orden": 6
    # },
    # {
    #     "nombre": "Reportes",
    #     "permiso": "reportes.ver",
    #     "url": "/reportes/",
    #     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
    #         <path stroke-linecap='round' stroke-linejoin='round' d='M3 10h18M3 6h18M3 14h18M3 18h18'/>
    #     </svg>""",
    #     "orden": 7
    # },
    # {
    #     "nombre": "IA",
    #     "permiso": "ia.reportes",
    #     "url": "/ia/",
    #     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
    #         <path stroke-linecap='round' stroke-linejoin='round' d='M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423L16.5 15.75l.394 1.183a2.25 2.25 0 001.423 1.423L19.5 18.75l-1.183.394a2.25 2.25 0 00-1.423 1.423z'/>
    #     </svg>""",
    #     "orden": 8
    # },
    {
        "nombre": _("Settings"),
        "permiso": "usuarios.dashboard",
        "url": "/core/dashboard/",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
            <path stroke-linecap='round' stroke-linejoin='round' d='M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' />
            <path stroke-linecap='round' stroke-linejoin='round' d='M15 12a3 3 0 11-6 0 3 3 0 016 0z' />
        </svg>""",
        "orden": 9
    },
    {
        "nombre": _("TiendaNube"),
        "permiso": "tiendanube.access",
        "url": "/tiendanube/",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M17.5 19a4.5 4.5 0 100-9 5.5 5.5 0 00-10.9 1.5A4.5 4.5 0 006.5 19h11z'/></svg>""",
        "orden": 10
    }
]

ADMIN_SIDEBAR_MENU = {
    _( "Quick Access" ): [
        {
            "label": _( "Dashboard" ),
            "url_name": "core:dashboard",
            "icon": "dashboard",
            "permission": "usuarios.dashboard"
        }
    ],
    _( "Access Management" ): [
        {
            "label": _( "Users" ),
            "url_name": "core:usuarios",
            "icon": "group",
            "permission": "usuarios.ver"
        },
        {
            "label": _( "Roles" ),
            "url_name": "core:listar_roles",
            "icon": "admin_panel_settings",
            "permission": "usuarios.roles.ver"
        },
        {
            "label": _( "Permissions" ),
            "url_name": "core:listar_permisos",
            "icon": "vpn_key",
            "permission": "usuarios.permisos.ver"
        }
    ],
    _( "General Configuration" ): [
        {
            "label": _( "Units of Measure" ),
            "url_name": "core:uom_list",
            "icon": "straighten",
            "permission": "configuracion.uom"
        }
    ],
    _( "Financial Configuration" ): [
        {
            "label": _( "Currencies" ),
            "url_name": "core:currency_list",
            "icon": "payments",
            "permission": "configuracion.moneda"
        },
        {
            "label": _( "Exchange Rates" ),
            "url_name": "core:exchange_rate_list",
            "icon": "currency_exchange",
            "permission": "configuracion.moneda"
        }
    ],
    _( "System Configuration" ): [
        {
            "label": _( "Configuration" ),
            "url_name": "core:system_config_list",
            "icon": "settings",
            "permission": "configuracion.sistema"
        },
        {
            "label": _( "Empresas" ),
            "url_name": "core:empresa_listar",
            "icon": "business",
            "permission": "configuracion.sistema"
        },
        {
            "label": _( "CDN Wizard" ),
            "url_name": "core:cdn_wizard",
            "icon": "cloud",
            "permission": "configuracion.sistema"
        }
    ]
}

INVENTORY_SIDEBAR_MENU = {
    _( "Main" ): [
        {
            "label": _( "Dashboard" ),
            "url_name": "inventory:stock_dashboard",
            "icon": "dashboard",
            "permission": "inventory.ver"
        },
        {
            "label": _( "Products" ),
            "url_name": "inventory:product_list",
            "icon": "inventory",
            "permission": "inventory.ver_product"
        }
    ],
    _( "Stock Management" ): [
        {
            "label": _( "Warehouses" ),
            "url_name": "inventory:warehouse_list",
            "icon": "warehouse",
            "permission": "inventory.ver_warehouse"
        },
        {
            "label": _( "Locations" ),
            "url_name": "inventory:location_list",
            "icon": "location_on",
            "permission": "inventory.ver_location"
        }
    ]
}

# Antes de usar firestore, asegúrate de inicializar Firebase:
get_firebase_app()

def sincronizar_usuario_desde_firestore(decoded_token: Dict[str, Any]) -> UsuarioExtendido:
    """
    Sincroniza un usuario autenticado por Firebase con el modelo UsuarioExtendido.
    Ya no usa tipo_usuario de Firebase. Solo actualiza nombre, idioma y email.
    """
    uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    nombre = decoded_token.get("name", "")

    if not uid or not email:
        raise ValueError("UID y email son requeridos para sincronizar usuario")

    try:
        firestore_db = firestore.client()
        doc_ref = firestore_db.collection("usuarios").document(uid)
        doc = doc_ref.get()

        idioma = "es"
        if doc.exists:
            data = doc.to_dict()
            idioma = data.get("idioma", "es")

        usuario, creado = UsuarioExtendido.objects.get_or_create(
            uid=uid, 
            defaults={
                "email": email,
                "nombre": nombre,
                "idioma": idioma,
            }
        )

        # Actualizar campos si han cambiado
        actualizado = False
        if usuario.email != email:
            usuario.email = email
            actualizado = True
        if usuario.nombre != nombre:
            usuario.nombre = nombre
            actualizado = True
        if usuario.idioma != idioma:
            usuario.idioma = idioma
            actualizado = True

        if actualizado:
            usuario.save()
            # Invalidar cache
            cache.delete(f"user_uid_{uid}")
            cache.delete(f"user_session_{uid}")

        return usuario

    except Exception as e:
        logger.error(f"Error sincronizando usuario {uid}: {e}")
        raise


def permisos_contextuales(
    request, 
    *codigos: str, 
    roles_permitidos: Optional[List[str]] = None, 
    debug: bool = False
) -> Dict[str, Any]:
    """
    Devuelve un diccionario con permisos para usar en el contexto de templates y vistas.
    Versión optimizada con cache.
    """
    permisos = {}
    user = getattr(request, "user", None)

    if not user or not getattr(user, "is_authenticated", False):
        return {
            "permisos_usuario": [],
            "rol_permitido": False,
            **{f"puede_{cod.replace('.', '_').replace('*', 'todos')}": False for cod in codigos}
        }

    # Usar método optimizado del modelo
    if isinstance(user, UsuarioExtendido):
        permisos_usuario = user.get_permisos_totales()
    else:
        permisos_usuario = set()

    # Evaluar permisos solicitados
    faltantes = []
    for cod in codigos:
        key = f"puede_{cod.replace('.', '_').replace('*', 'todos')}"
        if "*" in permisos_usuario or cod in permisos_usuario:
            permisos[key] = True
        else:
            permisos[key] = False
            faltantes.append(cod)

    # Roles permitidos (si aplica)
    if roles_permitidos and isinstance(user, UsuarioExtendido):
        user_roles = [r.nombre.lower() for r in user.roles.filter(activo=True)]
        permisos["rol_permitido"] = any(r.lower() in user_roles for r in roles_permitidos)
    elif roles_permitidos:
        permisos["rol_permitido"] = False

    if debug and faltantes:
        permisos["permisos_faltantes"] = faltantes

    # ✅ Agregar lista de permisos para el template (debug/info)
    permisos["permisos_usuario"] = sorted(permisos_usuario)

    return permisos


def modulos_visibles_para_usuario(user: Optional[UsuarioExtendido]) -> List[Dict[str, Any]]:
    """Obtiene módulos visibles para un usuario, ordenados por prioridad"""
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return []

    permisos_usuario = set()
    if isinstance(user, UsuarioExtendido):
        permisos_usuario = user.get_permisos_totales()

    modulos_filtrados = [
        m for m in MODULOS_MENU
        if "*" in permisos_usuario or m["permiso"] in permisos_usuario
    ]
    
    # Ordenar por el campo 'orden'
    return sorted(modulos_filtrados, key=lambda x: x.get('orden', 999))


def crear_roles_predeterminados() -> Dict[str, Rol]:
    """Crea roles predeterminados si no existen"""
    from core.constantes_permisos import ROLES_PREDEFINIDOS
    
    roles_creados = {}
    
    for nombre_rol, config in ROLES_PREDEFINIDOS.items():
        rol, creado = Rol.objects.get_or_create(
            nombre__iexact=nombre_rol,
            defaults={
                "nombre": nombre_rol,
                "descripcion": config["descripcion"],
                "activo": True
            }
        )
        
        if creado:
            logger.info(f"Rol creado: {nombre_rol}")
        
        # Asignar permisos si se especifican
        if config["permisos"] != ["*"]:
            from core.models import Permiso
            permisos_objs = []
            for perm_codigo in config["permisos"]:
                if perm_codigo.endswith(".*"):
                    # Permisos de módulo completo
                    modulo = perm_codigo[:-2]
                    permisos_modulo = Permiso.objects.filter(
                        codigo__startswith=f"{modulo}.",
                        activo=True
                    )
                    permisos_objs.extend(permisos_modulo)
                else:
                    # Permiso específico
                    try:
                        permiso = Permiso.objects.get(codigo=perm_codigo, activo=True)
                        permisos_objs.append(permiso)
                    except Permiso.DoesNotExist:
                        logger.warning(f"Permiso no encontrado: {perm_codigo}")
            
            rol.permisos.set(permisos_objs)
        
        roles_creados[nombre_rol] = rol
    
    return roles_creados


def obtener_estadisticas_sistema() -> Dict[str, Any]:
    """Obtiene estadísticas generales del sistema"""
    try:
        from core.models import UsuarioExtendido, Rol, Permiso
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta
        
        ahora = timezone.now()
        hace_30_dias = ahora - timedelta(days=30)
        
        stats = {
            "usuarios": {
                "total": UsuarioExtendido.objects.count(),
                "activos": UsuarioExtendido.objects.filter(is_active=True).count(),
                "nuevos_30_dias": UsuarioExtendido.objects.filter(
                    fecha_creacion__gte=hace_30_dias
                ).count(),
                "ultimo_acceso_30_dias": UsuarioExtendido.objects.filter(
                    ultimo_acceso__gte=hace_30_dias
                ).count()
            },
            "roles": {
                "total": Rol.objects.count(),
                "activos": Rol.objects.filter(activo=True).count()
            },
            "permisos": {
                "total": Permiso.objects.count(),
                "activos": Permiso.objects.filter(activo=True).count()
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {}


def validar_permiso_critico(usuario: UsuarioExtendido, permiso: str) -> bool:
    """Valida si un usuario puede ejecutar un permiso crítico"""
    from core.constantes_permisos import PERMISOS_CRITICOS
    
    if permiso not in PERMISOS_CRITICOS:
        return True
    
    # Para permisos críticos, verificar si es administrador o tiene confirmación especial
    if usuario.is_admin():
        return True
    
    # Aquí podrías implementar lógica adicional como:
    # - Verificar si el usuario tiene confirmación de 2FA
    # - Verificar si está en horario permitido
    # - Verificar si tiene autorización especial
    
    return False


def registrar_actividad_usuario(
    usuario: UsuarioExtendido, 
    accion: str, 
    detalles: Optional[Dict[str, Any]] = None
) -> None:
    """Registra actividad del usuario para auditoría"""
    try:
        actividad = {
            "timestamp": timezone.now().isoformat(),
            "usuario": usuario.email,
            "uid": usuario.uid,
            "accion": accion,
            "detalles": detalles or {}
        }
        
        logger.info(f"ACTIVIDAD_USUARIO: {json.dumps(actividad)}")
        
        # Aquí podrías guardar en una tabla de auditoría específica
        # o enviar a un sistema de logging externo
        
    except Exception as e:
        logger.error(f"Error registrando actividad: {e}")


def limpiar_cache_usuario(usuario: UsuarioExtendido) -> None:
    """Limpia todo el cache relacionado con un usuario"""
    cache_keys = [
        f"user_uid_{usuario.uid}",
        f"user_session_{usuario.uid}",
        usuario.get_permisos_cache_key()
    ]
    
    for key in cache_keys:
        cache.delete(key)

def require_empresa_activa(get_empresa):
    """
    Decorador para bloquear acceso a vistas si la empresa está inactiva.
    get_empresa: función que recibe (request, *args, **kwargs) y retorna la instancia de Empresa.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            empresa = get_empresa(request, *args, **kwargs)
            if not empresa.activa:
                return HttpResponseForbidden('Access denied: company is inactive.')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator