"""Configuración del menú lateral para el módulo Reports."""

MENU_CONFIG = {
    "group": "reports",
    "label": "Reports",
    "icon": "stacked_line_chart",
    "entries": [
        {
            "label": "Catálogo",
            "icon": "grid_view",
            "url_name": "reports:catalog",
        },
        {
            "label": "Workspace",
            "icon": "dashboard_customize",
            "url_name": "reports:workspace",
        },
        {
            "label": "Workspace ejecutivo",
            "icon": "connected_tv",
            "url_name": "reports:workspace_tv",
        },
    ],
}


