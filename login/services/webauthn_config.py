"""
Configuración WebAuthn: feature flag global (SystemConfiguration) y preferencia por usuario.
"""
from __future__ import annotations

from typing import Optional

from core.models import SystemConfiguration

from login.models import WebAuthnUserPreference

_CLAVE_FEATURE = "login.webauthn.unlock_enabled"
_DESCRIPCION_FEATURE = (
    "Activa el desbloqueo rápido WebAuthn en la PWA Synap (Settings → Acceso rápido PWA)."
)


def _normalizar_bool(valor: Optional[str], *, default: bool = False) -> bool:
    if valor is None:
        return default
    v = str(valor).strip().lower()
    if v in ("no", "0", "false", "off", "n"):
        return False
    if v in ("si", "sí", "1", "true", "on", "yes", "y"):
        return True
    return default


def _leer_valor_clave(key: str, default: str = "") -> str:
    obj = (
        SystemConfiguration.objects.filter(key=key, is_active=True).first()
        or SystemConfiguration.objects.filter(key=key).first()
    )
    if obj is None:
        return default
    return str(obj.value or "").strip()


def _guardar_clave(key: str, value: str, *, description: str = "") -> None:
    defaults = {"value": value, "is_active": True}
    if description:
        defaults["description"] = description
    SystemConfiguration.objects.update_or_create(key=key, defaults=defaults)


def is_webauthn_feature_enabled() -> bool:
    """True si el administrador activó WebAuthn en System Configuration."""
    return _normalizar_bool(
        _leer_valor_clave(_CLAVE_FEATURE, "false"),
        default=False,
    )


def set_webauthn_feature_enabled(enabled: bool) -> bool:
    """Persiste el flag global y devuelve el valor guardado."""
    _guardar_clave(
        _CLAVE_FEATURE,
        "true" if enabled else "false",
        description=_DESCRIPCION_FEATURE,
    )
    return is_webauthn_feature_enabled()


def is_webauthn_enabled() -> bool:
    """Alias operativo del flag global (sustituye settings.WEBAUTHN_UNLOCK_ENABLED)."""
    return is_webauthn_feature_enabled()


def get_user_quick_auth_enabled(base_empresa: str, id_usuario: int) -> bool:
    """Preferencia del usuario; default False si no existe registro."""
    pref = WebAuthnUserPreference.objects.filter(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
    ).first()
    if pref is None:
        return False
    return bool(pref.enabled)


def set_user_quick_auth_enabled(
    base_empresa: str,
    id_usuario: int,
    enabled: bool,
) -> bool:
    """Activa o desactiva la autenticación rápida del usuario (no borra passkeys)."""
    pref, _ = WebAuthnUserPreference.objects.update_or_create(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        defaults={"enabled": enabled},
    )
    return bool(pref.enabled)
