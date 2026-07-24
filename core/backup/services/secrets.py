"""Cifrado Fernet de credenciales SFTP (derivado de SECRET_KEY)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _build_fernet() -> Fernet:
    secret_key = getattr(settings, "SECRET_KEY", "") or ""
    if not secret_key.strip():
        raise ImproperlyConfigured(
            "SECRET_KEY es obligatorio para cifrar credenciales de backup."
        )
    digest = hashlib.sha256(f"{secret_key}:synap-backup-sftp".encode("utf-8")).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_secret(raw_value: str) -> str:
    if not raw_value:
        return ""
    return _build_fernet().encrypt(raw_value.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    try:
        return _build_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ImproperlyConfigured(
            "No se pudo descifrar la contraseña SFTP de backup."
        ) from exc
