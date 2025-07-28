"""
Configuración de menú para el módulo Tiendanube
"""

MENU_CONFIG = [
    {
        'name': 'tiendanube',
        'label': 'TiendaNube',
        'icon': 'fas fa-store',
        'permission': 'tiendanube.view_integration',
        'order': 20,
        'children': [
            {
                'name': 'synap_integration',
                'label': 'Integración Synap',
                'icon': 'fas fa-link',
                'order': 1,
                'children': [
                    {
                        'name': 'products',
                        'label': 'Products',
                        'url': 'tiendanube:mapping_list',
                        'permission': 'tiendanube.sync_products',
                        'icon': 'fas fa-box',
                        'order': 1
                    },
                    {
                        'name': 'orders',
                        'label': 'Orders',
                        'url': 'tiendanube:order_mapping_list',
                        'permission': 'tiendanube.sync_orders',
                        'icon': 'fas fa-file-invoice',
                        'order': 2
                    },
                    {
                        'name': 'logs',
                        'label': 'Sync Logs',
                        'url': 'tiendanube:logs_list',
                        'permission': 'tiendanube.view_sync_log',
                        'icon': 'fas fa-history',
                        'order': 3
                    },
                ]
            },
            {
                'name': 'adminet_integration',
                'label': 'Integración administraNET',
                'icon': 'fas fa-database',
                'order': 2,
                'children': [
                    {
                        'name': 'cond_venta_map',
                        'label': 'Cond. Venta Tiendanube ↔ Adminet',
                        'url': 'tiendanube:cond_venta_map_list',
                        'permission': 'tiendanube.configure_integration',
                        'icon': 'fas fa-exchange-alt',
                        'order': 1
                    },
                    {
                        'name': 'adminet_connection',
                        'label': 'Conexión Adminet (MySQL)',
                        'url': 'tiendanube:adminet_connection',
                        'permission': 'tiendanube.configure_integration',
                        'icon': 'fas fa-database',
                        'order': 2
                    },
                ]
            },
            {
                'name': 'dashboard',
                'label': 'Dashboard',
                'url': 'tiendanube:dashboard',
                'permission': 'tiendanube.view_integration',
                'icon': 'fas fa-tachometer-alt',
                'order': 99
            },
            {
                'name': 'settings',
                'label': 'Settings',
                'url': 'tiendanube:config_list',
                'permission': 'tiendanube.configure_integration',
                'icon': 'fas fa-cog',
                'order': 100
            },
        ]
    }
] 