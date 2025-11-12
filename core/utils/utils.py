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
                    {"label": _("Point of Sale (TPV)"), "url": "sales:pos_dashboard", "icon": "point_of_sale", "permission": "sales.view_pos"},
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
                "seccion": _("Payment Configuration"),
                "items": [
                    {"label": _("Payment Methods"), "url": "sales:payment_method_list", "icon": "credit_card", "permission": "sales.ver"},
                    {"label": _("Payment Processors"), "url": "sales:payment_processor_list", "icon": "settings", "permission": "sales.ver"},
                ]
            },
            {
                "seccion": _("Reports & Configuration"),
                "items": [
                    {"label": _("Reports"), "url": "sales:reports_dashboard", "icon": "bar_chart", "permission": "sales.ver_report"},
                    {"label": _("Price Lists"), "url": "sales:price_list_list", "icon": "price_change", "permission": "sales.ver_price_list"},
                    {"label": _("Payment Terms"), "url": "sales:payment_term_list", "icon": "schedule", "permission": "sales.ver_payment_term"},
                    {"label": _("POS Terminals"), "url": "sales:terminal_list", "icon": "terminal", "permission": "sales.view_posterminal"}
                ]
            }
        ]
    },
    {
        "id": "inventory",
        "nombre": _("Inventory"),
        "permiso": "inventory.ver_dashboard",
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
                        "permission": "inventory.ver_dashboard"
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
                        "permission": "inventory.config_tiendanube"
                    }
                ]
            }
        ]
    },
    {
        "id": "tiendanube",
        "nombre": _("TiendaNube"),
        "permiso": "tiendanube.view_integration",
        "url": "tiendanube:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M17.5 19a4.5 4.5 0 100-9 5.5 5.5 0 00-10.9 1.5A4.5 4.5 0 006.5 19h11z'/></svg>""",
        "orden": 3,
        "color": "purple",
        "submenus": [
            {
                "seccion": _("Integración Synap"),
                "items": [
                    {"label": _("Products"), "url": "tiendanube:mapping_list", "icon": "inventory", "permission": "tiendanube.sync_products"},
                    {"label": _("Orders"), "url": "tiendanube:order_mapping_list", "icon": "assignment", "permission": "tiendanube.sync_orders"},
                    {"label": _("Sync Logs"), "url": "tiendanube:logs_list", "icon": "history", "permission": "tiendanube.view_sync_log"}
                ]
            },
            {
                "seccion": _("Integración administraNET"),
                "items": [
                    {"label": _("Cond. Venta Tiendanube ↔ Adminet"), "url": "tiendanube:cond_venta_map_list", "icon": "compare_arrows", "permission": "tiendanube.configure_integration"},
                    {"label": _("Clientes Tiendanube ↔ Adminet"), "url": "tiendanube:cliente_map_list", "icon": "people", "permission": "tiendanube.configure_integration"},
                    {"label": _("Conexión Adminet (MySQL)"), "url": "tiendanube:adminet_connection", "icon": "storage", "permission": "tiendanube.configure_integration"}
                ]
            },
            {
                "seccion": _("General"),
                "items": [
                    {"label": _("Dashboard"), "url": "tiendanube:dashboard", "icon": "dashboard", "permission": "tiendanube.view_integration"},
                    {"label": _("Settings"), "url": "tiendanube:config_list", "icon": "settings", "permission": "tiendanube.configure_integration"}
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
        "id": "accounting",
        "nombre": _("Accounting"),
        "permiso": "accounting.ver",
        "url": "accounting:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z'/></svg>""",
        "orden": 4,
        "color": "emerald",
        "submenus": [
            {
                "seccion": _("Dashboard"),
                "items": [
                    {
                        "label": _("Dashboard"),
                        "url": "accounting:dashboard",
                        "icon": "dashboard",
                        "permission": "accounting.ver"
                    }
                ]
            },
            {
                "seccion": _("Chart of Accounts"),
                "items": [
                    {
                        "label": _("Accounts"),
                        "url": "accounting:account_list",
                        "icon": "account_balance",
                        "permission": "accounting.view_chartofaccounts"
                    },
                    {
                        "label": _("Account Types"),
                        "url": "accounting:account_type_list",
                        "icon": "category",
                        "permission": "accounting.view_chartofaccounts"
                    }
                ]
            },
            {
                "seccion": _("Journal Management"),
                "items": [
                    {
                        "label": _("Journal Entries"),
                        "url": "accounting:journal_entry_list",
                        "icon": "receipt_long",
                        "permission": "accounting.view_journalentry"
                    },
                    {
                        "label": _("Journals"),
                        "url": "accounting:journal_list",
                        "icon": "book",
                        "permission": "accounting.view_journal"
                    }
                ]
            },
            {
                "seccion": _("Tax Management"),
                "items": [
                    {
                        "label": _("Tax Groups"),
                        "url": "accounting:tax_group_list",
                        "icon": "group_work",
                        "permission": "accounting.view_taxgroup"
                    },
                    {
                        "label": _("Taxes"),
                        "url": "accounting:tax_list",
                        "icon": "receipt",
                        "permission": "accounting.view_tax"
                    },
                    {
                        "label": _("Fiscal Positions"),
                        "url": "accounting:fiscal_position_list",
                        "icon": "location_on",
                        "permission": "accounting.view_fiscalposition"
                    }
                ]
            },
            {
                "seccion": _("Period Management"),
                "items": [
                    {
                        "label": _("Accounting Periods"),
                        "url": "accounting:period_list",
                        "icon": "calendar_today",
                        "permission": "accounting.view_accountingperiod"
                    },
                    {
                        "label": _("Fiscal Years"),
                        "url": "accounting:fiscal_year_list",
                        "icon": "event",
                        "permission": "accounting.view_fiscalyear"
                    }
                ]
            },
            {
                "seccion": _("Configuration"),
                "items": [
                    {
                        "label": _("Currencies"),
                        "url": "accounting:currency_list",
                        "icon": "payments",
                        "permission": "core.view_currency"
                    }
                ]
            },
            {
                "seccion": _("Reports"),
                "items": [
                    {
                        "label": _("Balance Sheet"),
                        "url": "accounting:balance_sheet_report",
                        "icon": "assessment",
                        "permission": "accounting.view_report"
                    },
                    {
                        "label": _("Income Statement"),
                        "url": "accounting:income_statement_report",
                        "icon": "trending_up",
                        "permission": "accounting.view_report"
                    },
                    {
                        "label": _("Trial Balance"),
                        "url": "accounting:trial_balance_report",
                        "icon": "balance",
                        "permission": "accounting.view_report"
                    },
                    {
                        "label": _("General Ledger"),
                        "url": "accounting:general_ledger_report",
                        "icon": "library_books",
                        "permission": "accounting.view_report"
                    },
                    {
                        "label": _("Tax Report"),
                        "url": "accounting:tax_report",
                        "icon": "receipt_long",
                        "permission": "accounting.view_report"
                    }
                ]
            },
            {
                "seccion": _("Advanced Reports"),
                "items": [
                    {
                        "label": _("Bank Reconciliation"),
                        "url": "accounting:bank_reconciliation_report",
                        "icon": "account_balance_wallet",
                        "permission": "accounting.view_report"
                    },
                    {
                        "label": _("Trend Analysis"),
                        "url": "accounting:trend_analysis_report",
                        "icon": "show_chart",
                        "permission": "accounting.view_report"
                    },
                    {
                        "label": _("Financial Ratios"),
                        "url": "accounting:financial_ratios_report",
                        "icon": "analytics",
                        "permission": "accounting.view_report"
                    },
                    {
                        "label": _("Custom Reports"),
                        "url": "accounting:custom_reports",
                        "icon": "build",
                        "permission": "accounting.view_report"
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
                "seccion": _("Catalog"),
                "items": [
                    {
                        "label": _("Interactive catalog"),
                        "url": "reports:catalog",
                        "icon": "dashboard",
                        "permission": "reports.ver"
                    },
                    {
                        "label": _("Workspace Smart TV"),
                        "url": "reports:workspace",
                        "icon": "dashboard_customize",
                        "permission": "reports.ver"
                    },
                    {
                        "label": _("Saved dashboards"),
                        "url": "reports:saved_dashboards",
                        "icon": "bookmark",
                        "permission": "reports.ver"
                    }
                ]
            }
        ]
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
                        "permission": "mercadopago.view_mercadopagoconfig"
                    },
                    {
                        "label": _("Add Configuration"),
                        "url": "mercadopago:config_create",
                        "icon": "add_circle",
                        "permission": "mercadopago.add_mercadopagoconfig"
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
                        "permission": "mercadopago.view_mercadopagodevice"
                    },
                    {
                        "label": _("Add Device"),
                        "url": "mercadopago:device_create",
                        "icon": "add_circle",
                        "permission": "mercadopago.add_mercadopagodevice"
                    },
                    {
                        "label": _("Device Status"),
                        "url": "mercadopago:device_status",
                        "icon": "monitor_heart",
                        "permission": "mercadopago.view_mercadopagodevice"
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
                        "permission": "mercadopago.view_mercadopagotransaction"
                    },
                    {
                        "label": _("Failed Transactions"),
                        "url": "mercadopago:transaction_failed",
                        "icon": "error_outline",
                        "permission": "mercadopago.view_mercadopagotransaction"
                    },
                    {
                        "label": _("Transaction Reports"),
                        "url": "mercadopago:transaction_reports",
                        "icon": "analytics",
                        "permission": "mercadopago.view_reports"
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
                        "permission": "mercadopago.view_reports"
                    },
                    {
                        "label": _("Payment Methods"),
                        "url": "mercadopago:payment_methods_report",
                        "icon": "credit_card",
                        "permission": "mercadopago.view_reports"
                    },
                    {
                        "label": _("Device Performance"),
                        "url": "mercadopago:device_performance_report",
                        "icon": "speed",
                        "permission": "mercadopago.view_reports"
                    },
                    {
                        "label": _("Export Data"),
                        "url": "mercadopago:export_data",
                        "icon": "download",
                        "permission": "mercadopago.export_data"
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
                        "permission": "clover.view_cloverdevice"
                    },
                    {
                        "label": _("Add Device"),
                        "url": "clover:device_create",
                        "icon": "add_circle",
                        "permission": "clover.add_cloverdevice"
                    },
                    {
                        "label": _("Device Status"),
                        "url": "clover:device_status",
                        "icon": "monitor_heart",
                        "permission": "clover.view_cloverdevice"
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
                        "permission": "clover.view_clovertransaction"
                    },
                    {
                        "label": _("Failed Transactions"),
                        "url": "clover:transaction_failed",
                        "icon": "error_outline",
                        "permission": "clover.view_clovertransaction"
                    },
                    {
                        "label": _("Transaction Reports"),
                        "url": "clover:transaction_reports",
                        "icon": "analytics",
                        "permission": "clover.view_reports"
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
                        "permission": "clover.view_cloverconfig"
                    },
                    {
                        "label": _("Webhooks"),
                        "url": "clover:webhook_list",
                        "icon": "webhook",
                        "permission": "clover.view_cloverwebhook"
                    },
                    {
                        "label": _("API Configuration"),
                        "url": "clover:api_config",
                        "icon": "api",
                        "permission": "clover.change_cloverconfig"
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
                        "permission": "clover.view_reports"
                    },
                    {
                        "label": _("Payment Methods"),
                        "url": "clover:payment_methods_report",
                        "icon": "credit_card",
                        "permission": "clover.view_reports"
                    },
                    {
                        "label": _("Device Performance"),
                        "url": "clover:device_performance_report",
                        "icon": "speed",
                        "permission": "clover.view_reports"
                    },
                    {
                        "label": _("Export Data"),
                        "url": "clover:export_data",
                        "icon": "download",
                        "permission": "clover.export_data"
                    }
                ]
            }
        ]
    },
    {
        "id": "administraNET_integration",
        "nombre": _("Integración administraNET"),
        "permiso": "administraNET_integration.view_dashboard",
        "url": "adminet:adminet_panel",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
            <path stroke-linecap='round' stroke-linejoin='round' d='M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1'/>
        </svg>""",
        "orden": 15,
        "color": "purple",
        "submenus": [
            {
                "seccion": _("Dashboard"),
                "items": [
                    {"label": _("Dashboard"), "url": "adminet:adminet_panel", "icon": "dashboard", "permission": "administraNET_integration.view_dashboard"},
                    {"label": _("Status"), "url": "adminet:adminet_status", "icon": "monitor_heart", "permission": "administraNET_integration.view_dashboard"},
                ]
            },
            {
                "seccion": _("Configuration"),
                "items": [
                    {"label": _("Connection Settings"), "url": "adminet:adminet_connection", "icon": "settings", "permission": "administraNET_integration.change_config"},
                    {"label": _("Mappings"), "url": "adminet:adminet_mappings", "icon": "link", "permission": "administraNET_integration.view_mappings"},
                    {"label": _("Sync Settings"), "url": "adminet:sync_settings", "icon": "sync", "permission": "administraNET_integration.change_config"},
                ]
            },
            {
                "seccion": _("Synchronization"),
                "items": [
                    {"label": _("Manual Sync"), "url": "adminet:adminet_manual_sync", "icon": "play_arrow", "permission": "administraNET_integration.manual_sync"},
                    {"label": _("Sync History"), "url": "adminet:adminet_sync_history", "icon": "history", "permission": "administraNET_integration.view_logs"},
                    {"label": _("Data Validation"), "url": "adminet:adminet_validation", "icon": "verified", "permission": "administraNET_integration.view_logs"},
                ]
            },
            {
                "seccion": _("Monitoring"),
                "items": [
                    {"label": _("Logs"), "url": "adminet:adminet_sync_history", "icon": "article", "permission": "administraNET_integration.view_logs"},
                    {"label": _("Error Reports"), "url": "adminet:adminet_sync_history", "icon": "error", "permission": "administraNET_integration.view_logs"},
                    {"label": _("Performance"), "url": "adminet:adminet_status", "icon": "speed", "permission": "administraNET_integration.view_logs"},
                ]
            }
        ]
    },
    {
        "id": "finance",
        "nombre": _("Finance"),
        "permiso": "finance.view_creditlimitlog",
        "url": "finance:account_receivable_list",
        "icono_svg": "<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1'/></svg>",
        "orden": 20,
        "color": "teal",
        "submenus": [
            {
                "seccion": _("Accounts Receivable"),
                "items": [
                    {"label": _("Accounts Receivable"), "url": "finance:account_receivable_list", "icon": "account_balance_wallet", "permission": "finance.view_creditlimitlog"},
                    {"label": _("Create Account Receivable"), "url": "finance:account_receivable_create", "icon": "add", "permission": "finance.add_creditlimitlog"}
                ]
            },
            {
                "seccion": _("Credit Limit Logs"),
                "items": [
                    {"label": _("Credit Limit Logs"), "url": "finance:creditlimitlog_list", "icon": "history", "permission": "finance.view_creditlimitlog"},
                    {"label": _("Create Credit Limit Log"), "url": "finance:creditlimitlog_create", "icon": "add", "permission": "finance.add_creditlimitlog"}
                ]
            },
            {
                "seccion": _("Financial Reports"),
                "items": [
                    {"label": _("Financial Reports"), "url": "finance:financialreport_list", "icon": "bar_chart", "permission": "finance.view_financialreport"},
                    {"label": _("Create Financial Report"), "url": "finance:financialreport_create", "icon": "add", "permission": "finance.add_financialreport"}
                ]
            }
        ]
    },
    {
        "id": "logistics",
        "nombre": _("Logistics"),
        "permiso": "logistics.view_deliveryroute",
        "url": "logistics:dashboard",
        "icono_svg": "<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'><path stroke-linecap='round' stroke-linejoin='round' d='M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z'/></svg>",
        "orden": 21,
        "color": "blue",
        "submenus": [
            {
                "seccion": _("Main"),
                "items": [
                    {"label": _("Dashboard"), "url": "logistics:dashboard", "icon": "dashboard", "permission": "logistics.view_deliveryroute"}
                ]
            },
            {
                "seccion": _("Vehicles & Drivers"),
                "items": [
                    {"label": _("Vehicles"), "url": "logistics:vehicle_list", "icon": "local_shipping", "permission": "logistics.view_vehicle"},
                    {"label": _("Drivers"), "url": "logistics:driver_list", "icon": "person", "permission": "logistics.view_driver"}
                ]
            },
            {
                "seccion": _("Routes & Deliveries"),
                "items": [
                    {"label": _("Delivery Routes"), "url": "logistics:deliveryroute_list", "icon": "alt_route", "permission": "logistics.view_deliveryroute"},
                    {"label": _("Delivery Stops"), "url": "logistics:deliverystop_list", "icon": "place", "permission": "logistics.view_deliverystop"},
                    {"label": _("Delivery Events"), "url": "logistics:deliveryevent_list", "icon": "event", "permission": "logistics.view_deliveryevent"}
                ]
            },
            {
                "seccion": _("Tracking & Geofences"),
                "items": [
                    {"label": _("Real-Time Tracking"), "url": "logistics:tracking_realtime", "icon": "gps_fixed", "permission": "logistics.view_deliveryroute"},
                    {"label": _("Geofences"), "url": "logistics:geofence_add", "icon": "my_location", "permission": "logistics.view_deliveryroute"}
                ]
            }
        ]
    },
    {
        "id": "tiendanube_administranet",
        "nombre": _("Tiendanube-AdministraNET"),
        "permiso": "tiendanube_administranet.view_tiendanubeconfig",
        "url": "tiendanube_administranet:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
            <path stroke-linecap='round' stroke-linejoin='round' d='M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1'/>
        </svg>""",
        "orden": 16,
        "color": "purple",
        "submenus": [
            {
                "seccion": _("Status"),
                "items": [
                    {"label": _("Status"), "url": "tiendanube_administranet:dashboard", "icon": "monitor_heart", "permission": "tiendanube_administranet.view_tiendanubeconfig"},
                    {"label": _("Tiendanube Configuration"), "url": "tiendanube_administranet:tiendanube_config_list", "icon": "settings", "permission": "tiendanube_administranet.view_tiendanubeconfig"},
                    {"label": _("AdministraNET Configuration"), "url": "tiendanube_administranet:adminet_config", "icon": "storage", "permission": "tiendanube_administranet.view_administranetconfig"},
                ]
            },
            {
                "seccion": _("Mappings"),
                "items": [
                    {"label": _("Customer Mappings"), "url": "tiendanube_administranet:customer_mapping_list", "icon": "people", "permission": "tiendanube_administranet.view_customermapping"},
                    {"label": _("Product Mappings"), "url": "tiendanube_administranet:product_list", "icon": "inventory", "permission": "tiendanube_administranet.view_productmapping"},
                    {"label": _("Order Mappings"), "url": "tiendanube_administranet:order_mapping_list", "icon": "receipt", "permission": "tiendanube_administranet.view_ordermapping"},
                ]
            },
            {
                "seccion": _("Synchronization"),
                "items": [
                    {"label": _("Auto Sync Config"), "url": "tiendanube_administranet:auto_sync_config", "icon": "settings_suggest", "permission": "tiendanube_administranet.change_tiendanubeconfig"},
                    {"label": _("Manual Sync"), "url": "tiendanube_administranet:manual_sync", "icon": "sync", "permission": "tiendanube_administranet.run_sync"},
                    {"label": _("Sync History"), "url": "tiendanube_administranet:sync_history", "icon": "history", "permission": "tiendanube_administranet.view_synclog"},
                    {"label": _("Webhook Configurations"), "url": "tiendanube_administranet:webhook_config_list", "icon": "webhook", "permission": "tiendanube_administranet.view_webhookconfig"},
                    {"label": _("Webhook Events"), "url": "tiendanube_administranet:webhook_event_list", "icon": "notifications", "permission": "tiendanube_administranet.view_webhookevent"},
                ]
            }
        ]
    },
    {
        "id": "reports_ai",
        "nombre": _("Reports AI"),
        "permiso": "reports_ai.view_reports",
        "url": "reports_ai:dashboard",
        "icono_svg": """<svg class='h-6 w-6 gradient-icon mb-1' fill='none' stroke='currentColor' stroke-width='2' viewBox='0 0 24 24'>
            <path stroke-linecap='round' stroke-linejoin='round' d='M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z'/>
        </svg>""",
        "orden": 90,
        "color": "purple",
        "submenus": [
            {
                "seccion": _("Main"),
                "items": [
                    {"label": _("Dashboard"), "url": "reports_ai:dashboard", "icon": "dashboard", "permission": "reports_ai.view_reports"},
                    {"label": _("AI Assistant (Chat)"), "url": "reports_ai:ai_assistant", "icon": "chat_bubble", "permission": "reports_ai.generate_reports"},
                    {"label": _("Generate Report (Old)"), "url": "reports_ai:generate_report", "icon": "description", "permission": "reports_ai.generate_reports"},
                    {"label": _("Report History"), "url": "reports_ai:report_history", "icon": "history", "permission": "reports_ai.view_reports"},
                ]
            },
            {
                "seccion": _("AI Agents"),
                "items": [
                    {"label": _("Agent Metrics"), "url": "reports_ai:agent_metrics", "icon": "smart_toy", "permission": "reports_ai.view_agent_metrics"},
                ]
            },
                    {
                        "seccion": _("Data Management"),
                        "items": [
                            {"label": _("Functional Catalog"), "url": "reports_ai:catalog_list", "icon": "menu_book", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("New Catalog Entry"), "url": "reports_ai:catalog_create", "icon": "playlist_add", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("Business Rules"), "url": "reports_ai:business_rules_list", "icon": "rule", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("Create Rule"), "url": "reports_ai:business_rule_create", "icon": "add", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("Import from VB6"), "url": "reports_ai:business_rule_import", "icon": "upload", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("Glossary"), "url": "reports_ai:glossary_list", "icon": "spellcheck", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("Create Term"), "url": "reports_ai:glossary_term_create", "icon": "add_circle", "permission": "reports_ai.manage_business_rules"},
                        ]
                    },
                    {
                        "seccion": _("AI Training"),
                        "items": [
                            {"label": _("Train Logic Interpreter"), "url": "reports_ai:logic_interpreter_training", "icon": "psychology", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("Train Data Analyst"), "url": "reports_ai:data_analyst_training", "icon": "smart_toy", "permission": "reports_ai.manage_business_rules"},
                            {"label": _("Quality Dashboard"), "url": "reports_ai:quality_dashboard", "icon": "insights", "permission": "reports_ai.view_agent_metrics"},
                            {"label": _("Query Corrections"), "url": "reports_ai:corrections_list", "icon": "build", "permission": "reports_ai.manage_business_rules"},
                        ]
                    },
            {
                "seccion": _("API & Webhooks"),
                "items": [
                    {"label": _("API Documentation"), "url": "reports_ai:dashboard", "icon": "code", "permission": "reports_ai.access_webhooks"},
                    {"label": _("Health Check"), "url": "reports_ai:webhook_health", "icon": "monitor_heart", "permission": "reports_ai.access_webhooks"},
                ]
            },
            {
                "seccion": _("Configuration"),
                "items": [
                    {"label": _("Settings"), "url": "reports_ai:config", "icon": "settings", "permission": "reports_ai.configure_reports_ai"},
                ]
            }
        ]
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

def obtener_submenus_por_app(app_id: str, permisos_usuario: Set[str], request=None) -> List[Dict[str, Any]]:
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
                    
                    # Mapeo de URLs hardcodeadas para evitar problemas de resolución
                    url_mapping = {
                        'sales:dashboard': '/sales/',
                        'sales:client_list': '/sales/clients/',
                        'sales:client_create': '/sales/clients/create/',
                        'sales:tpv_main': '/sales/tpv/',
                        'sales:sales_order_list': '/sales/orders/',
                        'sales:sales_order_create': '/sales/orders/create/',
                        'sales:invoice_list': '/sales/invoices/',
                        'sales:payment_list': '/sales/payments/',
                        'sales:delivery_list': '/sales/deliveries/',
                        'sales:return_delivery_list': '/sales/returns/',
                        'sales:credit_note_list': '/sales/credit-notes/',
                        'sales:payment_method_list': '/sales/payment-methods/',
                        'sales:payment_processor_list': '/sales/payment-processors/',
                        'sales:reports_dashboard': '/sales/reports/',
                        'sales:price_list_list': '/sales/price-lists/',
                        'sales:payment_term_list': '/sales/payment-terms/',
                        'sales:terminal_list': '/sales/terminals/',
                        'accounting:tax_list': '/accounting/taxes/',
                        'inventory:stock_dashboard': '/inventory/dashboard/',
                        'inventory:product_list': '/inventory/products/',
                        'inventory:warehouse_list': '/inventory/warehouses/',
                        'inventory:location_list': '/inventory/locations/',
                        'inventory:brand_list': '/inventory/brands/',
                        'inventory:category_list': '/inventory/categories/',
                        'inventory:subcategory_list': '/inventory/subcategories/',
                        'inventory:tiendanube_dashboard': '/inventory/tiendanube/',
                        'tiendanube:mapping_list': '/tiendanube/mappings/',
                        'tiendanube:order_mapping_list': '/tiendanube/orders/',
                        'tiendanube:logs_list': '/tiendanube/logs/',
                        'tiendanube:cond_venta_map_list': '/tiendanube/adminet/cond_venta_map/',
                        'tiendanube:cliente_map_list': '/tiendanube/adminet/cliente_map/',
                        'tiendanube:adminet_connection': '/tiendanube/adminet/connection/',
                        'tiendanube:dashboard': '/tiendanube/',
                        'tiendanube:config_list': '/tiendanube/config/',
                    }
                    
                    # Usar mapeo hardcodeado si existe, sino intentar reverse
                    if item["url"] in url_mapping:
                        url = url_mapping[item["url"]]
                        print(f"Using hardcoded URL for '{item['url']}': '{url}'")
                    else:
                        # Usar reverse para generar la URL correcta
                        url = reverse(item["url"])
                        print(f"Successfully resolved URL '{item['url']}' to '{url}'")
                    
                    # Reemplazar {empresa_id} en la URL si existe y tenemos request
                    if request and '{empresa_id}' in url:
                        empresa_activa = None
                        if hasattr(request.user, 'empresa_activa') and request.user.empresa_activa:
                            empresa_activa = request.user.empresa_activa
                        elif request.session.get('empresa_activa_id'):
                            try:
                                from core.models import Empresa
                                empresa_activa = Empresa.objects.get(id=request.session['empresa_activa_id'], activa=True)
                            except:
                                pass
                        
                        if empresa_activa:
                            url = url.replace('{empresa_id}', str(empresa_activa.id))
                        else:
                            # Si no hay empresa activa, ocultar el ítem
                            continue
                            
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

def apps_visibles_para_usuario(user: Optional[UsuarioExtendido], request=None) -> List[Dict[str, Any]]:
    """Obtiene las apps visibles para un usuario, ordenadas por prioridad, con sus submenús"""
    from django.urls import reverse
    from django.urls.exceptions import NoReverseMatch
    from core.models import ModuleConfig
    
    if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
        return []

    permisos_usuario = set()
    if isinstance(user, UsuarioExtendido):
        permisos_usuario = user.get_permisos_totales()

    # Obtener módulos activos desde la base de datos
    active_modules = set(ModuleConfig.objects.filter(is_active=True).values_list('name', flat=True))
    
    # Agregar módulos core que siempre deben estar activos
    core_modules = {'core', 'login', 'dashboard'}
    active_modules.update(core_modules)

    apps_filtradas = []
    for app in APPS_MENU:
        app_id = app.get("id")
        
        # REGLA 1: Module Management y Settings siempre visibles para superusuarios
        if app_id in ["module_management", "settings"]:
            if user.is_superuser:
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
        if app.get("superuser_only") and not user.is_superuser:
            continue
            
        # REGLA 4: Verificar permisos (excepto para superusuarios que tienen acceso total)
        if user.is_superuser or "*" in permisos_usuario or app["permiso"] in permisos_usuario:
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
# get_firebase_app()  # Comentado temporalmente para desarrollo

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


def get_user_empresa(request):
    """
    Alias de get_empresa_actual para mantener compatibilidad con código existente
    """
    return get_empresa_actual(request)