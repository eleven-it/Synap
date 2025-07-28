# -*- coding: utf-8 -*-
"""
Configuración de menú de navegación para el módulo TiendaNube
"""

def get_nav_submenu_items():
    from .menu_config import MENU_CONFIG
    # Retorna los hijos del primer elemento (estructura estándar)
    return MENU_CONFIG[0]['children'] 