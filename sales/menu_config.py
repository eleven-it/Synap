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
            # Dashboard
            {
                'name': 'dashboard',
                'label': 'Dashboard',
                'url': 'sales:dashboard',
                'permission': 'sales.ver',
                'icon': 'fas fa-tachometer-alt',
                'order': 1
            },
            # Gestión de Clientes
            {
                'name': 'clients',
                'label': 'Clients',
                'url': 'sales:client_list',
                'permission': 'sales.view_client',
                'icon': 'fas fa-users',
                'order': 2
            },
            {
                'name': 'create_client',
                'label': 'Create Client',
                'url': 'sales:client_create',
                'permission': 'sales.add_client',
                'icon': 'fas fa-user-plus',
                'order': 3
            },
            # Operaciones de Venta
            {
                'name': 'pos',
                'label': 'Point of Sale (TPV)',
                'url': 'sales:tpv_main',
                'permission': 'sales.view_pos',
                'icon': 'fas fa-cash-register',
                'order': 4
            },
            {
                'name': 'orders',
                'label': 'Orders',
                'url': 'sales:order_list',
                'permission': 'sales.view_order',
                'icon': 'fas fa-file-invoice',
                'order': 5
            },
            {
                'name': 'create_order',
                'label': 'Create Order',
                'url': 'sales:sales_order_create',
                'permission': 'sales.add_order',
                'icon': 'fas fa-plus-circle',
                'order': 6
            },
            # Facturación y Pagos
            {
                'name': 'invoices',
                'label': 'Invoices',
                'url': 'sales:invoice_list',
                'permission': 'sales.view_invoice',
                'icon': 'fas fa-receipt',
                'order': 7
            },
            {
                'name': 'payments',
                'label': 'Payments',
                'url': 'sales:payment_list',
                'permission': 'sales.view_payment',
                'icon': 'fas fa-credit-card',
                'order': 8
            },
            # Logística
            {
                'name': 'deliveries',
                'label': 'Deliveries',
                'url': 'sales:delivery_list',
                'permission': 'sales.view_delivery',
                'icon': 'fas fa-truck',
                'order': 9
            },
            {
                'name': 'returns',
                'label': 'Returns',
                'url': 'sales:return_delivery_list',
                'permission': 'sales.ver_return',
                'icon': 'fas fa-undo',
                'order': 10
            },
            {
                'name': 'credit_notes',
                'label': 'Credit Notes',
                'url': 'sales:credit_note_list',
                'permission': 'sales.view_credit_note',
                'icon': 'fas fa-sticky-note',
                'order': 11
            },
            # Configuración de Pagos
            {
                'name': 'payment_configuration',
                'label': 'Payment Configuration',
                'icon': 'fas fa-cog',
                'permission': 'sales.ver',
                'order': 12,
                'children': [
                    {
                        'name': 'payment_methods',
                        'label': 'Payment Methods',
                        'url': 'sales:payment_method_list',
                        'permission': 'sales.ver',
                        'icon': 'fas fa-credit-card'
                    },
                    {
                        'name': 'payment_processors',
                        'label': 'Payment Processors',
                        'url': 'sales:payment_processor_list',
                        'permission': 'sales.ver',
                        'icon': 'fas fa-cogs'
                    }
                ]
            },
            # Reportes
            {
                'name': 'reports',
                'label': 'Reports',
                'icon': 'fas fa-chart-bar',
                'permission': 'sales.view_report',
                'order': 13,
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
                    },
                    {
                        'name': 'payment_analysis',
                        'label': 'Payment Analysis',
                        'url': 'sales:payment_list',
                        'permission': 'sales.view_report',
                        'icon': 'fas fa-credit-card'
                    }
                ]
            },
            # Configuración General
            {
                'name': 'configuration',
                'label': 'Configuration',
                'icon': 'fas fa-cog',
                'permission': 'sales.view_config',
                'order': 14,
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
                    },
                    {
                        'name': 'tax_configuration',
                        'label': 'Tax Configuration',
                        'url': 'accounting:tax_list',
                        'permission': 'accounting.view_tax',
                        'icon': 'fas fa-percentage'
                    }
                ]
            }
        ]
    }
] 