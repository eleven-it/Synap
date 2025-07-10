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
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

logger = logging.getLogger(__name__)

# core/utils.py

# ─────────────────────────────────────────────
# CONFIGURACIÓN CENTRAL DE MENÚS Y APPS
# ─────────────────────────────────────────────

# Configuración principal de apps/modulos
APPS_MENU = [
    {
        "id": "sales",
        "nombre": _("Sales"),
        "permiso": "sales.ver",
        "url": "sales:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M3 3h6v6H3V3zm0 12h6v6H3v-6zm12-12h6v6h-6V3zm0 12h6v6h-6v-6z'/></svg>""",
        "orden": 1,
        "color": "orange",
        "submenus": [
            {
                "seccion": _("Main"),
                "items": [
                    {"label": _("Dashboard"), "url": "sales:dashboard", "icon": "dashboard", "permission": "sales.ver"},
                ]
            },
            {
                "seccion": _("Customer Management"),
                "items": [
                    {"label": _("Clients"), "url": "sales:client_list", "icon": "groups", "permission": "sales.ver_client"},
                    {"label": _("Create Client"), "url": "sales:client_create", "icon": "person_add", "permission": "sales.crear_client"},
                ]
            },
            {
                "seccion": _("Sales Operations"),
                "items": [
                    {"label": _("Orders"), "url": "sales:sales_order_list", "icon": "assignment", "permission": "sales.ver_order"},
                    {"label": _("Create Order"), "url": "sales:sales_order_create", "icon": "add_box", "permission": "sales.crear_order"},
                ]
            },
            {
                "seccion": _("Invoices & Payments"),
                "items": [
                    {"label": _("Invoices"), "url": "sales:invoice_list", "icon": "receipt_long", "permission": "sales.ver_invoice"},
                    {"label": _("Payments"), "url": "sales:payment_list", "icon": "payments", "permission": "sales.ver_payment"},
                ]
            },
            {
                "seccion": _("Logistics"),
                "items": [
                    {"label": _("Deliveries"), "url": "sales:delivery_order_list", "icon": "local_shipping", "permission": "sales.ver_delivery"},
                    {"label": _("Returns"), "url": "sales:return_delivery_list", "icon": "undo", "permission": "sales.ver_return"},
                    {"label": _("Credit Notes"), "url": "sales:credit_note_list", "icon": "note_add", "permission": "sales.ver_credit_note"},
                ]
            },
            {
                "seccion": _("Reports & Configuration"),
                "items": [
                    {"label": _("Reports"), "url": "sales:reports_dashboard", "icon": "bar_chart", "permission": "sales.ver_report"},
                    {"label": _("Price Lists"), "url": "sales:price_list_list", "icon": "price_change", "permission": "sales.ver_price_list"},
                    {"label": _("Payment Terms"), "url": "sales:payment_term_list", "icon": "schedule", "permission": "sales.ver_payment_term"},
                ]
            }
        ]
    },
    {
        "id": "inventory",
        "nombre": _("Inventory"),
        "permiso": "inventory.ver",
        "url": "inventory:stock_dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M4 6h16M4 12h16M4 18h16'/></svg>""",
        "orden": 2,
        "color": "green",
        "submenus": [
            {
                "seccion": _("Main"),
                "items": [
                    {
                        "label": _("Dashboard"),
                        "url": "inventory:stock_dashboard",
                        "icon": "dashboard",
                        "permission": "inventory.ver"
                    },
                    {
                        "label": _("Products"),
                        "url": "inventory:product_list",
                        "icon": "inventory",
                        "permission": "inventory.ver_product"
                    }
                ]
            },
            {
                "seccion": _("Stock Management"),
                "items": [
                    {
                        "label": _("Warehouses"),
                        "url": "inventory:warehouse_list",
                        "icon": "warehouse",
                        "permission": "inventory.ver_warehouse"
                    },
                    {
                        "label": _("Locations"),
                        "url": "inventory:location_list",
                        "icon": "location_on",
                        "permission": "inventory.ver_location"
                    }
                ]
            },
            {
                "seccion": _("Catalog"),
                "items": [
                    {
                        "label": _("Brands"),
                        "url": "inventory:brand_list",
                        "icon": "label",
                        "permission": "inventory.view_brand"
                    },
                    {
                        "label": _("Categories"),
                        "url": "inventory:category_list",
                        "icon": "category",
                        "permission": "inventory.view_category"
                    },
                    {
                        "label": _("Subcategories"),
                        "url": "inventory:subcategory_list",
                        "icon": "subdirectory_arrow_right",
                        "permission": "inventory.view_subcategory"
                    }
                ]
            },
            {
                "seccion": _("TiendaNube"),
                "items": [
                    {
                        "label": _("Dashboard"),
                        "url": "inventory:tiendanube_dashboard",
                        "icon": "cloud",
                        "permission": "inventory.ver_dashboard_tiendanube"
                    }
                ]
            }
        ]
    },
    {
        "id": "tiendanube",
        "nombre": _("TiendaNube"),
        "permiso": "tiendanube.access",
        "url": "tiendanube:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M17.5 19a4.5 4.5 0 100-9 5.5 5.5 0 00-10.9 1.5A4.5 4.5 0 006.5 19h11z'/></svg>""",
        "orden": 3,
        "color": "purple",
        "submenus": [
            {
                "seccion": _("Integration"),
                "items": [
                    {
                        "label": _("Dashboard"),
                        "url": "tiendanube:dashboard",
                        "icon": "dashboard",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Configuration"),
                        "url": "tiendanube:config_list",
                        "icon": "settings",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Configuration Wizard"),
                        "url": "tiendanube:config_wizard",
                        "icon": "wizard",
                        "permission": "tiendanube.access"
                    }
                ]
            },
            {
                "seccion": _("Sync Management"),
                "items": [
                    {
                        "label": _("Sync Logs"),
                        "url": "tiendanube:logs_list",
                        "icon": "history",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Manual Sync"),
                        "url": "tiendanube:manual_sync",
                        "icon": "sync",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Sync Products"),
                        "url": "tiendanube:sync_products",
                        "icon": "inventory",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Sync All Products"),
                        "url": "tiendanube:sync_products",
                        "icon": "sync_alt",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Sync All Stock"),
                        "url": "tiendanube:sync_all_stock",
                        "icon": "local_shipping",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Sync Customers"),
                        "url": "tiendanube:sync_customers",
                        "icon": "people",
                        "permission": "tiendanube.access"
                    }
                ]
            },
            {
                "seccion": _("Mappings"),
                "items": [
                    {
                        "label": _("Product Mapping"),
                        "url": "tiendanube:mapping_list",
                        "icon": "link",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Customer Mapping"),
                        "url": "tiendanube:customer_mapping_list",
                        "icon": "person",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Order Mapping"),
                        "url": "tiendanube:order_mapping_list",
                        "icon": "receipt",
                        "permission": "tiendanube.access"
                    }
                ]
            },
            {
                "seccion": _("Restock Management"),
                "items": [
                    {
                        "label": _("Product Restock Policies"),
                        "url": "tiendanube:product_restock_policy_list",
                        "icon": "policy",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Restock Rules"),
                        "url": "tiendanube:restock_rule_list",
                        "icon": "rule",
                        "permission": "tiendanube.access"
                    },
                    {
                        "label": _("Restock Logs"),
                        "url": "tiendanube:restock_log_list",
                        "icon": "history",
                        "permission": "tiendanube.access"
                    }
                ]
            },
            {
                "seccion": _("Reports & Analytics"),
                "items": [
                    {
                        "label": _("Reports"),
                        "url": "tiendanube:reports",
                        "icon": "analytics",
                        "permission": "tiendanube.access"
                    }
                ]
            }
        ]
    },
    {
        "id": "purchases",
        "nombre": _("Purchases"),
        "permiso": "purchases.ver",
        "url": "purchases:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z'/></svg>""",
        "orden": 4,
        "color": "red",
        "submenus": [
            {
                "seccion": _("Main"),
                "items": [
                    {
                        "label": _("Dashboard"),
                        "url": "purchases:dashboard",
                        "icon": "dashboard",
                        "permission": "purchases.ver_dashboard"
                    }
                ]
            },
            {
                "seccion": _("Supplier Management"),
                "items": [
                    {
                        "label": _("Suppliers"),
                        "url": "purchases:supplier_list",
                        "icon": "business",
                        "permission": "purchases.ver_supplier"
                    },
                    {
                        "label": _("Create Supplier"),
                        "url": "purchases:supplier_create",
                        "icon": "add_business",
                        "permission": "purchases.crear_supplier"
                    }
                ]
            },
            {
                "seccion": _("Purchase Documents"),
                "items": [
                    {
                        "label": _("Documents"),
                        "url": "purchases:document_list",
                        "icon": "description",
                        "permission": "purchases.ver_request"
                    },
                    {
                        "label": _("Create Document"),
                        "url": "purchases:document_create",
                        "icon": "add",
                        "permission": "purchases.crear_request"
                    }
                ]
            },
            {
                "seccion": _("Quotations"),
                "items": [
                    {
                        "label": _("Quotations"),
                        "url": "purchases:quotation_list",
                        "icon": "description",
                        "permission": "purchases.ver_quotation"
                    },
                    {
                        "label": _("Create Quotation"),
                        "url": "purchases:quotation_create",
                        "icon": "post_add",
                        "permission": "purchases.crear_quotation"
                    },
                    {
                        "label": _("Compare Quotations"),
                        "url": "purchases:quotation_compare",
                        "icon": "compare_arrows",
                        "permission": "purchases.ver_quotation"
                    }
                ]
            },
            {
                "seccion": _("Purchase Orders"),
                "items": [
                    {
                        "label": _("Orders"),
                        "url": "purchases:order_list",
                        "icon": "shopping_cart",
                        "permission": "purchases.ver_order"
                    },
                    {
                        "label": _("Create Order"),
                        "url": "purchases:order_create",
                        "icon": "add_shopping_cart",
                        "permission": "purchases.crear_order"
                    }
                ]
            },
            {
                "seccion": _("Receipts"),
                "items": [
                    {
                        "label": _("Receipts"),
                        "url": "purchases:receipt_list",
                        "icon": "inventory_2",
                        "permission": "purchases.ver_receipt"
                    }
                ]
            },
            {
                "seccion": _("Supplier Ratings"),
                "items": [
                    {
                        "label": _("Ratings"),
                        "url": "purchases:rating_list",
                        "icon": "star_rate",
                        "permission": "purchases.ver_rating"
                    },
                    {
                        "label": _("Create Rating"),
                        "url": "purchases:rating_create",
                        "icon": "rate_review",
                        "permission": "purchases.crear_rating"
                    }
                ]
            },
            {
                "seccion": _("Approval Workflows"),
                "items": [
                    {
                        "label": _("Workflows"),
                        "url": "purchases:workflow_list",
                        "icon": "account_tree",
                        "permission": "purchases.ver_workflow"
                    },
                    {
                        "label": _("Create Workflow"),
                        "url": "purchases:workflow_create",
                        "icon": "add_chart",
                        "permission": "purchases.crear_workflow"
                    }
                ]
            },
            {
                "seccion": _("Reports & Settings"),
                "items": [
                    {
                        "label": _("Reports"),
                        "url": "purchases:reports",
                        "icon": "bar_chart",
                        "permission": "purchases.ver_report"
                    },
                    {
                        "label": _("Settings"),
                        "url": "purchases:settings",
                        "icon": "settings",
                        "permission": "purchases.ver_settings"
                    }
                ]
            }
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
                        "permission": "usuarios.dashboard"
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
                        "permission": "usuarios.ver"
                    },
                    {
                        "label": _("Roles"),
                        "url": "core:listar_roles",
                        "icon": "admin_panel_settings",
                        "permission": "usuarios.roles.ver"
                    },
                    {
                        "label": _("Permissions"),
                        "url": "core:listar_permisos",
                        "icon": "vpn_key",
                        "permission": "usuarios.permisos.ver"
                    },
                    {
                        "label": _("Universal Contacts"),
                        "items": [
                            {
                                "label": _("All Contacts"),
                                "url": "core:contact_list",
                                "icon": "contacts",
                                "permission": "core.ver_contact"
                            },
                            {
                                "label": _("Create Contact"),
                                "url": "core:contact_create",
                                "icon": "person_add",
                                "permission": "core.crear_contact"
                            },
                            {
                                "label": _("Contact Relationships"),
                                "url": "core:contact_relationship_list",
                                "icon": "link",
                                "permission": "core.ver_contact"
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
                        "permission": "configuracion.uom"
                    },
                    {
                        "label": _("Empresas"),
                        "url": "core:empresa_listar",
                        "icon": "business",
                        "permission": "configuracion.sistema"
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
                        "permission": "configuracion.moneda"
                    },
                    {
                        "label": _("Exchange Rates"),
                        "url": "core:exchange_rate_list",
                        "icon": "currency_exchange",
                        "permission": "configuracion.moneda"
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
                        "permission": "configuracion.sistema"
                    },
                    {
                        "label": _("CDN Wizard"),
                        "url": "core:cdn_wizard",
                        "icon": "cloud",
                        "permission": "configuracion.sistema"
                    },
                    {
                        "label": _("Hooks & Events"),
                        "url": "core:hook_dashboard",
                        "icon": "event",
                        "permission": "configuracion.sistema"
                    }
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
]

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

def obtener_submenus_por_app(app_id: str, permisos_usuario: Set[str]) -> List[Dict[str, Any]]:
    """Obtiene los submenús visibles para una app específica según los permisos del usuario"""
    from django.urls import reverse
    from django.urls.exceptions import NoReverseMatch
    
    app = obtener_app_por_id(app_id)
    if not app or not app.get("submenus"):
        return []
    
    submenus_visibles = []
    for submenu in app["submenus"]:
        items_visibles = []
        for item in submenu["items"]:
            if "*" in permisos_usuario or item.get("permission", "") in permisos_usuario:
                try:
                    # Verificar que la clave 'url' existe
                    if "url" not in item:
                        print(f"Warning: Item missing 'url' key: {item}")
                        continue
                    
                    # Usar reverse para generar la URL correcta
                    url = reverse(item["url"])
                    print(f"Successfully resolved URL '{item['url']}' to '{url}'")
                except NoReverseMatch:
                    # Si no se puede resolver la URL, usar una URL por defecto
                    print(f"Warning: Could not resolve URL '{item.get('url', '')}' for item: {item}")
                    url = "#"
                except Exception as e:
                    # Manejar cualquier otro error
                    print(f"Error processing item {item}: {e}")
                    url = "#"
                
                items_visibles.append({
                    "label": str(item.get("label", "")),
                    "url": url,
                    "icon": item.get("icon", ""),
                    "permission": item.get("permission", "")
                })
        
        if items_visibles:
            submenus_visibles.append({
                "seccion": str(submenu.get("seccion", "")),
                "items": items_visibles
            })
    
    return submenus_visibles

def apps_visibles_para_usuario(user: Optional[UsuarioExtendido]) -> List[Dict[str, Any]]:
    """Obtiene las apps visibles para un usuario, ordenadas por prioridad, con sus submenús"""
    from django.urls import reverse
    from django.urls.exceptions import NoReverseMatch
    
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return []

    permisos_usuario = set()
    if isinstance(user, UsuarioExtendido):
        permisos_usuario = user.get_permisos_totales()

    apps_filtradas = []
    for app in APPS_MENU:
        # Si la app es solo para superusuarios y el usuario no lo es, saltar
        if app.get("superuser_only") and not user.is_superuser:
            continue
        if "*" in permisos_usuario or app["permiso"] in permisos_usuario:
            app_copy = app.copy()
            
            # Resolver la URL principal de la app
            try:
                app_copy["url"] = reverse(app["url"])
            except NoReverseMatch:
                app_copy["url"] = "#"
            
            # Agregar submenús si existen
            if app.get("submenus"):
                submenus_visibles = obtener_submenus_por_app(app["id"], permisos_usuario)
                if submenus_visibles:
                    app_copy["submenus"] = submenus_visibles
                else:
                    # Si no hay submenús visibles, no mostrar la app
                    continue
            
            apps_filtradas.append(app_copy)
    
    # Ordenar por el campo 'orden'
    return sorted(apps_filtradas, key=lambda x: x.get('orden', 999))

# ─────────────────────────────────────────────
# COMPATIBILIDAD CON CÓDIGO EXISTENTE
# ─────────────────────────────────────────────

# Mantener las constantes antiguas para compatibilidad
MODULOS_MENU = APPS_MENU

# Obtener submenús para compatibilidad
settings_app = obtener_app_por_id("settings")
ADMIN_SIDEBAR_MENU = settings_app["submenus"] if settings_app and settings_app.get("submenus") else {}

inventory_app = obtener_app_por_id("inventory")
INVENTORY_SIDEBAR_MENU = inventory_app["submenus"] if inventory_app and inventory_app.get("submenus") else {}

# Función de compatibilidad
def modulos_visibles_para_usuario(user: Optional[UsuarioExtendido]) -> List[Dict[str, Any]]:
    """Función de compatibilidad que usa la nueva estructura"""
    return apps_visibles_para_usuario(user)

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