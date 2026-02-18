"""
Cifrado simétrico para secretos de configuración.
Clave maestra desde CONFIG_ENCRYPTION_KEY (base64). Nunca loguear valores sensibles.
"""
import base64
import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_fernet():
    """Fernet desde CONFIG_ENCRYPTION_KEY (base64 url-safe, 44 caracteres, ver Fernet.generate_key())."""
    key = getattr(settings, "CONFIG_ENCRYPTION_KEY", None)
    if not key:
        logger.warning("CONFIG_ENCRYPTION_KEY no configurada; secretos no se cifrarán.")
        return None
    if isinstance(key, str):
        key = key.encode("ascii")
    try:
        return Fernet(key)
    except Exception as e:
        logger.warning("CONFIG_ENCRYPTION_KEY inválida: %s", e)
        return None


def encrypt_json(data: dict[str, Any]) -> str:
    """Serializa dict a JSON y cifra. Si no hay clave, devuelve JSON en claro (no recomendado en prod)."""
    raw = json.dumps(data, sort_keys=True).encode("utf-8")
    f = _get_fernet()
    if f:
        return f.encrypt(raw).decode("ascii")
    return base64.b64encode(raw).decode("ascii")


def decrypt_json(payload: str) -> dict[str, Any] | None:
    """Descifra y deserializa. None si falla o payload vacío."""
    if not payload or not payload.strip():
        return None
    f = _get_fernet()
    raw_b64 = payload.encode("ascii")
    try:
        if f:
            raw = f.decrypt(raw_b64)
        else:
            raw = base64.b64decode(raw_b64)
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError) as e:
        logger.debug("decrypt_json failed: %s", e)
        return None


def mask_secret(value: str | None, last_n: int = 4) -> str:
    """Devuelve '****last4' o '****' si valor vacío o muy corto."""
    if not value or not isinstance(value, str):
        return "****"
    v = value.strip()
    if len(v) <= last_n:
        return "****"
    return "****" + v[-last_n:]
