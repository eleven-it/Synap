"""Configuración ampliada para el módulo Reports."""

from .menu_config import MENU_CONFIG


def get_nav_submenu_items():
    """Retorna items para el navbar dinámico."""
    # Comentario: Reutilizamos la estructura del primer nivel del menú.
    return MENU_CONFIG[0]["children"]


SETTINGS_SCHEMA = {
    "reports": {
        "cache_ttl": {
            "type": "integer",
            "default": 900,
            "label": "Cache TTL (seconds)",
            "help_text": "Default cache time for report payloads.",
        },
        "export_path": {
            "type": "string",
            "default": "reports/exports",
            "label": "Export path",
            "help_text": "Relative media path where exports will be stored.",
        },
    }
}


