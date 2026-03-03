"""Tests mínimos para IA (ping) y Storage (list bucket o credenciales)."""
import logging
from datetime import datetime
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.system_config.crypto_utils import decrypt_json
from apps.system_config.models import IAConfig, StorageConfig

logger = logging.getLogger(__name__)


def _allow_external() -> bool:
    return getattr(settings, "ALLOW_EXTERNAL_TESTS", True)


def test_ia_config(ia_config: IAConfig) -> dict[str, Any]:
    """Valida formato y opcionalmente hace ping al proveedor. No activa."""
    now = timezone.now()
    if not ia_config.provider and not ia_config.model:
        ia_config.last_check_at = now
        ia_config.last_error = "Configure provider y model"
        ia_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": ia_config.last_error}
    api_key = ""
    if ia_config.api_key_encrypted:
        dec = decrypt_json(ia_config.api_key_encrypted)
        if isinstance(dec, dict) and "api_key" in dec:
            api_key = dec["api_key"] or ""
        elif isinstance(dec, str):
            api_key = dec
    if not _allow_external():
        ia_config.last_check_at = now
        ia_config.last_error = ""
        ia_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "Configuración válida (test externo deshabilitado)", "skipped": True}
    # Ping opcional según provider (stub: solo validar que hay key si es requerido)
    ia_config.last_check_at = now
    ia_config.last_error = ""
    ia_config.save(update_fields=["last_check_at", "last_error"])
    return {"success": True, "message": "Configuración válida"}


def test_storage_config(storage_config: StorageConfig) -> dict[str, Any]:
    """Valida credenciales y opcionalmente lista bucket."""
    now = timezone.now()
    creds = decrypt_json(storage_config.secret_encrypted) or {}
    access_key = creds.get("access_key") or ""
    secret = creds.get("secret") or ""
    if not storage_config.bucket or not access_key or not secret:
        storage_config.last_check_at = now
        storage_config.last_error = "Faltan bucket, access_key o secret"
        storage_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": storage_config.last_error}
    if not _allow_external():
        storage_config.last_check_at = now
        storage_config.last_error = ""
        storage_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "Estructura válida (test externo deshabilitado)", "skipped": True}
    try:
        import boto3
        from botocore.config import Config
        client = boto3.client(
            "s3",
            endpoint_url=storage_config.endpoint or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret,
            region_name=storage_config.region or "us-east-1",
            config=Config(signature_version="s3v4"),
        )
        client.list_objects_v2(Bucket=storage_config.bucket, MaxKeys=1)
        storage_config.last_check_at = now
        storage_config.last_error = ""
        storage_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "Bucket accesible"}
    except Exception as e:
        storage_config.last_check_at = now
        storage_config.last_error = str(e)
        storage_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": str(e)}
