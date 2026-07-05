"""
Lectura de flags de escritura del módulo ecom (ModuleConfig + settings Django).
"""

from __future__ import annotations

from django.conf import settings

from core.module_registry import MODULE_CONFIGS


def _defaults() -> dict:
    return dict(MODULE_CONFIGS.get("ecom", {}).get("settings") or {})


def get_ecom_setting(key: str, default=None):
    """Valor efectivo de un setting del módulo ecom."""
    env_overrides = {
        "fe_write_enabled": "MAYORISTAPP_FE_WRITE_ENABLED",
        "cobranzas_write_enabled": "MAYORISTAPP_RECIBO_WRITE_ENABLED",
    }
    env_key = env_overrides.get(key)
    if env_key and hasattr(settings, env_key):
        return bool(getattr(settings, env_key))

    try:
        from core.models.module_config import ModuleConfig

        row = ModuleConfig.objects.filter(name="ecom").only("settings").first()
        if row and isinstance(row.settings, dict) and key in row.settings:
            return row.settings[key]
    except Exception:
        pass

    defs = _defaults()
    if key in defs:
        return defs[key]
    return default


def ecom_fe_write_enabled() -> bool:
    return bool(get_ecom_setting("fe_write_enabled", False))


def ecom_cobranzas_write_enabled() -> bool:
    return bool(get_ecom_setting("cobranzas_write_enabled", False))


def ecom_imputacion_write_enabled() -> bool:
    """Imputar/desimputar: FE o cobranzas habilitadas."""
    return ecom_fe_write_enabled() or ecom_cobranzas_write_enabled()
