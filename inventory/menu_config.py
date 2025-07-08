"""
Configuración de menú para el módulo de inventario
"""

MENU_CONFIG = [
    {
        'name': 'inventory',
        'label': 'Inventory',
        'icon': 'fas fa-boxes',
        'permission': 'inventory.view_product',
        'order': 30,
        'children': [
            {
                'name': 'products',
                'label': 'Products',
                'url': 'inventory:product_list',
                'permission': 'inventory.view_product',
                'icon': 'fas fa-box',
                'order': 1
            },
            {
                'name': 'categories',
                'label': 'Categories',
                'url': 'inventory:category_list',
                'permission': 'inventory.view_category',
                'icon': 'fas fa-tags',
                'order': 2
            },
            {
                'name': 'brands',
                'label': 'Brands',
                'url': 'inventory:brand_list',
                'permission': 'inventory.view_brand',
                'icon': 'fas fa-trademark',
                'order': 3
            },
            {
                'name': 'stock',
                'label': 'Stock',
                'url': 'inventory:stock_list',
                'permission': 'inventory.view_stock',
                'icon': 'fas fa-warehouse',
                'order': 4
            },
            {
                'name': 'movements',
                'label': 'Stock Movements',
                'url': 'inventory:movement_list',
                'permission': 'inventory.view_movement',
                'icon': 'fas fa-exchange-alt',
                'order': 5
            },
            {
                'name': 'warehouses',
                'label': 'Warehouses',
                'url': 'inventory:warehouse_list',
                'permission': 'inventory.view_warehouse',
                'icon': 'fas fa-building',
                'order': 6
            },
            {
                'name': 'locations',
                'label': 'Locations',
                'url': 'inventory:location_list',
                'permission': 'inventory.view_location',
                'icon': 'fas fa-map-marker-alt',
                'order': 7
            },
            {
                'name': 'reports',
                'label': 'Reports',
                'icon': 'fas fa-chart-bar',
                'permission': 'inventory.view_report',
                'order': 8,
                'children': [
                    {
                        'name': 'stock_report',
                        'label': 'Stock Report',
                        'url': 'inventory:stock_report',
                        'permission': 'inventory.view_report',
                        'icon': 'fas fa-chart-bar'
                    },
                    {
                        'name': 'movement_report',
                        'label': 'Movement Report',
                        'url': 'inventory:movement_report',
                        'permission': 'inventory.view_report',
                        'icon': 'fas fa-chart-line'
                    },
                    {
                        'name': 'low_stock_report',
                        'label': 'Low Stock Report',
                        'url': 'inventory:low_stock_report',
                        'permission': 'inventory.view_report',
                        'icon': 'fas fa-exclamation-triangle'
                    },
                    {
                        'name': 'product_performance',
                        'label': 'Product Performance',
                        'url': 'inventory:product_performance_report',
                        'permission': 'inventory.view_report',
                        'icon': 'fas fa-chart-pie'
                    }
                ]
            },
            {
                'name': 'configuration',
                'label': 'Configuration',
                'icon': 'fas fa-cog',
                'permission': 'inventory.view_config',
                'order': 9,
                'children': [
                    {
                        'name': 'uom',
                        'label': 'Units of Measure',
                        'url': 'inventory:uom_list',
                        'permission': 'inventory.view_uom',
                        'icon': 'fas fa-ruler'
                    },
                    {
                        'name': 'product_attributes',
                        'label': 'Product Attributes',
                        'url': 'inventory:attribute_list',
                        'permission': 'inventory.view_attribute',
                        'icon': 'fas fa-list-ul'
                    }
                ]
            }
        ]
    }
] 