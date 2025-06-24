INVENTORY_SIDEBAR_MENU = {
    "General": [
        {"label": "Dashboard", "url_name": "inventory:stock_dashboard", "icon": "dashboard", "permission": "inventory.ver_dashboard"},
        {"label": "Productos", "url_name": "inventory:product_list", "icon": "inventory", "permission": "inventory.ver_product"},
    ],
    "Estructura": [
        {"label": "Almacenes", "url_name": "inventory:warehouse_list", "icon": "store", "permission": "inventory.ver_almacen"},
        {"label": "Ubicaciones", "url_name": "inventory:location_list", "icon": "fmd_good", "permission": "inventory.ver_location"},
    ],
    "Catálogo": [
        {"label": "Marcas", "url_name": "inventory:brand_list", "icon": "label", "permission": "inventory.view_brand"},
        {"label": "Rubros", "url_name": "inventory:category_list", "icon": "category", "permission": "inventory.view_category"},
        {"label": "Subrubros", "url_name": "inventory:subcategory_list", "icon": "subdirectory_arrow_right", "permission": "inventory.view_subcategory"},
    ],
    "Tienda Nube": [
        {"label": "Dashboard", "url_name": "inventory:tiendanube_dashboard", "icon": "cloud", "permission": "inventory.ver_dashboard_tiendanube"},
    ],
} 