"""Configuración del menú lateral para el módulo Reports."""

MENU_CONFIG = [
    {
        "name": "reports",
        "label": "Reports",
        "icon": "fas fa-chart-line",
        "permission": "reports.ver",
        "order": 9,
        "children": [
            {
                "name": "catalog",
                "label": "Catalog",
                "url": "reports:catalog",
                "permission": "reports.ver",
                "icon": "fas fa-grid",
                "order": 1,
            },
            {
                "name": "operational_dashboards",
                "label": "Operational dashboards",
                "url": "reports:catalog",
                "permission": "reports.view_operational",
                "icon": "fas fa-industry",
                "order": 2,
            },
            {
                "name": "managerial_dashboards",
                "label": "Managerial dashboards",
                "url": "reports:catalog",
                "permission": "reports.view_managerial",
                "icon": "fas fa-briefcase",
                "order": 3,
            },
            {
                "name": "saved_dashboards",
                "label": "Saved dashboards",
                "url": "reports:saved_dashboards",
                "permission": "reports.ver",
                "icon": "fas fa-bookmark",
                "order": 4,
            },
        ],
    }
]


