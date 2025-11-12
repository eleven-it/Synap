"""Configuración del menú lateral para el módulo Reports."""

MENU_CONFIG = {
    "group": "reports",
    "label": "Reports",
    "icon": "stacked_line_chart",
    "entries": [
        {
            "label": "Catálogo interactivo",
            "icon": "grid_view",
            "url_name": "reports:catalog",
        },
        {
            "label": "Workspace Smart TV",
            "icon": "dashboard_customize",
            "url_name": "reports:workspace",
        },
    ],
}


