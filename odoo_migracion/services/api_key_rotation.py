"""Rotación de API keys Odoo vía JSON-2."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, Optional, TYPE_CHECKING

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from odoo_migracion.services.odoo_client import OdooApiError, OdooJson2Client

if TYPE_CHECKING:
    from odoo_migracion.models import OdooConnection

logger = logging.getLogger(__name__)


def _default_expiration(days: int = 90) -> str:
    """Odoo 19 limita duración; usamos 90 días por defecto (< 3 meses)."""
    return (date.today() + timedelta(days=days)).isoformat()


def rotate_api_key(
    connection: "OdooConnection",
    *,
    name: Optional[str] = None,
    expiration_date: Optional[str] = None,
    revoke_previous: bool = True,
) -> Dict[str, Any]:
    """
    Genera una nueva API key en Odoo, la persiste cifrada y opcionalmente revoca la anterior.

    Requiere en Odoo: base.enable_programmatic_api_keys = True y permisos de administración.
    """
    old_key = connection.get_api_key()
    if not old_key:
        raise OdooApiError(_("La conexión no tiene API key actual para rotar."))

    client = OdooJson2Client(connection)
    label = name or f"Synap migración {timezone.now().strftime('%d/%m/%Y %H:%M')}"
    exp = expiration_date or _default_expiration()

    new_key = client.call(
        "res.users.apikeys",
        "generate",
        {
            "key": old_key,
            "scope": None,
            "name": label,
            "expiration_date": exp,
        },
    )
    if not new_key or not isinstance(new_key, str):
        raise OdooApiError(_("Odoo no devolvió una API key válida al generar."))

    # Probar la nueva clave antes de persistir revocación
    probe = OdooJson2Client(connection)
    probe.api_key = new_key
    probe.smoke_test()

    connection.set_api_key(new_key)
    connection.api_key_label = label
    connection.api_key_expires_at = date.fromisoformat(exp)
    connection.last_test_ok_at = timezone.now()
    connection.last_test_message = _("Rotación de API key exitosa.")
    connection.save(
        update_fields=[
            "api_key_encrypted",
            "api_key_label",
            "api_key_expires_at",
            "last_test_ok_at",
            "last_test_message",
            "updated_at",
        ]
    )

    if revoke_previous:
        try:
            client.call("res.users.apikeys", "revoke", {"key": old_key})
        except OdooApiError as exc:
            logger.warning("No se pudo revocar API key anterior: %s", exc)
            return {
                "success": True,
                "warning": str(exc),
                "expires_at": exp,
                "label": label,
            }

    return {"success": True, "expires_at": exp, "label": label}


def test_connection(connection: "OdooConnection") -> Dict[str, Any]:
    client = OdooJson2Client(connection)
    try:
        result = client.smoke_test()
        connection.last_test_ok_at = timezone.now()
        connection.last_test_message = _("Conexión OK.")
        connection.save(update_fields=["last_test_ok_at", "last_test_message", "updated_at"])
        return {"success": True, "detail": result}
    except OdooApiError as exc:
        connection.last_test_message = str(exc)[:500]
        connection.save(update_fields=["last_test_message", "updated_at"])
        return {"success": False, "error": str(exc)}
