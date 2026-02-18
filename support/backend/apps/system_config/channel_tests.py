"""
Acciones de test por canal: Telegram getMe, WhatsApp Graph, Email SMTP/IMAP.
Si ALLOW_EXTERNAL_TESTS=False solo se valida estructura y se devuelve skipped.
"""
import logging
from datetime import datetime
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.system_config.crypto_utils import decrypt_json
from apps.system_config.models import ChannelConfig, ChannelType

logger = logging.getLogger(__name__)


def _allow_external() -> bool:
    return getattr(settings, "ALLOW_EXTERNAL_TESTS", True)


def test_channel_config(channel_config: ChannelConfig) -> dict[str, Any]:
    """
    Ejecuta test según channel_type. Actualiza last_check_at y last_error en el modelo.
    No cambia status a active (eso es activate). Devuelve { "success": bool, "message": str, "skipped": bool? }.
    """
    config = decrypt_json(channel_config.config_encrypted_json) or {}
    now = timezone.now()
    try:
        if channel_config.channel_type == ChannelType.TELEGRAM:
            return _test_telegram(channel_config, config, now)
        if channel_config.channel_type == ChannelType.WHATSAPP:
            return _test_whatsapp(channel_config, config, now)
        if channel_config.channel_type == ChannelType.EMAIL:
            return _test_email(channel_config, config, now)
        channel_config.last_check_at = now
        channel_config.last_error = f"Canal no soportado: {channel_config.channel_type}"
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": channel_config.last_error}
    except Exception as e:
        msg = str(e)
        channel_config.last_check_at = now
        channel_config.last_error = msg
        channel_config.save(update_fields=["last_check_at", "last_error"])
        logger.exception("test_channel_config failed")
        return {"success": False, "message": msg}


def _test_telegram(channel_config: ChannelConfig, config: dict, now: datetime) -> dict[str, Any]:
    token = config.get("token") or config.get("bot_token")
    if not token:
        channel_config.last_check_at = now
        channel_config.last_error = "Falta token de bot"
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": channel_config.last_error}
    if not _allow_external():
        channel_config.last_check_at = now
        channel_config.last_error = ""
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "Estructura válida (test externo deshabilitado)", "skipped": True}
    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/getMe",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = __import__("json").loads(resp.read().decode())
        if data.get("ok"):
            channel_config.last_check_at = now
            channel_config.last_error = ""
            channel_config.save(update_fields=["last_check_at", "last_error"])
            return {"success": True, "message": f"Bot @{data.get('result', {}).get('username', '')} verificado"}
        channel_config.last_check_at = now
        channel_config.last_error = data.get("description", "getMe no ok")
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": channel_config.last_error}
    except Exception as e:
        channel_config.last_check_at = now
        channel_config.last_error = str(e)
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": str(e)}


def _test_whatsapp(channel_config: ChannelConfig, config: dict, now: datetime) -> dict[str, Any]:
    access_token = config.get("access_token")
    phone_number_id = config.get("phone_number_id")
    if not access_token:
        channel_config.last_check_at = now
        channel_config.last_error = "Falta access_token"
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": channel_config.last_error}
    if not _allow_external():
        channel_config.last_check_at = now
        channel_config.last_error = ""
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "Estructura válida (test externo deshabilitado)", "skipped": True}
    try:
        import urllib.request
        url = f"https://graph.facebook.com/v18.0/{phone_number_id or 'me'}?access_token={access_token}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            __import__("json").loads(resp.read().decode())
        channel_config.last_check_at = now
        channel_config.last_error = ""
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "Token y número validados"}
    except Exception as e:
        channel_config.last_check_at = now
        channel_config.last_error = str(e)
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": str(e)}


def _test_email(channel_config: ChannelConfig, config: dict, now: datetime) -> dict[str, Any]:
    smtp_host = config.get("smtp_host")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user")
    smtp_password = config.get("smtp_password")
    if not smtp_host or not smtp_user or not smtp_password:
        channel_config.last_check_at = now
        channel_config.last_error = "Faltan smtp_host, smtp_user o smtp_password"
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": channel_config.last_error}
    if not _allow_external():
        channel_config.last_check_at = now
        channel_config.last_error = ""
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "Estructura válida (test externo deshabilitado)", "skipped": True}
    try:
        import smtplib
        with smtplib.SMTP(smtp_host, int(smtp_port), timeout=10) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_password)
        channel_config.last_check_at = now
        channel_config.last_error = ""
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": True, "message": "SMTP conectado y login correcto"}
    except Exception as e:
        channel_config.last_check_at = now
        channel_config.last_error = str(e)
        channel_config.save(update_fields=["last_check_at", "last_error"])
        return {"success": False, "message": str(e)}
