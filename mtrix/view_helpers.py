"""Helpers de vistas Mtrix."""

from __future__ import annotations

from django.http import HttpRequest

from mtrix.models import MtrixConfig
from mtrix.services.crypto import decrypt_secret, mask_secret


def base_empresa_sesion(request: HttpRequest) -> str:
    user = request.session.get("user") or {}
    return (user.get("base_empresa") or "").strip()


def get_or_create_config(base_empresa: str) -> MtrixConfig:
    cfg, _ = MtrixConfig.objects.get_or_create(base_empresa=base_empresa)
    return cfg


def sftp_masked(cfg: MtrixConfig) -> str:
    try:
        return mask_secret(decrypt_secret(cfg.sftp_password_encrypted or ""))
    except Exception:
        return ""
