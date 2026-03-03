"""
Idempotencia: leer clave de request; devolver respuesta almacenada o ejecutar y guardar.
"""
import re
from typing import Any

from django.http import HttpRequest

UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def get_idempotency_key(request: HttpRequest) -> str | None:
    """
    Extrae la clave de idempotencia del request: header Idempotency-Key o body action_uuid.
    Devuelve None si no viene o no es un UUID válido.
    """
    key = request.headers.get("Idempotency-Key") or request.data.get("action_uuid") if hasattr(request, "data") else None
    if isinstance(key, str):
        key = key.strip()
        if key and UUID_PATTERN.match(key):
            return key
    return None


def get_stored_idempotent_response(case_id: int, action_key: str, actor_id: int) -> tuple[int, dict] | None:
    """
    Si existe un registro (case_id, action_key, actor_id), devuelve (status_code, response_payload).
    Si no, devuelve None.
    """
    from apps.audit.models import IdempotencyRecord

    rec = IdempotencyRecord.objects.filter(
        case_id=case_id,
        action_key=action_key,
        actor_id=actor_id,
    ).first()
    if rec:
        return rec.status_code, rec.response_payload
    return None


def store_idempotent_response(
    case_id: int,
    action_key: str,
    actor_id: int,
    status_code: int,
    response_payload: dict[str, Any],
) -> None:
    """Guarda el resultado de una acción para devolverlo en repeticiones."""
    from apps.audit.models import IdempotencyRecord

    IdempotencyRecord.objects.update_or_create(
        case_id=case_id,
        action_key=action_key,
        actor_id=actor_id,
        defaults={"status_code": status_code, "response_payload": response_payload},
    )
