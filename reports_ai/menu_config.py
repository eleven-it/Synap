"""
Configuración del menú para Reports AI
Integración con el navbar de Synap
"""
from django.utils.translation import gettext_lazy as _

MENU_CONFIG = [
    {
        'name': 'reports_ai',
        'label': _('Reports AI'),
        'icon': 'fas fa-brain',  # Ícono de cerebro/IA
        'permission': 'reports_ai.view_reports',
        'order': 90,  # Orden en el menú principal
        'children': [
            # Dashboard principal
            {
                'name': 'dashboard',
                'label': _('Dashboard'),
                'url': 'reports_ai:dashboard',
                'permission': 'reports_ai.view_reports',
                'icon': 'fas fa-chart-line',
                'order': 1
            },
            # Generar reportes
            {
                'name': 'generate',
                'label': _('Generate Report'),
                'url': 'reports_ai:dashboard',  # Por ahora usa dashboard
                'permission': 'reports_ai.generate_reports',
                'icon': 'fas fa-plus-circle',
                'order': 2
            },
            # Historial de reportes
            {
                'name': 'history',
                'label': _('Report History'),
                'url': 'reports_ai:dashboard',  # Por ahora usa dashboard
                'permission': 'reports_ai.view_reports',
                'icon': 'fas fa-history',
                'order': 3
            },
            # Métricas de agentes
            {
                'name': 'agent_metrics',
                'label': _('Agent Metrics'),
                'url': 'reports_ai:dashboard',  # Por ahora usa dashboard
                'permission': 'reports_ai.view_agent_metrics',
                'icon': 'fas fa-robot',
                'order': 4
            },
            # Gestión de datos
            {
                'name': 'data_management',
                'label': _('Data Management'),
                'icon': 'fas fa-database',
                'permission': 'reports_ai.manage_business_rules',
                'order': 5,
                'children': [
                    {
                        'name': 'business_rules',
                        'label': _('Business Rules'),
                        'url': 'reports_ai:business_rules_list',
                        'permission': 'reports_ai.manage_business_rules',
                        'icon': 'fas fa-book',
                        'order': 1
                    },
                    {
                        'name': 'business_rules_create',
                        'label': _('Create Rule'),
                        'url': 'reports_ai:business_rule_create',
                        'permission': 'reports_ai.manage_business_rules',
                        'icon': 'fas fa-plus',
                        'order': 2
                    },
                    {
                        'name': 'business_rules_import',
                        'label': _('Import from VB6'),
                        'url': 'reports_ai:business_rule_import',
                        'permission': 'reports_ai.manage_business_rules',
                        'icon': 'fas fa-upload',
                        'order': 3
                    },
                    {
                        'name': 'glossary',
                        'label': _('Glossary'),
                        'url': 'reports_ai:glossary_list',
                        'permission': 'reports_ai.manage_business_rules',
                        'icon': 'fas fa-book-open',
                        'order': 4
                    },
                    {
                        'name': 'glossary_create',
                        'label': _('Create Term'),
                        'url': 'reports_ai:glossary_term_create',
                        'permission': 'reports_ai.manage_business_rules',
                        'icon': 'fas fa-plus',
                        'order': 5
                    }
                ]
            },
            # Webhooks (solo para usuarios con permiso)
            {
                'name': 'webhooks',
                'label': _('Webhooks'),
                'icon': 'fas fa-plug',
                'permission': 'reports_ai.access_webhooks',
                'order': 6,
                'children': [
                    {
                        'name': 'webhook_docs',
                        'label': _('API Documentation'),
                        'url': 'reports_ai:dashboard',
                        'permission': 'reports_ai.access_webhooks',
                        'icon': 'fas fa-file-code'
                    },
                    {
                        'name': 'webhook_health',
                        'label': _('Health Check'),
                        'url': 'reports_ai:webhook_health',
                        'permission': 'reports_ai.access_webhooks',
                        'icon': 'fas fa-heartbeat'
                    }
                ]
            },
            # Configuración
            {
                'name': 'configuration',
                'label': _('Configuration'),
                'url': 'reports_ai:config',
                'permission': 'reports_ai.configure_reports_ai',
                'icon': 'fas fa-cog',
                'order': 7
            }
        ]
    }
]

