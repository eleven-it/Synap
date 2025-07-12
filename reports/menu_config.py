"""
Configuración de menú para el módulo de Reportes
"""

MENU_CONFIG = [
    {
        'name': 'reports',
        'label': 'Reports',
        'icon': 'fas fa-chart-bar',
        'permission': 'reports.view_report',
        'order': 50,
        'children': [
            {
                'name': 'reports_dashboard',
                'label': 'Dashboard',
                'url': 'reports:dashboard',
                'icon': 'fas fa-tachometer-alt',
                'permission': 'reports.view_report',
                'order': 10
            },
            {
                'name': 'reports_list',
                'label': 'Reports',
                'url': 'reports:report_list',
                'icon': 'fas fa-file-alt',
                'permission': 'reports.view_report',
                'order': 20
            },
            {
                'name': 'reports_builder',
                'label': 'Report Builder',
                'url': 'reports:report_builder',
                'icon': 'fas fa-paint-brush',
                'permission': 'reports.use_builder',
                'order': 30
            },
            {
                'name': 'reports_templates',
                'label': 'Templates',
                'url': 'reports:template_list',
                'icon': 'fas fa-layer-group',
                'permission': 'reports.view_template',
                'order': 40
            },
            {
                'name': 'reports_components',
                'label': 'Components',
                'url': 'reports:component_library',
                'icon': 'fas fa-puzzle-piece',
                'permission': 'reports.view_component',
                'order': 50
            },
            {
                'name': 'reports_schedules',
                'label': 'Schedules',
                'url': 'reports:schedule_list',
                'icon': 'fas fa-clock',
                'permission': 'reports.view_schedule',
                'order': 60
            },
            {
                'name': 'reports_ai',
                'label': 'AI Features',
                'icon': 'fas fa-robot',
                'permission': 'reports.use_ai_features',
                'order': 70,
                'children': [
                    {
                        'name': 'ai_generate_report',
                        'label': 'Generate Report',
                        'url': 'reports:ai_generate',
                        'icon': 'fas fa-magic',
                        'permission': 'reports.use_ai_features',
                        'order': 10
                    },
                    {
                        'name': 'ai_analyze_content',
                        'label': 'Analyze Content',
                        'url': 'reports:ai_analyze',
                        'icon': 'fas fa-brain',
                        'permission': 'reports.use_ai_features',
                        'order': 20
                    },
                    {
                        'name': 'ai_optimize_design',
                        'label': 'Optimize Design',
                        'url': 'reports:ai_optimize',
                        'icon': 'fas fa-palette',
                        'permission': 'reports.use_ai_features',
                        'order': 30
                    }
                ]
            },
            {
                'name': 'reports_export',
                'label': 'Export',
                'icon': 'fas fa-download',
                'permission': 'reports.export_report',
                'order': 80,
                'children': [
                    {
                        'name': 'export_pdf',
                        'label': 'Export to PDF',
                        'url': 'reports:export_pdf',
                        'icon': 'fas fa-file-pdf',
                        'permission': 'reports.export_report',
                        'order': 10
                    },
                    {
                        'name': 'export_pptx',
                        'label': 'Export to PPTX',
                        'url': 'reports:export_pptx',
                        'icon': 'fas fa-file-powerpoint',
                        'permission': 'reports.export_report',
                        'order': 20
                    },
                    {
                        'name': 'export_branding',
                        'label': 'Branding Settings',
                        'url': 'reports:branding_settings',
                        'icon': 'fas fa-palette',
                        'permission': 'reports.manage_branding',
                        'order': 30
                    }
                ]
            },
            {
                'name': 'reports_administration',
                'label': 'Administration',
                'icon': 'fas fa-cog',
                'permission': 'reports.view_report',
                'order': 90,
                'children': [
                    {
                        'name': 'reports_settings',
                        'label': 'Settings',
                        'url': 'reports:settings',
                        'icon': 'fas fa-sliders-h',
                        'permission': 'reports.view_report',
                        'order': 10
                    },
                    {
                        'name': 'reports_analytics',
                        'label': 'Analytics',
                        'url': 'reports:analytics',
                        'icon': 'fas fa-chart-line',
                        'permission': 'reports.view_report',
                        'order': 20
                    },
                    {
                        'name': 'reports_logs',
                        'label': 'System Logs',
                        'url': 'reports:logs',
                        'icon': 'fas fa-list-alt',
                        'permission': 'reports.view_report',
                        'order': 30
                    }
                ]
            }
        ]
    }
]


REPORTS_MENU_CONFIG = {
    'main_menu': {
        'name': 'reports',
        'label': 'Reports',
        'icon': 'fas fa-chart-bar',
        'order': 50,
        'permission': 'reports.view_report',
        'children': [
            {
                'name': 'reports_dashboard',
                'label': 'Dashboard',
                'url': 'reports:dashboard',
                'icon': 'fas fa-tachometer-alt',
                'order': 10,
                'permission': 'reports.view_report',
            },
            {
                'name': 'reports_list',
                'label': 'Reports',
                'url': 'reports:report_list',
                'icon': 'fas fa-file-alt',
                'order': 20,
                'permission': 'reports.view_report',
            },
            {
                'name': 'reports_builder',
                'label': 'Report Builder',
                'url': 'reports:report_builder',
                'icon': 'fas fa-paint-brush',
                'order': 30,
                'permission': 'reports.use_builder',
            },
            {
                'name': 'reports_templates',
                'label': 'Templates',
                'url': 'reports:template_list',
                'icon': 'fas fa-layer-group',
                'order': 40,
                'permission': 'reports.view_template',
            },
            {
                'name': 'reports_components',
                'label': 'Components',
                'url': 'reports:component_library',
                'icon': 'fas fa-puzzle-piece',
                'order': 50,
                'permission': 'reports.view_component',
            },
            {
                'name': 'reports_schedules',
                'label': 'Schedules',
                'url': 'reports:schedule_list',
                'icon': 'fas fa-clock',
                'order': 60,
                'permission': 'reports.view_schedule',
            },
            {
                'name': 'reports_ai',
                'label': 'AI Features',
                'icon': 'fas fa-robot',
                'order': 70,
                'permission': 'reports.use_ai_features',
                'children': [
                    {
                        'name': 'ai_generate_report',
                        'label': 'Generate Report',
                        'url': 'reports:ai_generate',
                        'icon': 'fas fa-magic',
                        'order': 10,
                        'permission': 'reports.use_ai_features',
                    },
                    {
                        'name': 'ai_analyze_content',
                        'label': 'Analyze Content',
                        'url': 'reports:ai_analyze',
                        'icon': 'fas fa-brain',
                        'order': 20,
                        'permission': 'reports.use_ai_features',
                    },
                    {
                        'name': 'ai_optimize_design',
                        'label': 'Optimize Design',
                        'url': 'reports:ai_optimize',
                        'icon': 'fas fa-palette',
                        'order': 30,
                        'permission': 'reports.use_ai_features',
                    },
                ]
            },
            {
                'name': 'reports_export',
                'label': 'Export',
                'icon': 'fas fa-download',
                'order': 80,
                'permission': 'reports.export_report',
                'children': [
                    {
                        'name': 'export_pdf',
                        'label': 'Export to PDF',
                        'url': 'reports:export_pdf',
                        'icon': 'fas fa-file-pdf',
                        'order': 10,
                        'permission': 'reports.export_report',
                    },
                    {
                        'name': 'export_pptx',
                        'label': 'Export to PPTX',
                        'url': 'reports:export_pptx',
                        'icon': 'fas fa-file-powerpoint',
                        'order': 20,
                        'permission': 'reports.export_report',
                    },
                    {
                        'name': 'export_branding',
                        'label': 'Branding Settings',
                        'url': 'reports:branding_settings',
                        'icon': 'fas fa-palette',
                        'order': 30,
                        'permission': 'reports.manage_branding',
                    },
                ]
            },
            {
                'name': 'reports_administration',
                'label': 'Administration',
                'icon': 'fas fa-cog',
                'order': 90,
                'permission': 'reports.view_report',
                'children': [
                    {
                        'name': 'reports_settings',
                        'label': 'Settings',
                        'url': 'reports:settings',
                        'icon': 'fas fa-sliders-h',
                        'order': 10,
                        'permission': 'reports.view_report',
                    },
                    {
                        'name': 'reports_analytics',
                        'label': 'Analytics',
                        'url': 'reports:analytics',
                        'icon': 'fas fa-chart-line',
                        'order': 20,
                        'permission': 'reports.view_report',
                    },
                    {
                        'name': 'reports_logs',
                        'label': 'System Logs',
                        'url': 'reports:logs',
                        'icon': 'fas fa-list-alt',
                        'order': 30,
                        'permission': 'reports.view_report',
                    },
                ]
            },
        ]
    },
    
    'quick_actions': [
        {
            'name': 'create_report',
            'label': 'Create Report',
            'url': 'reports:report_create',
            'icon': 'fas fa-plus',
            'permission': 'reports.add_report',
            'color': 'success',
        },
        {
            'name': 'ai_generate',
            'label': 'AI Generate',
            'url': 'reports:ai_generate',
            'icon': 'fas fa-magic',
            'permission': 'reports.use_ai_features',
            'color': 'primary',
        },
        {
            'name': 'export_report',
            'label': 'Export',
            'url': 'reports:export_pdf',
            'icon': 'fas fa-download',
            'permission': 'reports.export_report',
            'color': 'info',
        },
        {
            'name': 'schedule_report',
            'label': 'Schedule',
            'url': 'reports:schedule_create',
            'icon': 'fas fa-clock',
            'permission': 'reports.add_schedule',
            'color': 'warning',
        },
    ],
    
    'dashboard_widgets': [
        {
            'name': 'reports_overview',
            'label': 'Reports Overview',
            'template': 'reports/widgets/reports_overview.html',
            'permission': 'reports.view_report',
            'size': 'medium',
            'order': 10,
        },
        {
            'name': 'recent_reports',
            'label': 'Recent Reports',
            'template': 'reports/widgets/recent_reports.html',
            'permission': 'reports.view_report',
            'size': 'small',
            'order': 20,
        },
        {
            'name': 'scheduled_reports',
            'label': 'Scheduled Reports',
            'template': 'reports/widgets/scheduled_reports.html',
            'permission': 'reports.view_schedule',
            'size': 'small',
            'order': 30,
        },
        {
            'name': 'ai_insights',
            'label': 'AI Insights',
            'template': 'reports/widgets/ai_insights.html',
            'permission': 'reports.use_ai_features',
            'size': 'medium',
            'order': 40,
        },
    ],
    
    'breadcrumbs': {
        'reports:dashboard': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
        ],
        'reports:report_list': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
            {'label': 'All Reports', 'url': 'reports:report_list'},
        ],
        'reports:report_create': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
            {'label': 'All Reports', 'url': 'reports:report_list'},
            {'label': 'Create Report', 'url': 'reports:report_create'},
        ],
        'reports:report_detail': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
            {'label': 'All Reports', 'url': 'reports:report_list'},
            {'label': 'Report Detail', 'url': 'reports:report_detail'},
        ],
        'reports:report_builder': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
            {'label': 'Report Builder', 'url': 'reports:report_builder'},
        ],
        'reports:template_list': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
            {'label': 'Templates', 'url': 'reports:template_list'},
        ],
        'reports:component_library': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
            {'label': 'Components', 'url': 'reports:component_library'},
        ],
        'reports:schedule_list': [
            {'label': 'Reports', 'url': 'reports:dashboard'},
            {'label': 'Schedules', 'url': 'reports:schedule_list'},
        ],
    },
    
    'notifications': {
        'report_scheduled': {
            'title': 'Report Scheduled',
            'message': 'Report "{report_title}" has been scheduled successfully.',
            'type': 'success',
            'icon': 'fas fa-clock',
        },
        'report_generated': {
            'title': 'Report Generated',
            'message': 'Report "{report_title}" has been generated successfully.',
            'type': 'success',
            'icon': 'fas fa-file-alt',
        },
        'report_exported': {
            'title': 'Report Exported',
            'message': 'Report "{report_title}" has been exported to {format}.',
            'type': 'info',
            'icon': 'fas fa-download',
        },
        'ai_generation_completed': {
            'title': 'AI Generation Completed',
            'message': 'AI has completed generating content for "{report_title}".',
            'type': 'success',
            'icon': 'fas fa-robot',
        },
        'schedule_executed': {
            'title': 'Schedule Executed',
            'message': 'Scheduled report "{report_title}" has been executed.',
            'type': 'info',
            'icon': 'fas fa-check-circle',
        },
        'schedule_failed': {
            'title': 'Schedule Failed',
            'message': 'Scheduled report "{report_title}" failed to execute.',
            'type': 'error',
            'icon': 'fas fa-exclamation-triangle',
        },
    },
} 