"""
Configuración de permisos para la app Clover
Sigue la estructura definida en core.constantes_permisos
"""

# Permisos para dispositivos Clover
CLOVER_DEVICE_VIEW = 'clover.view_cloverdevice'
CLOVER_DEVICE_CREATE = 'clover.add_cloverdevice'
CLOVER_DEVICE_UPDATE = 'clover.change_cloverdevice'
CLOVER_DEVICE_DELETE = 'clover.delete_cloverdevice'

# Permisos para transacciones Clover
CLOVER_TRANSACTION_VIEW = 'clover.view_clovertransaction'
CLOVER_TRANSACTION_CREATE = 'clover.add_clovertransaction'
CLOVER_TRANSACTION_UPDATE = 'clover.change_clovertransaction'
CLOVER_TRANSACTION_DELETE = 'clover.delete_clovertransaction'

# Permisos para configuración Clover
CLOVER_CONFIG_VIEW = 'clover.view_cloverconfig'
CLOVER_CONFIG_CREATE = 'clover.add_cloverconfig'
CLOVER_CONFIG_UPDATE = 'clover.change_cloverconfig'
CLOVER_CONFIG_DELETE = 'clover.delete_cloverconfig'

# Permisos para webhooks Clover
CLOVER_WEBHOOK_VIEW = 'clover.view_cloverwebhook'
CLOVER_WEBHOOK_CREATE = 'clover.add_cloverwebhook'
CLOVER_WEBHOOK_UPDATE = 'clover.change_cloverwebhook'
CLOVER_WEBHOOK_DELETE = 'clover.delete_cloverwebhook'

# Grupos de permisos
CLOVER_PERMISSIONS = {
    'clover_admin': {
        'name': 'Clover Administrator',
        'description': 'Full access to all Clover functionality',
        'permissions': [
            CLOVER_DEVICE_VIEW, CLOVER_DEVICE_CREATE, CLOVER_DEVICE_UPDATE, CLOVER_DEVICE_DELETE,
            CLOVER_TRANSACTION_VIEW, CLOVER_TRANSACTION_CREATE, CLOVER_TRANSACTION_UPDATE, CLOVER_TRANSACTION_DELETE,
            CLOVER_CONFIG_VIEW, CLOVER_CONFIG_CREATE, CLOVER_CONFIG_UPDATE, CLOVER_CONFIG_DELETE,
            CLOVER_WEBHOOK_VIEW, CLOVER_WEBHOOK_CREATE, CLOVER_WEBHOOK_UPDATE, CLOVER_WEBHOOK_DELETE,
        ]
    },
    'clover_manager': {
        'name': 'Clover Manager',
        'description': 'Manage Clover devices and view transactions',
        'permissions': [
            CLOVER_DEVICE_VIEW, CLOVER_DEVICE_CREATE, CLOVER_DEVICE_UPDATE,
            CLOVER_TRANSACTION_VIEW, CLOVER_TRANSACTION_UPDATE,
            CLOVER_CONFIG_VIEW, CLOVER_CONFIG_UPDATE,
            CLOVER_WEBHOOK_VIEW, CLOVER_WEBHOOK_UPDATE,
        ]
    },
    'clover_operator': {
        'name': 'Clover Operator',
        'description': 'Operate Clover devices and view transactions',
        'permissions': [
            CLOVER_DEVICE_VIEW,
            CLOVER_TRANSACTION_VIEW, CLOVER_TRANSACTION_CREATE,
            CLOVER_CONFIG_VIEW,
            CLOVER_WEBHOOK_VIEW,
        ]
    },
    'clover_viewer': {
        'name': 'Clover Viewer',
        'description': 'View-only access to Clover data',
        'permissions': [
            CLOVER_DEVICE_VIEW,
            CLOVER_TRANSACTION_VIEW,
            CLOVER_CONFIG_VIEW,
            CLOVER_WEBHOOK_VIEW,
        ]
    }
}

# Permisos requeridos para funcionalidades específicas
CLOVER_FUNCTIONALITY_PERMISSIONS = {
    'device_management': [
        CLOVER_DEVICE_VIEW, CLOVER_DEVICE_CREATE, CLOVER_DEVICE_UPDATE, CLOVER_DEVICE_DELETE
    ],
    'transaction_processing': [
        CLOVER_TRANSACTION_VIEW, CLOVER_TRANSACTION_CREATE, CLOVER_TRANSACTION_UPDATE
    ],
    'configuration_management': [
        CLOVER_CONFIG_VIEW, CLOVER_CONFIG_CREATE, CLOVER_CONFIG_UPDATE, CLOVER_CONFIG_DELETE
    ],
    'webhook_management': [
        CLOVER_WEBHOOK_VIEW, CLOVER_WEBHOOK_CREATE, CLOVER_WEBHOOK_UPDATE, CLOVER_WEBHOOK_DELETE
    ],
    'reporting': [
        CLOVER_TRANSACTION_VIEW, CLOVER_DEVICE_VIEW
    ]
} 