"""Configuración del módulo para Module Management."""

SETTINGS_SCHEMA = {
    "odoo_migracion": {
        "batch_size": {
            "type": "integer",
            "default": 100,
            "label": "Tamaño de lote",
            "help_text": "Registros por lote en jobs de migración.",
        },
        "api_key_alert_days": {
            "type": "integer",
            "default": 7,
            "label": "Alerta vencimiento API key (días)",
        },
    }
}
