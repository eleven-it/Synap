"""
Configuración de menú para el módulo Clover
"""

from django.utils.translation import gettext_lazy as _

MENU_CONFIG = [
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