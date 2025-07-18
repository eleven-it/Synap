"""
Configuración de menú para el módulo MercadoPago
"""

from django.utils.translation import gettext_lazy as _

MENU_CONFIG = [
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