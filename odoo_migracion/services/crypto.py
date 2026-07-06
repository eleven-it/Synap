"""Cifrado de secretos (API keys Odoo) derivado de SECRET_KEY de Django."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    if plain is None:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_secret(cipher: str) -> str:
    if not cipher:
        return ""
    try:
        return _fernet().decrypt(cipher.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("No se pudo descifrar el secreto almacenado.") from exc


def mask_secret(value: str, visible_tail: int = 4) -> str:
    if not value:
        return ""
    tail = value[-visible_tail:] if len(value) > visible_tail else value
    return f"{'•' * 12}{tail}"
