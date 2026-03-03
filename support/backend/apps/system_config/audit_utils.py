"""Registro de eventos de configuración en la auditoría existente."""
from django.conf import settings

from apps.audit.models import AuditEvent, AuditEventType


def log_config_event(
    event_type: str,
    *,
    area: str,
    object_id: int | None = None,
    scope: str = "global",
    company_id: int | None = None,
    actor_id: int | None = None,
    payload: dict | None = None,
):
    """
    Append-only: registra evento config.updated | config.tested | config.activated | config.deactivated.
    company_id opcional (global si no se pasa).
    """
    event_type_map = {
        "config.updated": AuditEventType.CONFIG_UPDATED,
        "config.tested": AuditEventType.CONFIG_TESTED,
        "config.activated": AuditEventType.CONFIG_ACTIVATED,
        "config.deactivated": AuditEventType.CONFIG_DEACTIVATED,
    }
    choice = event_type_map.get(event_type) or event_type
    payload = dict(payload or {}, area=area, scope=scope)
    if object_id is not None:
        payload["object_id"] = object_id
    AuditEvent.objects.create(
        company_id=company_id,
        case=None,
        event_type=choice,
        payload=payload,
        actor_id=actor_id or (getattr(settings, "SYSTEM_USER_ID", None)),
    )
