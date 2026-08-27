"""Cifrado Fernet de credenciales SFTP Mtrix (pepper distinto al de backup)."""

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
            "SECRET_KEY es obligatorio para cifrar credenciales SFTP de Mtrix."
        )
    digest = hashlib.sha256(f"{secret_key}:synap-mtrix-sftp".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


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
            "No se pudo descifrar la contraseña SFTP de Mtrix."
        ) from exc


def mask_secret(value: str, visible_tail: int = 4) -> str:
    if not value:
        return ""
    tail = value[-visible_tail:] if len(value) > visible_tail else value
    return f"{'•' * 12}{tail}"
