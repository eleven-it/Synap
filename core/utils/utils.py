from core.models import UsuarioExtendido, Rol
# Firebase deshabilitado para instalación mínima de Reportes
# from django_project.firebase_config import get_firebase_app
import fnmatch
import logging
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from typing import Dict, List, Set, Optional, Any
import json
from django.utils.translation import gettext_lazy as _
# Firebase deshabilitado para instalación mínima de Reportes
# import firebase_admin
# from firebase_admin import firestore
from django.http import HttpResponseForbidden
from functools import wraps
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from core.utils.permissions import get_user_permission_set, user_has_full_access

logger = logging.getLogger(__name__)

# core/utils.py

# ─────────────────────────────────────────────
# CONFIGURACIÓN CENTRAL DE MENÚS Y APPS
# ─────────────────────────────────────────────

# Configuración principal de apps/modulos
# Archivo (paridad menú VB6 Principal.frm) — ítems migrados; visibilidad igual que Settings
APPS_MENU = [
    {
        "id": "archivo",
        "nombre": _("Archivo"),
        "permiso": "usuarios.dashboard",
        "url": "core:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M5 19a2 2 0 01-2 2H3a2 2 0 01-2-2V5a2 2 0 012-2h2a2 2 0 012 2v2m0 0h10a2 2 0 012 2v8a2 2 0 01-2 2H9a2 2 0 01-2-2v-6' /></svg>""",
        "orden": 0,
        "color": "slate",
        "submenus": [
            {
                "seccion": _("Parámetros"),
                "items": [
                    {"label": _("Datos empresa"), "url": "core:empresa_listar", "icon": "business", "permission": "configuracion.sistema", "menu_item_id": "archivo_param_empresa"},
                    {"label": _("Sucursales"), "url": "core:branch_list", "icon": "location_on", "permission": "configuracion.sistema", "url_kwargs": {"empresa_id": 1}, "menu_item_id": "archivo_param_sucursales"},
                    {"label": _("Administrador de usuario"), "url": "core:usuarios", "icon": "group", "permission": "usuarios.ver", "menu_item_id": "archivo_param_usuarios"},
                    {"label": _("Puesto"), "url": "core:listar_roles", "icon": "badge", "permission": "usuarios.roles.ver", "menu_item_id": "archivo_param_puesto"},
                    {"label": _("Permiso en menú"), "url": "core:listar_permisos", "icon": "menu_book", "permission": "usuarios.permisos.ver", "menu_item_id": "archivo_param_permiso_menu"},
                    {"label": _("Permiso en sistema"), "url": "core:permisos_sistema", "icon": "admin_panel_settings", "permission": "usuarios.permisos.ver", "menu_item_id": "archivo_param_permiso_sistema"},
                    {"label": _("Asignar permisos por puesto"), "url": "core:permisos_puesto_lista", "icon": "security", "permission": "usuarios.permisos.ver", "menu_item_id": "archivo_param_permisos_puesto"},
                    {"label": _("Referencia de movimiento de stock"), "url": "stock:ref_movstock_list", "icon": "bookmark", "permission": "stock.ref_movstock", "menu_item_id": "archivo_param_ref_movstock"},
                    {"label": _("Migración esquema MySQL (legacy)"), "url": "core:legacy_mysql_schema", "icon": "storage", "permission": "configuracion.sistema", "menu_item_id": "archivo_param_mysql_schema"},
                ]
            },
        ]
    },
    {
        "id": "stock",
        "nombre": _("Stock"),
        "permiso": "stock.ver",
        "url": "stock:alta_movimiento",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4'/></svg>""",
        "orden": 3,
        "color": "blue",
        "submenus": [
            {
                "seccion": _("Movimientos"),
                "items": [
                    {"label": _("Ingreso Mov. Stock"), "url": "stock:alta_movimiento", "icon": "add_circle", "permission": "stock.crear_movimiento", "menu_item_id": "stock_mov_ingreso"},
                    {"label": _("Remito de Compra"), "url": "compras:remito_compra_form", "icon": "receipt", "permission": "stock.crear_movimiento", "menu_item_id": "stock_mov_remito_compra"},
                    {"label": _("Remito de Venta"), "url": "stock:alta_movimiento", "icon": "receipt_long", "permission": "stock.crear_movimiento", "menu_item_id": "stock_mov_remito_venta"},
                    {"label": _("Pedido interno a depósito / compras"), "url": "stock:alta_movimiento", "icon": "swap_horiz", "permission": "stock.crear_movimiento", "menu_item_id": "stock_mov_pedido_interno"},
                    {"label": _("Inventario"), "url": "stock:inventario", "icon": "inventory_2", "permission": "stock.consultas", "menu_item_id": "stock_mov_inventario"},
                ]
            },
            {
                "seccion": _("Consultas"),
                "items": [
                    {"label": _("Inventario por etapa"), "url": "stock:inventario", "icon": "description", "permission": "stock.consultas", "menu_item_id": "stock_cons_ficha"},
                    {"label": _("Consultas y Anulaciones"), "url": "stock:visualiza_movimientos", "icon": "list_alt", "permission": "stock.consultas", "menu_item_id": "stock_cons_anulaciones"},
                    {"label": _("Informes"), "url": "stock:visualiza_movimientos", "icon": "assessment", "permission": "stock.informes", "menu_item_id": "stock_cons_informes"},
                ]
            },
            {
                "seccion": _("Comprobantes de compra"),
                "items": [
                    {"label": _("Expedientes captura"), "url": "factura_compra_captura_web:lista-expedientes", "icon": "folder_open", "permission": "compras.ver", "menu_item_id": "stock_cc_expedientes_captura"},
                    {"label": _("Captura móvil"), "url": "factura_compra_captura_web:captura-movil", "icon": "add_a_photo", "permission": "compras.ver", "menu_item_id": "stock_cc_captura_movil"},
                    {"label": _("Facturación"), "url": "compras:factura_compra", "icon": "receipt", "permission": "stock.ver", "menu_item_id": "stock_cc_facturacion"},
                    {"label": _("Listado de proveedores"), "url": "compras:hub_comprobantes", "icon": "list", "permission": "stock.ver", "menu_item_id": "stock_cc_proveedores"},
                ]
            }
        ]
    },
    {
        "id": "ventas",
        "nombre": _("Ventas"),
        "permiso": "ventas.ver",
        "url": "ventas:objetivos_periodos_list",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z'/><path stroke-linecap='round' stroke-linejoin='round' d='M9 14h6'/></svg>""",
        "orden": 3.5,
        "color": "cyan",
        "submenus": [
            {
                "seccion": _("Comprobantes"),
                "items": [
                    {
                        "label": _("Presupuestos"),
                        "url": "ventas:presupuesto_list",
                        "icon": "description",
                        "permission": "ventas.presupuesto.ver",
                        "menu_item_id": "ventas_cb_presupuestos",
                    },
                    {
                        "label": _("Pedidos"),
                        "url": "ecom:mayoristapp_pedidos_hub",
                        "icon": "receipt_long",
                        "permission": "ecom.pedidos.ver",
                        "menu_item_id": "ventas_cb_pedidos",
                    },
                    {
                        "label": _("Pedido masivo sucursales"),
                        "url": "ecom:mayoristapp_pedido_masivo_sucursales",
                        "icon": "grid_on",
                        "permission": "ecom.pedido_masivo.usar",
                        "menu_item_id": "ventas_cb_pedido_masivo",
                    },
                    {
                        "label": _("Vendedor · Cliente · Marca"),
                        "url": "ecom:mayoristapp_config_vendedor_cliente_marca",
                        "icon": "hub",
                        "permission": "ecom.config_vendedor_cliente_marca",
                        "menu_item_id": "ventas_cb_vendedor_cliente_marca",
                    },
                    {
                        "label": _("Actualización de precios"),
                        "url": "ventas:precios_terminados",
                        "icon": "price_change",
                        "permission": "ventas.precios_terminados.editar",
                        "menu_item_id": "ventas_cb_precios_terminados",
                    },
                    {
                        "label": _("Evolución de precios"),
                        "url": "ventas:evolucion_precios",
                        "icon": "timeline",
                        "permission": "ventas.precios_historial.ver",
                        "menu_item_id": "ventas_cb_evolucion_precios",
                    },
                ]
            },
            {
                "seccion": _("Ajustes"),
                "items": [
                    {
                        "label": _("Ajustes de ventas"),
                        "url": "ecom:mayoristapp_ajustes_ventas",
                        "icon": "settings",
                        "permission": "ecom.config_ajustes_ventas",
                        "menu_item_id": "ventas_ajustes_ventas",
                    },
                ]
            },
            {
                "seccion": _("Gestión"),
                "items": [
                    {
                        "label": _("Asignación vendedor"),
                        "url": "ventas:vendedor_asignacion",
                        "icon": "swap_horiz",
                        "permission": "ventas.ver",
                        "menu_item_id": "ventas_gest_asignacion_vendedor",
                    },
                ]
            },
            {
                "seccion": _("Objetivos"),
                "items": [
                    {
                        "label": _("Objetivos de venta"),
                        "url": "ventas:objetivos_periodos_list",
                        "icon": "flag",
                        "permission": "ventas.ver",
                        "menu_item_id": "ventas_obj_objetivos_venta",
                    },
                ]
            },
        ]
    },
    {
        "id": "compras",
        "nombre": _("Compras"),
        "permiso": "compras.ver",
        "url": "compras:factura_compra",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z'/></svg>""",
        "orden": 4,
        "color": "emerald",
        "submenus": [
            {
                "seccion": _("Comprobantes"),
                "items": [
                    {"label": _("Expedientes captura"), "url": "factura_compra_captura_web:lista-expedientes", "icon": "folder_open", "permission": "compras.ver", "menu_item_id": "compras_cb_lista_expedientes"},
                    {"label": _("Captura y expedientes"), "url": "factura_compra_captura_web:captura-movil", "icon": "add_a_photo", "permission": "compras.ver", "menu_item_id": "compras_cb_captura_expedientes"},
                    {"label": _("Facturación"), "url": "compras:factura_compra", "icon": "receipt", "permission": "compras.ver", "menu_item_id": "compras_cb_facturacion"},
                    {"label": _("Listado de proveedores"), "url": "compras:hub_comprobantes", "icon": "list", "permission": "compras.ver", "menu_item_id": "compras_cb_listado"},
                    {"label": _("Remito de Compra"), "url": "compras:remito_compra_form", "icon": "receipt", "permission": "compras.crear", "menu_item_id": "compras_cb_remito"},
                ]
            }
        ]
    },
    {
        "id": "mpr",
        "nombre": _("Producción (MPR)"),
        "permiso": "mpr.ver",
        "url": "mpr:tablero_produccion",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z'/></svg>""",
        "orden": 5,
        "color": "purple",
        "submenus": [
            {
                "seccion": _("Producción diaria"),
                "items": [
                    {"label": _("Tablero de producción"), "url": "mpr:tablero_produccion", "icon": "table_chart", "permission": "mpr.ver", "menu_item_id": "mpr_prod_tablero"},
                    {"label": _("Parte de producción"), "url": "mpr:parte_produccion", "icon": "assignment", "permission": "mpr.ver", "menu_item_id": "mpr_prod_parte"},
                    {"label": _("Partes pendientes (aprobación)"), "url": "mpr:partes_pendientes", "icon": "fact_check", "permission": "mpr.aprobar_parte", "menu_item_id": "mpr_prod_partes_pendientes"},
                    {"label": _("Control de calidad"), "url": "mpr:clasificacion_produccion", "icon": "verified", "permission": "mpr.ver", "menu_item_id": "mpr_prod_clasificacion"},
                    {"label": _("Planificación de turnos"), "url": "mpr:planificacion_turnos", "icon": "calendar_month", "permission": "mpr.ver", "menu_item_id": "mpr_prod_planificacion"},
                    {"label": _("Tablero de control (KPIs)"), "url": "mpr:tablero", "icon": "dashboard", "permission": "mpr.ver", "menu_item_id": "mpr_prod_kpis"},
                ]
            },
            {
                "seccion": _("Armado y stock"),
                "items": [
                    {"label": _("Armado"), "url": "mpr:armado", "icon": "build", "permission": "mpr.ver", "menu_item_id": "mpr_op_armado"},
                    {"label": _("Imputación de pedido"), "url": "mpr:imputacion_armado_1ra", "icon": "assignment_turned_in", "permission": "mpr.imputar_armado_1ra", "menu_item_id": "mpr_op_imputacion_armado_1ra"},
                    {"label": _("Reclasificación"), "url": "mpr:reclasificacion", "icon": "swap_horiz", "permission": "mpr.ver", "menu_item_id": "mpr_op_reclasificacion"},
                ]
            },
            {
                "seccion": _("Reportes"),
                "items": [
                    {"label": _("Reportes MPR"), "url": "mpr:reportes", "icon": "assessment", "permission": "mpr.ver", "menu_item_id": "mpr_rep_reportes"},
                ]
            },
            {
                "seccion": _("Configuración"),
                "items": [
                    {"label": _("Turnos de producción"), "url": "mpr:turnos_list", "icon": "schedule", "permission": "mpr.ver", "menu_item_id": "mpr_cfg_turnos"},
                    {"label": _("Config. Depósitos"), "url": "mpr:config_depositos", "icon": "warehouse", "permission": "mpr.ver", "menu_item_id": "mpr_cfg_depositos"},
                    {"label": _("Operarios"), "url": "mpr:operarios_list", "icon": "engineering", "permission": "mpr.ver", "menu_item_id": "mpr_cfg_operarios"},
                    {"label": _("Líneas"), "url": "mpr:lineas_list", "icon": "view_stream", "permission": "mpr.maquinas_lineas", "menu_item_id": "mpr_cfg_lineas"},
                    {"label": _("Máquinas"), "url": "mpr:maquinas_list", "icon": "precision_manufacturing", "permission": "mpr.maquinas_lineas", "menu_item_id": "mpr_cfg_maquinas"},
                    {"label": _("Operarios y usuarios"), "url": "mpr:operario_usuario_map", "icon": "badge", "permission": "mpr.maquinas_lineas", "menu_item_id": "mpr_cfg_operario_usuario"},
                    {"label": _("Línea habitual (operarios)"), "url": "mpr:operario_linea", "icon": "conveyor_belt", "permission": "mpr.maquinas_lineas", "menu_item_id": "mpr_cfg_operario_linea"},
                    {"label": _("Migración BEST"), "url": "mpr:migracion_best_hub", "icon": "sync_alt", "permission": "mpr.ver", "menu_item_id": "mpr_cfg_migracion_best"},
                ]
            },
        ]
    },
    {
        "id": "logistica",
        "nombre": _("Logística"),
        "permiso": "logistica_editar_entregas",
        "url": "logistica:entregas",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M9 17a2 2 0 11-4 0 2 2 0 014 0zm10 0a2 2 0 11-4 0 2 2 0 014 0z'/><path stroke-linecap='round' stroke-linejoin='round' d='M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0'/></svg>""",
        "orden": 5,
        "color": "amber",
        "submenus": [
            {
                "seccion": _("Operación"),
                "items": [
                    {
                        "label": _("Entregas"),
                        "url": "logistica:entregas",
                        "icon": "local_shipping",
                        "permission": "logistica_editar_entregas",
                        "menu_item_id": "logistica_op_entregas",
                    },
                ]
            },
        ]
    },
    {
        "id": "settings",
        "nombre": _("Settings"),
        "permiso": "usuarios.dashboard",
        "url": "core:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' /><path stroke-linecap='round' stroke-linejoin='round' d='M15 12a3 3 0 11-6 0 3 3 0 016 0z' /></svg>""",
        "orden": 5,
        "color": "gray",
        "submenus": [
            {
                "seccion": _("Quick Access"),
                "items": [
                    {
                        "label": _("Dashboard"),
                        "url": "core:dashboard",
                        "icon": "dashboard",
                        "permission": "usuarios.dashboard",
                        "menu_item_id": "settings_qa_dashboard",
                    }
                ]
            },
            {
                "seccion": _("Access Management"),
                "items": [
                    {
                        "label": _("Users"),
                        "url": "core:usuarios",
                        "icon": "group",
                        "permission": "usuarios.ver",
                        "menu_item_id": "settings_am_users",
                    },
                    {
                        "label": _("Roles"),
                        "url": "core:listar_roles",
                        "icon": "admin_panel_settings",
                        "permission": "usuarios.roles.ver",
                        "menu_item_id": "settings_am_roles",
                    },
                    {
                        "label": _("Permissions"),
                        "url": "core:listar_permisos",
                        "icon": "vpn_key",
                        "permission": "usuarios.permisos.ver",
                        "menu_item_id": "settings_am_permissions",
                    },
                    {
                        "label": _("Universal Contacts"),
                        "items": [
                            {
                                "label": _("All Contacts"),
                                "url": "core:contact_list",
                                "icon": "contacts",
                                "permission": "core.ver_contact",
                                "menu_item_id": "settings_uc_contacts_all",
                            },
                            {
                                "label": _("Create Contact"),
                                "url": "core:contact_create",
                                "icon": "person_add",
                                "permission": "core.crear_contact",
                                "menu_item_id": "settings_uc_contacts_create",
                            },
                            {
                                "label": _("Contact Relationships"),
                                "url": "core:contact_relationship_list",
                                "icon": "link",
                                "permission": "core.ver_contact",
                                "menu_item_id": "settings_uc_relationships",
                            }
                        ]
                    }
                ]
            },
            {
                "seccion": _("General Configuration"),
                "items": [
                    {
                        "label": _("Units of Measure"),
                        "url": "core:uom_list",
                        "icon": "straighten",
                        "permission": "configuracion.uom",
                        "menu_item_id": "settings_gc_uom",
                    },
                    {
                        "label": _("Empresas"),
                        "url": "core:empresa_listar",
                        "icon": "business",
                        "permission": "configuracion.sistema",
                        "menu_item_id": "settings_gc_empresas",
                    }
                ]
            },
            {
                "seccion": _("Financial Configuration"),
                "items": [
                    {
                        "label": _("Currencies"),
                        "url": "core:currency_list",
                        "icon": "payments",
                        "permission": "configuracion.moneda",
                        "menu_item_id": "settings_fc_currencies",
                    },
                    {
                        "label": _("Exchange Rates"),
                        "url": "core:exchange_rate_list",
                        "icon": "currency_exchange",
                        "permission": "configuracion.moneda",
                        "menu_item_id": "settings_fc_exchange",
                    }
                ]
            },
            {
                "seccion": _("System Configuration"),
                "items": [
                    {
                        "label": _("Configuration"),
                        "url": "core:system_config_list",
                        "icon": "settings",
                        "permission": "configuracion.sistema",
                        "menu_item_id": "settings_sc_config",
                    },
                    {
                        "label": _("CDN Wizard"),
                        "url": "core:cdn_wizard",
                        "icon": "cloud",
                        "permission": "configuracion.sistema",
                        "menu_item_id": "settings_sc_cdn",
                    },
                    {
                        "label": _("Hooks & Events"),
                        "url": "core:hook_dashboard",
                        "icon": "event",
                        "permission": "configuracion.sistema",
                        "menu_item_id": "settings_sc_hooks",
                    }
                ]
            }
        ]
    },
    {
        "id": "self_checkout",
        "nombre": _("Self-Checkout / TPV"),
        "permiso": "self_checkout.ver",
        "url": "self_checkout:index",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z'/></svg>""",
        "orden": 7,
        "color": "purple",
        "submenus": [
            {
                "seccion": _("Autoservicio / TPV"),
                "items": [
                    {"label": _("Selector de kiosco"), "url": "self_checkout:index", "icon": "storefront", "permission": "self_checkout.ver", "menu_item_id": "sc_tpv_selector"},
                    {"label": _("Configuración autoservicios"), "url": "self_checkout:config_list", "icon": "settings", "permission": "self_checkout.admin", "menu_item_id": "sc_tpv_config"},
                    {"label": _("Carritos pendientes"), "url": "self_checkout:carritos_pendientes", "icon": "shopping_cart", "permission": "self_checkout.ver", "menu_item_id": "sc_tpv_carritos"},
                    {"label": _("Talonarios"), "url": "self_checkout:talonarios_list", "icon": "receipt", "permission": "self_checkout.admin", "menu_item_id": "sc_tpv_talonarios"},
                    {
                        "label": _("Facturación AFIP"),
                        "url": "fe_afip:config_list",
                        "icon": "verified_user",
                        "permission": "fe_afip.view_afipconfig",
                        "menu_item_id": "sc_tpv_fe_afip",
                    },
                ]
            }
        ]
    },
    {
        "id": "odoo_migracion",
        "nombre": _("Migración Odoo"),
        "permiso": "odoo_migracion.ver",
        "url": "odoo_migracion:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7c-2 0-3 1-3 3z'/><path stroke-linecap='round' stroke-linejoin='round' d='M8 12h8M12 8v8'/></svg>""",
        "orden": 95,
        "color": "indigo",
        "superuser_only": True,
        "submenus": [
            {
                "seccion": _("Migración"),
                "items": [
                    {"label": _("Panel"), "url": "odoo_migracion:dashboard", "icon": "dashboard", "permission": "odoo_migracion.ver", "menu_item_id": "odoo_mig_panel"},
                    {"label": _("Inventario"), "url": "odoo_migracion:discovery", "icon": "inventory", "permission": "odoo_migracion.ver", "menu_item_id": "odoo_mig_inventario"},
                    {"label": _("Wizard migración"), "url": "odoo_migracion:wizard", "icon": "play_arrow", "permission": "odoo_migracion.jobs", "menu_item_id": "odoo_mig_wizard"},
                    {"label": _("Conexiones Odoo"), "url": "odoo_migracion:conexion_list", "icon": "link", "permission": "odoo_migracion.conexiones", "menu_item_id": "odoo_mig_conexiones"},
                    {"label": _("Jobs"), "url": "odoo_migracion:job_list", "icon": "sync", "permission": "odoo_migracion.jobs", "menu_item_id": "odoo_mig_jobs"},
                    {"label": _("Validación / cuadre"), "url": "odoo_migracion:validacion", "icon": "fact_check", "permission": "odoo_migracion.ver", "menu_item_id": "odoo_mig_validacion"},
                    {"label": _("Mapeos"), "url": "odoo_migracion:mapping_list", "icon": "compare_arrows", "permission": "odoo_migracion.ver", "menu_item_id": "odoo_mig_mapeos"},
                ]
            }
        ]
    },
    {
        "id": "module_management",
        "nombre": _("Module Management"),
        "permiso": "core.change_moduleconfig",
        "url": "core:module_list",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1'/></svg>""",
        "orden": 100,
        "color": "indigo",
        "superuser_only": True,
        "submenus": []
    },
    {
        "id": "reports",
        "nombre": _("Reports"),
        "permiso": "reports.ver",
        "url": "reports:catalog",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M4 4h6l2 3h8v13H4z'/></svg>""",
        "orden": 6,
        "color": "teal",
        "submenus": [
            {
                "seccion": _("Catálogo"),
                "items": [
                    {
                        "label": _("Catálogo"),
                        "url": "reports:catalog",
                        "icon": "dashboard",
                        "permission": "reports.ver",
                        "menu_item_id": "reports_cat_catalogo",
                    },
                    {
                        "label": _("Workspace"),
                        "url": "reports:workspace",
                        "icon": "dashboard_customize",
                        "permission": "reports.ver",
                        "menu_item_id": "reports_cat_workspace",
                    }
                ]
            }
        ]
    },
    {
        "id": "ia",
        "nombre": _("IA"),
        "permiso": "ia.ver",
        "url": "ia:home",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423L16.5 15.75l.394 1.183a2.25 2.25 0 001.423 1.423L19.5 18.75l-1.183.394a2.25 2.25 0 00-1.423 1.423z'/></svg>""",
        "orden": 6.5,
        "color": "fuchsia",
        "submenus": [
            {
                "seccion": _("Asistentes"),
                "items": [
                    {
                        "label": _("Inicio IA"),
                        "url": "ia:home",
                        "icon": "smart_toy",
                        "permission": "ia.ver",
                        "menu_item_id": "ia_home",
                    },
                    {
                        "label": _("Asistente de Reportes"),
                        "url": "ia:chat",
                        "url_kwargs": {"slug": "asistente-reportes"},
                        "icon": "analytics",
                        "permission": "ia.reportes",
                        "menu_item_id": "ia_reportes_chat",
                    },
                    {
                        "label": _("Configuración IA"),
                        "url": "ia:configuration",
                        "icon": "tune",
                        "permission": "ia.admin",
                        "menu_item_id": "ia_configuration",
                    },
                ]
            }
        ]
    },
    {
        "id": "ecom",
        "nombre": _("E-commerce"),
        "permiso": "ecom.ver",
        "url": "ecom:mayoristapp_hub",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z'/></svg>""",
        "orden": 6.2,
        "color": "sky",
        "submenus": [
            {
                "seccion": _("Portal"),
                "items": [
                    {
                        "label": _("Portal mayorista"),
                        "url": "ecom:mayoristapp_hub",
                        "icon": "storefront",
                        "permission": "ecom.ver",
                        "menu_item_id": "ecom_hub",
                    },
                    {
                        "label": _("Pedido de venta"),
                        "url": "ecom:mayoristapp_venta",
                        "icon": "shopping_cart",
                        "permission": "ecom.carrito.editar",
                        "menu_item_id": "ecom_compra",
                    },
                ],
            },
            {
                "seccion": _("Comprobantes"),
                "items": [
                    {
                        "label": _("Presupuestos"),
                        "url": "ecom:mayoristapp_presupuestos_vendedor",
                        "icon": "description",
                        "permission": "ecom.comprobantes.ver",
                        "menu_item_id": "ecom_presupuestos",
                    },
                    {
                        "label": _("Pedidos"),
                        "url": "ecom:mayoristapp_pedidos_vendedor",
                        "icon": "receipt_long",
                        "permission": "ecom.comprobantes.ver",
                        "menu_item_id": "ecom_pedidos",
                    },
                    {
                        "label": _("Remitos"),
                        "url": "ecom:mayoristapp_listado_remitos",
                        "icon": "local_shipping",
                        "permission": "ecom.comprobantes.ver",
                        "menu_item_id": "ecom_remitos",
                    },
                    {
                        "label": _("Recibos web"),
                        "url": "ecom:mayoristapp_listado_recibos",
                        "icon": "payments",
                        "permission": "ecom.cobranzas.ver",
                        "menu_item_id": "ecom_recibos",
                    },
                    {
                        "label": _("Alta recibo"),
                        "url": "ecom:mayoristapp_alta_recibo",
                        "icon": "add_card",
                        "permission": "ecom.cobranzas.editar",
                        "menu_item_id": "ecom_alta_recibo",
                    },
                ],
            },
            {
                "seccion": _("Clientes y catálogo"),
                "items": [
                    {
                        "label": _("Clientes"),
                        "url": "ecom:mayoristapp_clientes",
                        "icon": "groups",
                        "permission": "ecom.clientes.ver",
                        "menu_item_id": "ecom_clientes",
                    },
                    {
                        "label": _("Promociones"),
                        "url": "ecom:mayoristapp_listado_promociones",
                        "icon": "sell",
                        "permission": "ecom.catalogo.ver",
                        "menu_item_id": "ecom_promociones",
                    },
                ],
            },
            {
                "seccion": _("Logística"),
                "items": [
                    {
                        "label": _("Preparación de pedidos"),
                        "url": "ecom:mayoristapp_estado_pedidos_preparacion",
                        "icon": "inventory",
                        "permission": "ecom.logistica.ver",
                        "menu_item_id": "ecom_estado_pedidos",
                    },
                    {
                        "label": _("Entregas en ruta"),
                        "url": "logistica:entregas",
                        "icon": "local_shipping",
                        "permission": "ecom.logistica.ver",
                        "menu_item_id": "ecom_logistica_entregas",
                    },
                ],
            },
        ],
    },
    {
        "id": "mercadopago",
        "nombre": _("MercadoPago"),
        "permiso": "mercadopago.view_mercadopagoconfig",
        "url": "mercadopago:config_list",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1'/></svg>""",
        "orden": 96,
        "color": "blue",
        "submenus": [
            {
                "seccion": _("Configuration"),
                "items": [
                    {
                        "label": _("Settings"),
                        "url": "mercadopago:config_list",
                        "icon": "settings",
                        "permission": "mercadopago.view_mercadopagoconfig",
                        "menu_item_id": "mp_cfg_settings",
                    },
                    {
                        "label": _("Add Configuration"),
                        "url": "mercadopago:config_create",
                        "icon": "add_circle",
                        "permission": "mercadopago.add_mercadopagoconfig",
                        "menu_item_id": "mp_cfg_add",
                    }
                ]
            },
            {
                "seccion": _("Device Management"),
                "items": [
                    {
                        "label": _("SmartPOS Devices"),
                        "url": "mercadopago:device_list",
                        "icon": "point_of_sale",
                        "permission": "mercadopago.view_mercadopagodevice",
                        "menu_item_id": "mp_dev_list",
                    },
                    {
                        "label": _("Add Device"),
                        "url": "mercadopago:device_create",
                        "icon": "add_circle",
                        "permission": "mercadopago.add_mercadopagodevice",
                        "menu_item_id": "mp_dev_add",
                    },
                    {
                        "label": _("Device Status"),
                        "url": "mercadopago:device_status",
                        "icon": "monitor_heart",
                        "permission": "mercadopago.view_mercadopagodevice",
                        "menu_item_id": "mp_dev_status",
                    }
                ]
            },
            {
                "seccion": _("Transactions"),
                "items": [
                    {
                        "label": _("Transaction History"),
                        "url": "mercadopago:transaction_list",
                        "icon": "receipt_long",
                        "permission": "mercadopago.view_mercadopagotransaction",
                        "menu_item_id": "mp_tx_history",
                    },
                    {
                        "label": _("Failed Transactions"),
                        "url": "mercadopago:transaction_failed",
                        "icon": "error_outline",
                        "permission": "mercadopago.view_mercadopagotransaction",
                        "menu_item_id": "mp_tx_failed",
                    },
                    {
                        "label": _("Transaction Reports"),
                        "url": "mercadopago:transaction_reports",
                        "icon": "analytics",
                        "permission": "mercadopago.view_reports",
                        "menu_item_id": "mp_tx_reports",
                    }
                ]
            },
            {
                "seccion": _("Reports & Analytics"),
                "items": [
                    {
                        "label": _("Sales by Device"),
                        "url": "mercadopago:device_sales_report",
                        "icon": "bar_chart",
                        "permission": "mercadopago.view_reports",
                        "menu_item_id": "mp_ra_sales_device",
                    },
                    {
                        "label": _("Payment Methods"),
                        "url": "mercadopago:payment_methods_report",
                        "icon": "credit_card",
                        "permission": "mercadopago.view_reports",
                        "menu_item_id": "mp_ra_payment_methods",
                    },
                    {
                        "label": _("Device Performance"),
                        "url": "mercadopago:device_performance_report",
                        "icon": "speed",
                        "permission": "mercadopago.view_reports",
                        "menu_item_id": "mp_ra_device_perf",
                    },
                    {
                        "label": _("Export Data"),
                        "url": "mercadopago:export_data",
                        "icon": "download",
                        "permission": "mercadopago.export_data",
                        "menu_item_id": "mp_ra_export",
                    }
                ]
            }
        ]
    },
    {
        "id": "clover",
        "nombre": _("Clover"),
        "permiso": "clover.view_cloverdevice",
        "url": "clover:device_list",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z'/></svg>""",
        "orden": 97,
        "color": "green",
        "submenus": [
            {
                "seccion": _("Device Management"),
                "items": [
                    {
                        "label": _("Devices"),
                        "url": "clover:device_list",
                        "icon": "point_of_sale",
                        "permission": "clover.view_cloverdevice",
                        "menu_item_id": "clover_dev_list",
                    },
                    {
                        "label": _("Add Device"),
                        "url": "clover:device_create",
                        "icon": "add_circle",
                        "permission": "clover.add_cloverdevice",
                        "menu_item_id": "clover_dev_add",
                    },
                    {
                        "label": _("Device Status"),
                        "url": "clover:device_status",
                        "icon": "monitor_heart",
                        "permission": "clover.view_cloverdevice",
                        "menu_item_id": "clover_dev_status",
                    }
                ]
            },
            {
                "seccion": _("Transactions"),
                "items": [
                    {
                        "label": _("Transaction History"),
                        "url": "clover:transaction_list",
                        "icon": "receipt_long",
                        "permission": "clover.view_clovertransaction",
                        "menu_item_id": "clover_tx_history",
                    },
                    {
                        "label": _("Failed Transactions"),
                        "url": "clover:transaction_failed",
                        "icon": "error_outline",
                        "permission": "clover.view_clovertransaction",
                        "menu_item_id": "clover_tx_failed",
                    },
                    {
                        "label": _("Transaction Reports"),
                        "url": "clover:transaction_reports",
                        "icon": "analytics",
                        "permission": "clover.view_reports",
                        "menu_item_id": "clover_tx_reports",
                    }
                ]
            },
            {
                "seccion": _("Configuration"),
                "items": [
                    {
                        "label": _("Settings"),
                        "url": "clover:config_list",
                        "icon": "settings",
                        "permission": "clover.view_cloverconfig",
                        "menu_item_id": "clover_cfg_settings",
                    },
                    {
                        "label": _("Webhooks"),
                        "url": "clover:webhook_list",
                        "icon": "webhook",
                        "permission": "clover.view_cloverwebhook",
                        "menu_item_id": "clover_cfg_webhooks",
                    },
                    {
                        "label": _("API Configuration"),
                        "url": "clover:api_config",
                        "icon": "api",
                        "permission": "clover.change_cloverconfig",
                        "menu_item_id": "clover_cfg_api",
                    }
                ]
            },
            {
                "seccion": _("Reports & Analytics"),
                "items": [
                    {
                        "label": _("Sales by Device"),
                        "url": "clover:device_sales_report",
                        "icon": "bar_chart",
                        "permission": "clover.view_reports",
                        "menu_item_id": "clover_ra_sales_device",
                    },
                    {
                        "label": _("Payment Methods"),
                        "url": "clover:payment_methods_report",
                        "icon": "credit_card",
                        "permission": "clover.view_reports",
                        "menu_item_id": "clover_ra_payment_methods",
                    },
                    {
                        "label": _("Device Performance"),
                        "url": "clover:device_performance_report",
                        "icon": "speed",
                        "permission": "clover.view_reports",
                        "menu_item_id": "clover_ra_device_perf",
                    },
                    {
                        "label": _("Export Data"),
                        "url": "clover:export_data",
                        "icon": "download",
                        "permission": "clover.export_data",
                        "menu_item_id": "clover_ra_export",
                    }
                ]
            }
        ]
    },
    {
        "id": "tiendanube_administranet",
        "nombre": _("Tienda Nube — AdministraNET"),
        "permiso": "tiendanube_administranet.view_tiendanubeconfig",
        "url": "tiendanube_administranet:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z'/></svg>""",
        "orden": 98,
        "color": "sky",
        "submenus": [
            {
                "seccion": _("Operación"),
                "items": [
                    {
                        "label": _("Estado del sistema"),
                        "url": "tiendanube_administranet:dashboard",
                        "icon": "insights",
                        "permission": "tiendanube_administranet.view_tiendanubeconfig",
                        "menu_item_id": "tn_anet_op_estado",
                    },
                    {
                        "label": _("Sincronización manual"),
                        "url": "tiendanube_administranet:manual_sync",
                        "icon": "sync",
                        "permission": "tiendanube_administranet.run_sync",
                        "menu_item_id": "tn_anet_op_manual",
                    },
                    {
                        "label": _("Historial de sincronización"),
                        "url": "tiendanube_administranet:sync_history",
                        "icon": "history",
                        "permission": "tiendanube_administranet.view_synclog",
                        "menu_item_id": "tn_anet_op_historial",
                    },
                ],
            },
            {
                "seccion": _("Mapeos"),
                "items": [
                    {
                        "label": _("Clientes"),
                        "url": "tiendanube_administranet:customer_mapping_list",
                        "icon": "people",
                        "permission": "tiendanube_administranet.view_customermapping",
                        "menu_item_id": "tn_anet_map_clientes",
                    },
                    {
                        "label": _("Productos"),
                        "url": "tiendanube_administranet:product_list",
                        "icon": "inventory_2",
                        "permission": "tiendanube_administranet.view_productmapping",
                        "menu_item_id": "tn_anet_map_productos",
                    },
                    {
                        "label": _("Pedidos"),
                        "url": "tiendanube_administranet:order_mapping_list",
                        "icon": "shopping_cart",
                        "permission": "tiendanube_administranet.view_ordermapping",
                        "menu_item_id": "tn_anet_map_pedidos",
                    },
                    {
                        "label": _("Categorías"),
                        "url": "tiendanube_administranet:category_list",
                        "icon": "category",
                        "permission": "tiendanube_administranet.view_productcategorymapping",
                        "menu_item_id": "tn_anet_map_categorias",
                    },
                ],
            },
            {
                "seccion": _("Configuración"),
                "items": [
                    {
                        "label": _("Tiendas Tienda Nube"),
                        "url": "tiendanube_administranet:tiendanube_config_list",
                        "icon": "store",
                        "permission": "tiendanube_administranet.view_tiendanubeconfig",
                        "menu_item_id": "tn_anet_cfg_tiendas",
                    },
                    {
                        "label": _("AdministraNET"),
                        "url": "tiendanube_administranet:adminet_config",
                        "icon": "dns",
                        "permission": "tiendanube_administranet.change_administranetconfig",
                        "menu_item_id": "tn_anet_cfg_adminet",
                    },
                    {
                        "label": _("Webhooks"),
                        "url": "tiendanube_administranet:webhook_config_list",
                        "icon": "webhook",
                        "permission": "tiendanube_administranet.view_webhookconfig",
                        "menu_item_id": "tn_anet_cfg_webhooks",
                    },
                    {
                        "label": _("Eventos de webhook"),
                        "url": "tiendanube_administranet:webhook_event_list",
                        "icon": "notifications_active",
                        "permission": "tiendanube_administranet.view_webhookevent",
                        "menu_item_id": "tn_anet_cfg_webhook_eventos",
                    },
                    {
                        "label": _("Sincronización automática"),
                        "url": "tiendanube_administranet:auto_sync_config",
                        "icon": "schedule",
                        "permission": "tiendanube_administranet.change_tiendanubeconfig",
                        "menu_item_id": "tn_anet_cfg_autosync",
                    },
                ],
            },
        ],
    },
]


def iter_menu_hojas_apps_menu():
    """
    Recorre APPS_MENU y produce una tupla por cada ítem hoja con URL y menu_item_id.
    Usado por la UI de visibilidad granular del navbar y validación de IDs únicos.
    """
    for app in APPS_MENU:
        app_id = app["id"]
        nombre_mod = str(app["nombre"])
        for submenu in app.get("submenus") or []:
            seccion = str(submenu.get("seccion", "") or "")
            for item in submenu.get("items") or []:
                if "url" in item:
                    mid = item.get("menu_item_id")
                    if mid:
                        yield (
                            app_id,
                            nombre_mod,
                            seccion,
                            str(item.get("label", "")),
                            str(item.get("url", "")),
                            mid,
                        )
                elif "items" in item:
                    for child in item.get("items") or []:
                        if "url" not in child:
                            continue
                        mid = child.get("menu_item_id")
                        if mid:
                            yield (
                                app_id,
                                nombre_mod,
                                seccion,
                                str(child.get("label", "")),
                                str(child.get("url", "")),
                                mid,
                            )


# Apps comentadas para futuras implementaciones
# {
#     "id": "crm",
#     "nombre": _("CRM"),
#     "permiso": "crm.ver",
#     "url": "/crm/",
#     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
#         <path stroke-linecap='round' stroke-linejoin='round' d='M9.75 3.75h4.5m-9 3h13.5m-13.5 3h13.5M4.5 9.75v10.5a.75.75 0 00.75.75h13.5a.75.75 0 00.75-.75V9.75'/>
#     </svg>""",
#     "orden": 5,
#     "color": "indigo",
#     "submenus": []
# },
# {
#     "id": "ventas",
#     "nombre": _("Sales"),
#     "permiso": "ventas.ver",
#     "url": "/ventas/",
#     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
#         <path stroke-linecap='round' stroke-linejoin='round' d='M3 3h6v6H3V3zm0 12h6v6H3v-6zm12-12h6v6h-6V3zm0 12h6v6h-6v-6z'/>
#     </svg>""",
#     "orden": 6,
#     "color": "orange",
#     "submenus": []
# },
# {
#     "id": "compras",
#     "nombre": _("Purchases"),
#     "permiso": "compras.ver",
#     "url": "/compras/",
#     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
#         <path stroke-linecap='round' stroke-linejoin='round' d='M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z'/>
#     </svg>""",
#     "orden": 7,
#     "color": "red",
#     "submenus": []
# },
# {
#     "id": "finance",
#     "nombre": _("Finance"),
#     "permiso": "finance.ver",
#     "url": "/finance/",
#     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
#         <path stroke-linecap='round' stroke-linejoin='round' d='M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1'/>
#     </svg>""",
#     "orden": 8,
#     "color": "emerald",
#     "submenus": []
# },
# {
#     "id": "reportes",
#     "nombre": _("Reports"),
#     "permiso": "reportes.ver",
#     "url": "/reportes/",
#     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
#         <path stroke-linecap='round' stroke-linejoin='round' d='M3 10h18M3 6h18M3 14h18M3 18h18'/>
#     </svg>""",
#     "orden": 9,
#     "color": "teal",
#     "submenus": []
# },
# {
#     "id": "ia",
#     "nombre": _("AI"),
#     "permiso": "ia.reportes",
#     "url": "/ia/",
#     "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
#         <path stroke-linecap='round' stroke-linejoin='round' d='M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423L16.5 15.75l.394 1.183a2.25 2.25 0 001.423 1.423L19.5 18.75l-1.183.394a2.25 2.25 0 00-1.423 1.423z'/>
#     </svg>""",
#     "orden": 10,
#     "color": "pink",
#     "submenus": []
# }

# ─────────────────────────────────────────────
# FUNCIONES DE UTILIDAD PARA MENÚS
# ─────────────────────────────────────────────

def obtener_app_por_id(app_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene una app específica por su ID"""
    for app in APPS_MENU:
        if app["id"] == app_id:
            return app
    return None

def _resolver_url_item(item: Dict, request, permisos_usuario: Set[str]) -> Optional[Dict[str, Any]]:
    """Resuelve la URL de un ítem de menú con 'url'. Retorna dict con label, url, icon, permission o None si no aplica."""
    from django.urls import reverse
    from django.urls.exceptions import NoReverseMatch

    if "url" not in item:
        return None
    if "*" not in permisos_usuario and item.get("permission", "") not in permisos_usuario:
        return None
    try:
        url_mapping = {}
        if item["url"] in url_mapping:
            url = url_mapping[item["url"]]
        else:
            url_kwargs = item.get("url_kwargs") or {}
            url = reverse(item["url"], kwargs=url_kwargs)
            url_query = item.get("url_query") or {}
            if url_query:
                from urllib.parse import urlencode
                url = f"{url}?{urlencode(url_query)}"
        if request and "{empresa_id}" in url:
            empresa_activa = None
            if hasattr(request.user, "empresa_activa") and request.user.empresa_activa:
                empresa_activa = request.user.empresa_activa
            elif request.session.get("empresa_activa_id"):
                try:
                    from core.models import Empresa
                    empresa_activa = Empresa.objects.get(id=request.session["empresa_activa_id"], activa=True)
                except Exception:
                    pass
            if empresa_activa:
                url = url.replace("{empresa_id}", str(empresa_activa.id))
            else:
                return None
        return {
            "label": str(item.get("label", "")),
            "url": url,
            "icon": item.get("icon", ""),
            "permission": item.get("permission", ""),
        }
    except NoReverseMatch:
        logger.debug("NoReverseMatch para ítem de menú: %s", item.get("url", ""))
        return {"label": str(item.get("label", "")), "url": "#", "icon": item.get("icon", ""), "permission": item.get("permission", "")}
    except Exception as e:
        logger.debug("Error resolviendo URL ítem %s: %s", item.get("url", ""), e)
        return {"label": str(item.get("label", "")), "url": "#", "icon": item.get("icon", ""), "permission": item.get("permission", "")}


def obtener_submenus_por_app(app_id: str, permisos_usuario: Set[str], request=None) -> List[Dict[str, Any]]:
    """Obtiene los submenús visibles para una app específica según los permisos del usuario.
    Soporta ítems anidados: si un ítem tiene 'items' y no 'url', se procesan solo los hijos."""
    from core.services.navbar_visibilidad import (
        cargar_estado_granular,
        item_visible_en_navbar_granular,
    )

    app = obtener_app_por_id(app_id)
    if not app or not app.get("submenus"):
        return []

    modulos_oc_gran, items_oc_gran = cargar_estado_granular()

    submenus_visibles = []
    for submenu in app["submenus"]:
        items_visibles = []
        for item in submenu["items"]:
            if "items" in item and "url" not in item:
                for child in item.get("items", []):
                    if not item_visible_en_navbar_granular(
                        app_id,
                        child.get("menu_item_id"),
                        modulos_oc_gran,
                        items_oc_gran,
                    ):
                        continue
                    resolved = _resolver_url_item(child, request, permisos_usuario)
                    if resolved:
                        items_visibles.append(resolved)
                continue
            if not item_visible_en_navbar_granular(
                app_id,
                item.get("menu_item_id"),
                modulos_oc_gran,
                items_oc_gran,
            ):
                continue
            resolved = _resolver_url_item(item, request, permisos_usuario)
            if resolved:
                items_visibles.append(resolved)
        if items_visibles:
            submenus_visibles.append({
                "seccion": str(submenu.get("seccion", "")),
                "items": items_visibles,
            })
    return submenus_visibles


def _navbar_menu_oculto_global() -> bool:
    """
    True si el supervisor activó la ocultación global del menú navbar (Synap).
    Ver NavbarMenuGlobal y docs/general/NAVBAR_OCULTACION_GLOBAL_SUPERVISOR.md
    """
    try:
        from core.models import NavbarMenuGlobal

        return bool(NavbarMenuGlobal.get_solo().ocultar_todos_items)
    except Exception as e:
        logger.debug("NavbarMenuGlobal no disponible: %s", e)
        return False


def apps_visibles_sin_filtro_pwa(
    user: Optional[UsuarioExtendido], request=None
) -> List[Dict[str, Any]]:
    """Apps visibles en menú (escritorio y móvil) sin el filtro PWA de Nivel A."""
    from django.urls import reverse
    from django.urls.exceptions import NoReverseMatch
    from core.module_manager import ModuleManager

    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return []

    permisos_usuario = get_user_permission_set(user)
    es_supervisor_usuario = user_has_full_access(user)

    # Módulos activos: ModuleConfig + app instalada (misma regla que ModuleMiddleware).
    active_modules = set(ModuleManager().get_active_modules())
    
    # Siempre visibles en menú: cadena base y apps sin registro en ModuleConfig.
    # Los demás módulos de MODULE_CONFIGS (reports, ia, mpr, logistica, fe_afip, …)
    # dependen solo de ModuleConfig.is_active.
    core_modules = {'core', 'login', 'dashboard', 'stock', 'ventas', 'compras', 'self_checkout'}
    active_modules.update(core_modules)

    from core.services.navbar_visibilidad import (
        app_visible_en_navbar_granular,
        cargar_estado_granular,
    )

    modulos_oc_gran, _items_oc_gran = cargar_estado_granular()

    apps_filtradas = []
    for app in APPS_MENU:
        app_id = app.get("id")

        if not app_visible_en_navbar_granular(app_id, modulos_oc_gran):
            continue

        # REGLA 1: Archivo, Module Management y Settings solo visibles para el usuario 'supervisor' (superuser)
        # NOTA: El puesto/rol "Supervisor" NO puede ver estos módulos
        if app_id in ["archivo", "module_management", "settings", "odoo_migracion"]:
            # Solo el usuario 'supervisor' (por cod_usuario) es superuser
            if es_supervisor_usuario or user.is_superuser:
                app_copy = app.copy()
                try:
                    app_copy["url"] = reverse(app["url"])
                except NoReverseMatch:
                    app_copy["url"] = "#"
                
                # Agregar submenús si existen
                if app.get("submenus"):
                    submenus_visibles = obtener_submenus_por_app(app["id"], permisos_usuario, request)
                    if submenus_visibles:
                        app_copy["submenus"] = submenus_visibles
                
                apps_filtradas.append(app_copy)
            continue  # Saltar el resto de verificaciones para Module Management y Settings
        
        # REGLA 2: Para el resto de apps, verificar módulo activo
        if app_id not in active_modules:
            continue
            
        # REGLA 3: Si la app es solo para superusuarios y el usuario no lo es, saltar
        # Solo el usuario 'supervisor' (por cod_usuario) es superuser
        if app.get("superuser_only") and not (es_supervisor_usuario or user.is_superuser):
            continue
            
        # REGLA 4: Verificar permisos
        # Solo usuarios con permisos "*" (usuario supervisor) o con el permiso específico pueden acceder
        # El puesto/rol "Supervisor" solo tiene permisos específicos (reports.ver)
        if "*" in permisos_usuario or app["permiso"] in permisos_usuario:
            app_copy = app.copy()
            
            # Resolver la URL principal de la app
            try:
                app_copy["url"] = reverse(app["url"])
            except NoReverseMatch:
                app_copy["url"] = "#"
            
            # Agregar submenús si existen
            if app.get("submenus"):
                submenus_visibles = obtener_submenus_por_app(app["id"], permisos_usuario, request)
                if submenus_visibles:
                    app_copy["submenus"] = submenus_visibles
                else:
                    # Si no hay submenús visibles, no mostrar la app
                    continue
            
            apps_filtradas.append(app_copy)
    
    resultado = sorted(apps_filtradas, key=lambda x: x.get("orden", 999))
    # Ocultación global del navbar (solo supervisor puede revertir; ve solo Archivo)
    if _navbar_menu_oculto_global():
        es_sup = hasattr(user, "cod_usuario") and (user.cod_usuario or "").lower() == "supervisor"
        if es_sup:
            resultado = [a for a in resultado if a.get("id") == "archivo"]
        else:
            resultado = []
    return resultado


def apps_visibles_para_usuario(user: Optional[UsuarioExtendido], request=None) -> List[Dict[str, Any]]:
    """Obtiene las apps visibles para un usuario, ordenadas por prioridad, con sus submenús."""
    from core.pwa_nivel_a import filtrar_apps_menu_para_pwa_movil

    resultado = apps_visibles_sin_filtro_pwa(user, request)
    return filtrar_apps_menu_para_pwa_movil(resultado, request, user=user)


# ─────────────────────────────────────────────
# COMPATIBILIDAD CON CÓDIGO EXISTENTE
# ─────────────────────────────────────────────

# Mantener las constantes antiguas para compatibilidad
MODULOS_MENU = APPS_MENU

# Obtener submenús para compatibilidad
settings_app = obtener_app_por_id("settings")
ADMIN_SIDEBAR_MENU = settings_app["submenus"] if settings_app and settings_app.get("submenus") else {}

INVENTORY_SIDEBAR_MENU = []

# Función de compatibilidad
def modulos_visibles_para_usuario(user: Optional[UsuarioExtendido]) -> List[Dict[str, Any]]:
    """Función de compatibilidad que usa la nueva estructura"""
    return apps_visibles_para_usuario(user)

# Firebase deshabilitado para administraNET Analytics
# Antes de usar firestore, asegúrate de inicializar Firebase:
# get_firebase_app()  # Comentado - Firebase deshabilitado

def sincronizar_usuario_desde_firestore(decoded_token: Dict[str, Any]) -> UsuarioExtendido:
    """
    DESHABILITADO: Esta función sincronizaba usuarios desde Firebase.
    Para administraNET Analytics, los usuarios se autentican directamente contra MySQL.
    """
    raise NotImplementedError("Firebase deshabilitado - usar autenticación administraNET Gestión")
    
    # Código deshabilitado
    # uid = decoded_token.get("uid")
    # email = decoded_token.get("email")
    # nombre = decoded_token.get("name", "")
    # 
    # if not uid or not email:
    #     raise ValueError("UID y email son requeridos para sincronizar usuario")
    # 
    # try:
    #     firestore_db = firestore.client()
    #     doc_ref = firestore_db.collection("usuarios").document(uid)
    #     doc = doc_ref.get()
    # 
    #     idioma = "es"
    #     if doc.exists:
    #         data = doc.to_dict()
    #         idioma = data.get("idioma", "es")
    # 
    #     usuario, creado = UsuarioExtendido.objects.get_or_create(
    #         uid=uid, 
    #         defaults={
    #             "email": email,
    #             "nombre": nombre,
    #             "idioma": idioma,
    #         }
    #     )
    # 
    #     # Actualizar campos si han cambiado
    #     actualizado = False
    #     if usuario.email != email:
    #         usuario.email = email
    #         actualizado = True
    #     if usuario.nombre != nombre:
    #         usuario.nombre = nombre
    #         actualizado = True
    #     if usuario.idioma != idioma:
    #         usuario.idioma = idioma
    #         actualizado = True
    # 
    #     if actualizado:
    #         usuario.save()
    #         # Invalidar cache
    #         cache.delete(f"user_uid_{uid}")
    #         cache.delete(f"user_session_{uid}")
    # 
    #     return usuario
    # 
    # except Exception as e:
    #     logger.error(f"Error sincronizando usuario {uid}: {e}")
    #     raise


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
    elif hasattr(user, 'get_permisos_totales'):
        # Para AdministraNETUser (usuario de administraNET Gestión)
        permisos_usuario = user.get_permisos_totales()
    else:
        permisos_usuario = set()
    
    # El usuario "supervisor" de administraNET tiene todos los permisos
    if hasattr(user, 'cod_usuario') and (user.cod_usuario or '').lower() == 'supervisor':
        permisos_usuario = {"*"}

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
    # Solo el usuario "supervisor" (por cod_usuario) tiene acceso total
    # NOTA: El puesto/rol "Supervisor" NO otorga acceso total
    es_supervisor_usuario = False
    if hasattr(user, 'cod_usuario') and (user.cod_usuario or '').lower() == 'supervisor':
        es_supervisor_usuario = True
        permisos["rol_permitido"] = True
    elif roles_permitidos and isinstance(user, UsuarioExtendido):
        user_roles = [r.nombre.lower() for r in user.roles.filter(activo=True)]
        permisos["rol_permitido"] = any(r.lower() in user_roles for r in roles_permitidos)
    elif roles_permitidos and hasattr(user, 'is_admin') and user.is_admin():
        permisos["rol_permitido"] = True
    elif roles_permitidos:
        permisos["rol_permitido"] = False

    if debug and faltantes:
        permisos["permisos_faltantes"] = faltantes

    # ✅ Agregar lista de permisos para el template (debug/info)
    permisos["permisos_usuario"] = sorted(permisos_usuario)

    return permisos


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

def get_empresa_actual(request):
    """
    Obtiene la empresa activa del usuario desde la sesión o del usuario
    """
    from core.models import Empresa
    
    # Intentar obtener desde la sesión
    empresa_id = request.session.get('empresa_activa_id')
    if empresa_id:
        try:
            return Empresa.objects.get(id=empresa_id, activa=True)
        except Empresa.DoesNotExist:
            pass
    
    # Intentar obtener desde el usuario
    if hasattr(request.user, 'empresa_activa') and request.user.empresa_activa:
        return request.user.empresa_activa
    
    # Fallback: primera empresa activa
    return Empresa.objects.filter(activa=True).first()


def get_user_empresa(request):
    """
    Alias de get_empresa_actual para mantener compatibilidad con código existente
    """
    return get_empresa_actual(request)