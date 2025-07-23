# -*- coding: utf-8 -*-
"""
Configuración de menú de navegación para el módulo TiendaNube
"""

def get_nav_submenu_items():
    return [
        {'label': 'Dashboard', 'url': '/tiendanube/'},
        {'label': 'Products', 'url': '/tiendanube/products/'},
        {'label': 'Orders', 'url': '/tiendanube/orders/'},
        {'label': 'Settings', 'url': '/tiendanube/settings/'},
    ] 