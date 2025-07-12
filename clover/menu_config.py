"""
Configuración del menú para la app Clover
Sigue la estructura definida en core.menu_config
"""

from .permissions import CLOVER_PERMISSIONS

# Configuración del menú principal de Clover
CLOVER_MENU_CONFIG = {
    'id': 'clover_main',
    'name': 'Clover',
    'icon': 'fas fa-credit-card',
    'url': 'clover:device_list',
    'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][0]],  # Solo necesita ver dispositivos
    'order': 6,  # Después de Sales
    'children': [
        {
            'id': 'clover_devices',
            'name': 'Devices',
            'icon': 'fas fa-mobile-alt',
            'url': 'clover:device_list',
            'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][0]],
            'order': 1,
        },
        {
            'id': 'clover_transactions',
            'name': 'Transactions',
            'icon': 'fas fa-receipt',
            'url': 'clover:transaction_list',
            'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][4]],  # Ver transacciones
            'order': 2,
        },
        {
            'id': 'clover_config',
            'name': 'Configuration',
            'icon': 'fas fa-cog',
            'url': 'clover:config_list',
            'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][8]],  # Ver configuración
            'order': 3,
        },
        {
            'id': 'clover_webhooks',
            'name': 'Webhooks',
            'icon': 'fas fa-link',
            'url': 'clover:webhook_list',
            'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][12]],  # Ver webhooks
            'order': 4,
        },
        {
            'id': 'clover_reports',
            'name': 'Reports',
            'icon': 'fas fa-chart-bar',
            'url': 'clover:reports',
            'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][4]],  # Ver transacciones
            'order': 5,
        },
    ]
}

# Configuración de submenús específicos
CLOVER_SUBMENU_CONFIG = {
    'device_management': {
        'id': 'clover_device_management',
        'name': 'Device Management',
        'icon': 'fas fa-tools',
        'children': [
            {
                'id': 'clover_device_list',
                'name': 'All Devices',
                'url': 'clover:device_list',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][0]],
            },
            {
                'id': 'clover_device_create',
                'name': 'Add Device',
                'url': 'clover:device_create',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][1]],
            },
            {
                'id': 'clover_device_status',
                'name': 'Device Status',
                'url': 'clover:device_status',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][0]],
            },
        ]
    },
    'transaction_management': {
        'id': 'clover_transaction_management',
        'name': 'Transaction Management',
        'icon': 'fas fa-exchange-alt',
        'children': [
            {
                'id': 'clover_transaction_list',
                'name': 'All Transactions',
                'url': 'clover:transaction_list',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][4]],
            },
            {
                'id': 'clover_transaction_create',
                'name': 'New Transaction',
                'url': 'clover:transaction_create',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][5]],
            },
            {
                'id': 'clover_transaction_refunds',
                'name': 'Refunds',
                'url': 'clover:refund_list',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][6]],
            },
        ]
    },
    'system_config': {
        'id': 'clover_system_config',
        'name': 'System Configuration',
        'icon': 'fas fa-server',
        'children': [
            {
                'id': 'clover_config_list',
                'name': 'Configuration',
                'url': 'clover:config_list',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][8]],
            },
            {
                'id': 'clover_webhook_list',
                'name': 'Webhooks',
                'url': 'clover:webhook_list',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][12]],
            },
            {
                'id': 'clover_api_settings',
                'name': 'API Settings',
                'url': 'clover:api_settings',
                'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][10]],
            },
        ]
    }
}

# Configuración de breadcrumbs
CLOVER_BREADCRUMB_CONFIG = {
    'clover:device_list': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Devices', 'url': 'clover:device_list'},
    ],
    'clover:device_create': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Devices', 'url': 'clover:device_list'},
        {'name': 'Add Device', 'url': 'clover:device_create'},
    ],
    'clover:device_detail': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Devices', 'url': 'clover:device_list'},
        {'name': 'Device Detail', 'url': None},
    ],
    'clover:device_update': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Devices', 'url': 'clover:device_list'},
        {'name': 'Edit Device', 'url': None},
    ],
    'clover:transaction_list': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Transactions', 'url': 'clover:transaction_list'},
    ],
    'clover:transaction_detail': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Transactions', 'url': 'clover:transaction_list'},
        {'name': 'Transaction Detail', 'url': None},
    ],
    'clover:config_list': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Configuration', 'url': 'clover:config_list'},
    ],
    'clover:webhook_list': [
        {'name': 'Clover', 'url': 'clover:device_list'},
        {'name': 'Webhooks', 'url': 'clover:webhook_list'},
    ],
}

# Configuración de acciones rápidas
CLOVER_QUICK_ACTIONS = [
    {
        'id': 'add_device',
        'name': 'Add Device',
        'icon': 'fas fa-plus',
        'url': 'clover:device_create',
        'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][1]],
        'color': 'green',
    },
    {
        'id': 'view_transactions',
        'name': 'View Transactions',
        'icon': 'fas fa-receipt',
        'url': 'clover:transaction_list',
        'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][4]],
        'color': 'blue',
    },
    {
        'id': 'device_status',
        'name': 'Device Status',
        'icon': 'fas fa-wifi',
        'url': 'clover:device_status',
        'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][0]],
        'color': 'purple',
    },
    {
        'id': 'sync_devices',
        'name': 'Sync Devices',
        'icon': 'fas fa-sync',
        'url': 'clover:sync_devices',
        'permissions': [CLOVER_PERMISSIONS['clover_admin']['permissions'][2]],
        'color': 'orange',
    },
] 