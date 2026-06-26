"""
Control sync/webhooks Tienda Nube.

Fuente de verdad operativa: UI / BD (TiendanubeConfig.is_active, auto_sync, WebhookConfig.is_active).
Variables de entorno: kill switch de emergencia (ops/deploy), default True.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from ..models import TiendanubeConfig


def _env_sync_kill_switch() -> bool:
    return getattr(settings, 'TIENDANUBE_SYNC_ENABLED', True)


def _env_webhooks_kill_switch() -> bool:
    return getattr(settings, 'TIENDANUBE_WEBHOOKS_ENABLED', True)


def _resolve_tiendanube_config(
    tiendanube_config: Optional['TiendanubeConfig'],
) -> Optional['TiendanubeConfig']:
    if tiendanube_config is not None:
        return tiendanube_config
    from ..models import TiendanubeConfig
    return TiendanubeConfig.objects.filter(is_active=True).first()


def tiendanube_sync_enabled(
    tiendanube_config: Optional['TiendanubeConfig'] = None,
) -> bool:
    """Sync habilitado: env OK + configuración Tiendanube activa."""
    if not _env_sync_kill_switch():
        return False
    config = _resolve_tiendanube_config(tiendanube_config)
    return config is not None and config.is_active


def tiendanube_sync_disabled_reason(
    tiendanube_config: Optional['TiendanubeConfig'] = None,
) -> Optional[str]:
    if not _env_sync_kill_switch():
        return (
            'Sincronización deshabilitada por kill switch de emergencia '
            '(TIENDANUBE_SYNC_ENABLED=false en entorno)'
        )
    config = _resolve_tiendanube_config(tiendanube_config)
    if config is None:
        return 'Sincronización deshabilitada: no hay configuración Tiendanube activa'
    if not config.is_active:
        return 'Sincronización deshabilitada: configuración Tiendanube inactiva (UI)'
    return None


def tiendanube_auto_sync_enabled(
    tiendanube_config: Optional['TiendanubeConfig'] = None,
) -> bool:
    """Sync programada: sync habilitado + auto_sync en UI."""
    if not tiendanube_sync_enabled(tiendanube_config):
        return False
    config = _resolve_tiendanube_config(tiendanube_config)
    return config is not None and config.auto_sync


def tiendanube_auto_sync_disabled_reason(
    tiendanube_config: Optional['TiendanubeConfig'] = None,
) -> Optional[str]:
    reason = tiendanube_sync_disabled_reason(tiendanube_config)
    if reason:
        return reason
    config = _resolve_tiendanube_config(tiendanube_config)
    if config and not config.auto_sync:
        return (
            'Sincronización automática deshabilitada en configuración Tiendanube (UI)'
        )
    return None


def tiendanube_webhooks_enabled(
    tiendanube_config: Optional['TiendanubeConfig'] = None,
) -> bool:
    """Webhooks habilitados: env OK + configuración Tiendanube activa."""
    if not _env_webhooks_kill_switch():
        return False
    config = _resolve_tiendanube_config(tiendanube_config)
    return config is not None and config.is_active


def tiendanube_webhooks_disabled_reason(
    tiendanube_config: Optional['TiendanubeConfig'] = None,
) -> Optional[str]:
    if not _env_webhooks_kill_switch():
        return (
            'Webhooks deshabilitados por kill switch de emergencia '
            '(TIENDANUBE_WEBHOOKS_ENABLED=false en entorno)'
        )
    config = _resolve_tiendanube_config(tiendanube_config)
    if config is None:
        return 'Webhooks deshabilitados: no hay configuración Tiendanube activa'
    if not config.is_active:
        return 'Webhooks deshabilitados: configuración Tiendanube inactiva (UI)'
    return None
