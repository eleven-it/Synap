"""
ConfigService: lectura de configuración activa con cache TTL corto.
Webhooks y workers consumen por aquí; no acceden al storage cifrado directamente.
"""
import logging
from functools import lru_cache
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.companies.models import Company
from apps.system_config.crypto_utils import decrypt_json
from apps.system_config.models import (
    BrandingConfig,
    ChannelConfig,
    ConfigStatus,
    IAConfig,
    NotificationsConfig,
    RAGConfig,
    SecurityConfig,
    StorageConfig,
)

logger = logging.getLogger(__name__)

CONFIG_CACHE_PREFIX = "system_config:"
CONFIG_CACHE_TTL = 30  # segundos


def _cache_key(area: str, company_id: int | None) -> str:
    return f"{CONFIG_CACHE_PREFIX}{area}:{company_id or 'global'}"


def invalidate_config_cache(area: str | None = None, company_id: int | None = None):
    """Invalida cache por área (o todas si area es None)."""
    if area:
        key = _cache_key(area, company_id)
        cache.delete(key)
    else:
        # Invalidar todos los keys del prefijo (simple: por áreas conocidas)
        for a in ("channel", "ia", "rag", "storage", "security", "notifications", "branding"):
            cache.delete(_cache_key(a, company_id))
            cache.delete(_cache_key(a, None))


def get_active_channel_config(
    channel_type: str,
    company_id: int | None = None,
) -> dict[str, Any] | None:
    """
    Config activa del canal. Fallback: primero empresa, luego global.
    Devuelve dict con credenciales descifradas para uso interno (adapters).
    """
    cache_key = _cache_key("channel", company_id)
    cached = cache.get(cache_key)
    if cached is not None:
        by_type = cached.get(channel_type)
        return by_type if by_type else None

    qs = ChannelConfig.objects.filter(status=ConfigStatus.ACTIVE)
    # Por empresa
    if company_id:
        row = qs.filter(company_id=company_id, channel_type=channel_type).first()
        if row:
            out = _channel_config_decrypted(row)
            if out:
                _cache_channel(company_id, channel_type, out)
                return out
    # Global
    row = qs.filter(company__isnull=True, channel_type=channel_type).first()
    if row:
        out = _channel_config_decrypted(row)
        if out:
            _cache_channel(None, channel_type, out)
            return out
    return None


def get_first_active_channel_config(channel_type: str) -> tuple[dict[str, Any] | None, int | None]:
    """
    Devuelve la primera config activa del canal (cualquier empresa o global).
    Útil para webhooks donde no se conoce company_id de antemano.
    Returns (config_dict, company_id). company_id es None si la config es global.
    """
    qs = ChannelConfig.objects.filter(status=ConfigStatus.ACTIVE, channel_type=channel_type).order_by("id")
    for row in qs:
        out = _channel_config_decrypted(row)
        if out:
            return out, row.company_id
    return None, None


def _channel_config_decrypted(row: ChannelConfig) -> dict[str, Any] | None:
    if not row.config_encrypted_json:
        return {}
    data = decrypt_json(row.config_encrypted_json)
    if data is None:
        return {}
    data["_config_id"] = row.id
    data["channel_type"] = row.channel_type
    data["_company_id"] = row.company_id
    return data


def _cache_channel(company_id: int | None, channel_type: str, data: dict):
    key = _cache_key("channel", company_id)
    existing = cache.get(key) or {}
    existing[channel_type] = data
    cache.set(key, existing, CONFIG_CACHE_TTL)


def get_active_ia_config(company_id: int | None = None) -> dict[str, Any] | None:
    """Config IA activa. Fallback empresa -> global."""
    key = _cache_key("ia", company_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    qs = IAConfig.objects.filter(status=ConfigStatus.ACTIVE)
    row = None
    if company_id:
        row = qs.filter(company_id=company_id).first()
    if not row:
        row = qs.filter(company__isnull=True).first()
    if not row:
        return None
    out = {
        "provider": row.provider,
        "model": row.model,
        "limits": row.limits_json or {},
        "prompt_version_id": row.prompt_version_id or "",
    }
    if row.api_key_encrypted:
        dec = decrypt_json(row.api_key_encrypted)
        if isinstance(dec, dict) and "api_key" in dec:
            out["api_key"] = dec["api_key"]
        else:
            out["api_key"] = dec if isinstance(dec, str) else ""
    else:
        out["api_key"] = ""
    cache.set(key, out, CONFIG_CACHE_TTL)
    return out


def get_rag_config(company_id: int | None = None) -> dict[str, Any] | None:
    """Config RAG (activa). Fallback empresa -> global."""
    key = _cache_key("rag", company_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    qs = RAGConfig.objects.filter(status=ConfigStatus.ACTIVE)
    row = None
    if company_id:
        row = qs.filter(company_id=company_id).first()
    if not row:
        row = qs.filter(company__isnull=True).first()
    if not row:
        return None
    out = {
        "top_k": row.top_k,
        "sources_enabled": row.sources_enabled_json or [],
        "cache_ttl_seconds": row.cache_ttl_seconds,
    }
    cache.set(key, out, CONFIG_CACHE_TTL)
    return out


def get_storage_config() -> dict[str, Any] | None:
    """Config storage activa (global)."""
    key = _cache_key("storage", None)
    cached = cache.get(key)
    if cached is not None:
        return cached

    row = StorageConfig.objects.filter(status=ConfigStatus.ACTIVE).first()
    if not row:
        return None
    secret = ""
    access_key = ""
    if row.secret_encrypted:
        dec = decrypt_json(row.secret_encrypted)
        if isinstance(dec, dict):
            secret = dec.get("secret") or ""
            access_key = dec.get("access_key") or ""
        elif isinstance(dec, str):
            secret = dec
    out = {
        "endpoint": row.endpoint or "",
        "bucket": row.bucket or "",
        "region": row.region or "us-east-1",
        "force_path_style": row.force_path_style,
        "access_key": access_key,
        "secret": secret,
        "max_size_bytes": row.max_size_bytes,
        "allowed_content_types": row.allowed_content_types_json or [],
        "retention_days": row.retention_days,
    }
    cache.set(key, out, CONFIG_CACHE_TTL)
    return out


def get_security_config() -> dict[str, Any] | None:
    """Config seguridad (global)."""
    key = _cache_key("security", None)
    cached = cache.get(key)
    if cached is not None:
        return cached

    row = SecurityConfig.objects.first()
    if not row:
        return None
    out = {
        "rate_limits": row.rate_limits_json or {},
        "anti_spam_enabled": row.anti_spam_enabled,
        "pii_warning_enabled": row.pii_warning_enabled,
    }
    cache.set(key, out, CONFIG_CACHE_TTL)
    return out


def get_notifications_config() -> dict[str, Any] | None:
    """Config notificaciones (global)."""
    key = _cache_key("notifications", None)
    cached = cache.get(key)
    if cached is not None:
        return cached

    row = NotificationsConfig.objects.first()
    if not row:
        return None
    out = {
        "escalation_emails": row.escalation_emails_json or [],
        "sla_warning_message_template": row.sla_warning_message_template or "",
        "sla_breach_message_template": row.sla_breach_message_template or "",
        "internal_alert_channel": row.internal_alert_channel or "",
    }
    cache.set(key, out, CONFIG_CACHE_TTL)
    return out


def get_branding_config(company_id: int | None = None) -> dict[str, Any] | None:
    """Branding. Fallback empresa -> global."""
    key = _cache_key("branding", company_id)
    cached = cache.get(key)
    if cached is not None:
        return cached

    row = None
    if company_id:
        row = BrandingConfig.objects.filter(company_id=company_id).first()
    if not row:
        row = BrandingConfig.objects.filter(company__isnull=True).first()
    if not row:
        return None
    out = {
        "assistant_name": row.assistant_name or "",
        "welcome_message": row.welcome_message or "",
        "default_language": row.default_language or "es",
    }
    cache.set(key, out, CONFIG_CACHE_TTL)
    return out
