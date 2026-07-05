"""Configuración ampliada para el módulo E-commerce mayorista."""

SETTINGS_SCHEMA = {
    "ecom": {
        "lp_pdf_max_items": {
            "type": "integer",
            "default": 2500,
            "label": "Máximo ítems PDF lista de precios",
            "help_text": "Umbral de volumen sin imágenes (paridad legacy LP_PDF_MAX_ITEMS).",
        },
        "lp_pdf_max_items_con_imagen": {
            "type": "integer",
            "default": 1800,
            "label": "Máximo ítems PDF con imagen",
            "help_text": "Umbral cuando el export incluye imágenes.",
        },
        "fe_write_enabled": {
            "type": "boolean",
            "default": False,
            "label": "Habilitar escritura FE/imputación",
            "help_text": "Acciones de escritura en relays de factura electrónica (deshabilitado por defecto).",
        },
        "cobranzas_write_enabled": {
            "type": "boolean",
            "default": False,
            "label": "Habilitar escritura cobranzas/recibos",
            "help_text": "Alta de recibos e imputación desde el portal (deshabilitado por defecto).",
        },
    }
}
