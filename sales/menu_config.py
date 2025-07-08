"""
Configuración de menú para el módulo de ventas
"""

MENU_CONFIG = [
    {
        'name': 'sales',
        'label': 'Sales',
        'icon': 'fas fa-shopping-cart',
        'permission': 'sales.view_client',
        'order': 10,
        'children': [
            {
                'name': 'clients',
                'label': 'Clients',
                'url': 'sales:client_list',
                'permission': 'sales.view_client',
                'icon': 'fas fa-users',
                'order': 1
            },
            {
                'name': 'orders',
                'label': 'Orders',
                'url': 'sales:order_list',
                'permission': 'sales.view_order',
                'icon': 'fas fa-file-invoice',
                'order': 2
            },
            {
                'name': 'invoices',
                'label': 'Invoices',
                'url': 'sales:invoice_list',
                'permission': 'sales.view_invoice',
                'icon': 'fas fa-receipt',
                'order': 3
            },
            {
                'name': 'payments',
                'label': 'Payments',
                'url': 'sales:payment_list',
                'permission': 'sales.view_payment',
                'icon': 'fas fa-credit-card',
                'order': 4
            },
            {
                'name': 'deliveries',
                'label': 'Deliveries',
                'url': 'sales:delivery_list',
                'permission': 'sales.view_delivery',
                'icon': 'fas fa-truck',
                'order': 5
            },
            {
                'name': 'credit_notes',
                'label': 'Credit Notes',
                'url': 'sales:credit_note_list',
                'permission': 'sales.view_credit_note',
                'icon': 'fas fa-undo',
                'order': 6
            },
            {
                'name': 'reports',
                'label': 'Reports',
                'icon': 'fas fa-chart-bar',
                'permission': 'sales.view_report',
                'order': 7,
                'children': [
                    {
                        'name': 'sales_summary',
                        'label': 'Sales Summary',
                        'url': 'sales:sales_summary_report',
                        'permission': 'sales.view_report',
                        'icon': 'fas fa-chart-line'
                    },
                    {
                        'name': 'client_analysis',
                        'label': 'Client Analysis',
                        'url': 'sales:client_analysis_report',
                        'permission': 'sales.view_report',
                        'icon': 'fas fa-user-chart'
                    },
                    {
                        'name': 'product_performance',
                        'label': 'Product Performance',
                        'url': 'sales:product_performance_report',
                        'permission': 'sales.view_report',
                        'icon': 'fas fa-box-chart'
                    }
                ]
            },
            {
                'name': 'configuration',
                'label': 'Configuration',
                'icon': 'fas fa-cog',
                'permission': 'sales.view_config',
                'order': 8,
                'children': [
                    {
                        'name': 'price_lists',
                        'label': 'Price Lists',
                        'url': 'sales:price_list_list',
                        'permission': 'sales.view_price_list',
                        'icon': 'fas fa-tags'
                    },
                    {
                        'name': 'payment_terms',
                        'label': 'Payment Terms',
                        'url': 'sales:payment_term_list',
                        'permission': 'sales.view_payment_term',
                        'icon': 'fas fa-calendar-alt'
                    }
                ]
            }
        ]
    }
] 