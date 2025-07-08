"""
Configuración de menú para el módulo de compras
"""

MENU_CONFIG = [
    {
        'name': 'purchases',
        'label': 'Purchases',
        'icon': 'fas fa-shopping-basket',
        'permission': 'purchases.view_supplier',
        'order': 20,
        'children': [
            {
                'name': 'suppliers',
                'label': 'Suppliers',
                'url': 'purchases:supplier_list',
                'permission': 'purchases.view_supplier',
                'icon': 'fas fa-industry',
                'order': 1
            },
            {
                'name': 'orders',
                'label': 'Purchase Orders',
                'url': 'purchases:order_list',
                'permission': 'purchases.view_order',
                'icon': 'fas fa-file-invoice-dollar',
                'order': 2
            },
            {
                'name': 'receipts',
                'label': 'Receipts',
                'url': 'purchases:receipt_list',
                'permission': 'purchases.view_receipt',
                'icon': 'fas fa-boxes',
                'order': 3
            },
            {
                'name': 'approvals',
                'label': 'Approvals',
                'url': 'purchases:approval_list',
                'permission': 'purchases.approve_order',
                'icon': 'fas fa-check-circle',
                'order': 4
            },
            {
                'name': 'ratings',
                'label': 'Supplier Ratings',
                'url': 'purchases:rating_list',
                'permission': 'purchases.view_rating',
                'icon': 'fas fa-star',
                'order': 5
            },
            {
                'name': 'reports',
                'label': 'Reports',
                'icon': 'fas fa-chart-bar',
                'permission': 'purchases.view_report',
                'order': 6,
                'children': [
                    {
                        'name': 'purchase_summary',
                        'label': 'Purchase Summary',
                        'url': 'purchases:purchase_summary_report',
                        'permission': 'purchases.view_report',
                        'icon': 'fas fa-chart-line'
                    },
                    {
                        'name': 'supplier_analysis',
                        'label': 'Supplier Analysis',
                        'url': 'purchases:supplier_analysis_report',
                        'permission': 'purchases.view_report',
                        'icon': 'fas fa-industry-chart'
                    },
                    {
                        'name': 'spending_analysis',
                        'label': 'Spending Analysis',
                        'url': 'purchases:spending_analysis_report',
                        'permission': 'purchases.view_report',
                        'icon': 'fas fa-money-bill-chart'
                    }
                ]
            },
            {
                'name': 'configuration',
                'label': 'Configuration',
                'icon': 'fas fa-cog',
                'permission': 'purchases.view_config',
                'order': 7,
                'children': [
                    {
                        'name': 'approval_workflows',
                        'label': 'Approval Workflows',
                        'url': 'purchases:workflow_list',
                        'permission': 'purchases.view_workflow',
                        'icon': 'fas fa-project-diagram'
                    },
                    {
                        'name': 'supplier_categories',
                        'label': 'Supplier Categories',
                        'url': 'purchases:category_list',
                        'permission': 'purchases.view_category',
                        'icon': 'fas fa-tags'
                    }
                ]
            }
        ]
    }
] 