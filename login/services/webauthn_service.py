"""
Servicio WebAuthn: registro, autenticación (unlock), revocación y fingerprint.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import options_to_json
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from login.administranet_auth import AdministraNETAuth
from login.models import WebAuthnCredential
from login.services.webauthn_config import (
    get_user_quick_auth_enabled,
    is_webauthn_enabled,
)

logger = logging.getLogger(__name__)


class WebAuthnServiceError(Exception):
    """Error de negocio WebAuthn con mensaje en español para el cliente."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def is_webauthn_feature_enabled() -> bool:
    """Reexport del módulo de configuración (compatibilidad de imports)."""
    from login.services.webauthn_config import is_webauthn_feature_enabled as _enabled

    return _enabled()


def user_handle(base_empresa: str, id_usuario: int) -> bytes:
    return f"{base_empresa}:{id_usuario}".encode("utf-8")


def resolve_webauthn_rp(request=None) -> tuple[str, str]:
    """
    Resuelve (rp_id, origin) del contexto de navegación actual.

    WebAuthn exige que rp_id coincida con el hostname de la página. Si el
    cliente entra por IP LAN o un host distinto a SITE_URL, usar settings
    fijos hace fallar create()/get() en el navegador sin llegar a verificar.

    Usa HTTP_HOST del META (sin get_host()) para no depender de ALLOWED_HOSTS
    en el cálculo del RP — el middleware de host ya validó la petición.
    """
    if request is not None:
        host = (request.META.get("HTTP_HOST") or "").strip()
        if not host and hasattr(request, "get_host"):
            try:
                host = (request.get_host() or "").strip()
            except Exception:
                host = ""
        if host:
            hostname = host.split(":")[0].lower()
            forwarded = (request.META.get("HTTP_X_FORWARDED_PROTO") or "").split(",")[0].strip()
            if forwarded:
                scheme = forwarded
            elif getattr(request, "is_secure", lambda: False)():
                scheme = "https"
            else:
                scheme = getattr(request, "scheme", None) or "http"
            return hostname, f"{scheme}://{host}"
    return (
        getattr(settings, "WEBAUTHN_RP_ID", "localhost"),
        getattr(settings, "WEBAUTHN_ORIGIN", "http://localhost"),
    )


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _challenge_cache_key(kind: str, session_key: str) -> str:
    return f"webauthn:{kind}:{session_key}"


def _store_challenge(kind: str, session_key: str, payload: dict) -> None:
    ttl = getattr(settings, "WEBAUTHN_CHALLENGE_TTL", 120)
    cache.set(_challenge_cache_key(kind, session_key), payload, timeout=ttl)


def _pop_challenge(kind: str, session_key: str) -> Optional[dict]:
    key = _challenge_cache_key(kind, session_key)
    payload = cache.get(key)
    if payload is None:
        return None
    cache.delete(key)
    return payload


def _active_credentials_qs(base_empresa: str, id_usuario: int):
    return WebAuthnCredential.objects.filter(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        revoked_at__isnull=True,
    )


def count_active_credentials(base_empresa: str, id_usuario: int) -> int:
    return _active_credentials_qs(base_empresa, id_usuario).count()


def list_credentials_for_user(base_empresa: str, id_usuario: int) -> list[dict]:
    creds = _active_credentials_qs(base_empresa, id_usuario).order_by("-created_at")
    items = []
    for cred in creds:
        items.append(
            {
                "credential_id": _b64url_encode(bytes(cred.credential_id)),
                "device_label": cred.device_label or "Dispositivo",
                "created_at": cred.created_at.strftime("%d/%m/%Y %H:%M"),
                "last_used_at": (
                    cred.last_used_at.strftime("%d/%m/%Y %H:%M")
                    if cred.last_used_at
                    else None
                ),
            }
        )
    return items


def revoke_all_credentials(base_empresa: str, id_usuario: int) -> int:
    now = timezone.now()
    return _active_credentials_qs(base_empresa, id_usuario).update(revoked_at=now)


def revoke_credential(
    base_empresa: str,
    id_usuario: int,
    credential_id_b64: str,
) -> bool:
    try:
        cred_id = _b64url_decode(credential_id_b64)
    except Exception:
        raise WebAuthnServiceError("Identificador de credencial inválido", status=400)
    updated = _active_credentials_qs(base_empresa, id_usuario).filter(
        credential_id=cred_id,
    ).update(revoked_at=timezone.now())
    return updated > 0


def generate_register_options(
    *,
    session_key: str,
    base_empresa: str,
    id_usuario: int,
    cod_usuario: str,
    nombre_completo: str,
    device_label: str = "",
    request=None,
) -> dict:
    if not get_user_quick_auth_enabled(base_empresa, id_usuario):
        raise WebAuthnServiceError(
            "La autenticación rápida está desactivada en tu perfil. "
            "Activála en Ajustes para registrar un dispositivo.",
            status=403,
        )

    max_creds = getattr(settings, "WEBAUTHN_MAX_CREDENTIALS", 3)
    if count_active_credentials(base_empresa, id_usuario) >= max_creds:
        raise WebAuthnServiceError(
            f"Máximo {max_creds} dispositivos registrados. Revocá uno desde Ajustes.",
            status=400,
        )

    exclude = [
        PublicKeyCredentialDescriptor(id=bytes(c.credential_id))
        for c in _active_credentials_qs(base_empresa, id_usuario).only("credential_id")
    ]

    rp_id, origin = resolve_webauthn_rp(request)
    handle = user_handle(base_empresa, id_usuario)
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user_name=f"{base_empresa}:{cod_usuario}",
        user_id=handle,
        user_display_name=nombre_completo or cod_usuario,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=exclude or None,
    )

    challenge_b64 = json.loads(options_to_json(options))["challenge"]
    _store_challenge(
        "reg",
        session_key,
        {
            "challenge": challenge_b64,
            "base_empresa": base_empresa,
            "id_usuario": id_usuario,
            "device_label": (device_label or "").strip()[:128],
            "rp_id": rp_id,
            "origin": origin,
        },
    )
    return json.loads(options_to_json(options))


def verify_register(
    *,
    session_key: str,
    credential_json: dict,
    auth_service: Optional[AdministraNETAuth] = None,
    request=None,
) -> dict:
    stored = _pop_challenge("reg", session_key)
    if not stored:
        raise WebAuthnServiceError(
            "El desafío expiró o ya fue utilizado. Intentá de nuevo.",
            status=400,
        )

    if auth_service is None:
        auth_service = AdministraNETAuth()

    base_empresa = stored["base_empresa"]
    id_usuario = stored["id_usuario"]
    device_label = stored.get("device_label") or "Dispositivo"
    rp_id = stored.get("rp_id") or resolve_webauthn_rp(request)[0]
    origin = stored.get("origin") or resolve_webauthn_rp(request)[1]

    if not get_user_quick_auth_enabled(base_empresa, id_usuario):
        raise WebAuthnServiceError(
            "La autenticación rápida está desactivada en tu perfil.",
            status=403,
        )

    max_creds = getattr(settings, "WEBAUTHN_MAX_CREDENTIALS", 3)
    if count_active_credentials(base_empresa, id_usuario) >= max_creds:
        raise WebAuthnServiceError(
            f"Máximo {max_creds} dispositivos registrados.",
            status=400,
        )

    challenge_bytes = _b64url_decode(stored["challenge"])
    try:
        verified = verify_registration_response(
            credential=credential_json,
            expected_challenge=challenge_bytes,
            expected_rp_id=rp_id,
            expected_origin=origin,
            require_user_verification=True,
        )
    except Exception as e:
        logger.warning("verify_registration_response falló: %s", e)
        raise WebAuthnServiceError(
            "No se pudo registrar el dispositivo. Intentá de nuevo.",
            status=400,
        ) from e

    fingerprint = auth_service.get_password_fingerprint(id_usuario, base_empresa)
    if not fingerprint:
        raise WebAuthnServiceError(
            "No se pudo validar la contraseña del usuario.",
            status=400,
        )

    WebAuthnCredential.objects.create(
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        device_label=device_label or "Dispositivo",
        password_fingerprint=fingerprint,
    )
    return {"success": True}


def generate_authenticate_options(
    *,
    session_key: str,
    base_empresa: str,
    cod_usuario: str,
    auth_service: Optional[AdministraNETAuth] = None,
    request=None,
) -> dict:
    if auth_service is None:
        auth_service = AdministraNETAuth()

    user_data = auth_service.get_user_by_cod(cod_usuario, base_empresa)
    if not user_data:
        raise WebAuthnServiceError(
            "Usuario no encontrado en la empresa seleccionada.",
            status=404,
        )

    id_usuario = user_data["id_usuario"]
    if not get_user_quick_auth_enabled(base_empresa, id_usuario):
        raise WebAuthnServiceError(
            "La autenticación rápida está desactivada para este usuario.",
            status=403,
        )

    creds = list(_active_credentials_qs(base_empresa, id_usuario))
    if not creds:
        raise WebAuthnServiceError(
            "No hay desbloqueo biométrico registrado para este usuario. "
            "Activá la autenticación rápida en Perfil y registrá este dispositivo.",
            status=404,
        )

    rp_id, origin = resolve_webauthn_rp(request)
    allow = [
        PublicKeyCredentialDescriptor(id=bytes(c.credential_id))
        for c in creds
    ]
    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=allow,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    challenge_b64 = json.loads(options_to_json(options))["challenge"]
    _store_challenge(
        "auth",
        session_key,
        {
            "challenge": challenge_b64,
            "base_empresa": base_empresa,
            "id_usuario": id_usuario,
            "rp_id": rp_id,
            "origin": origin,
        },
    )
    return json.loads(options_to_json(options))


def verify_authenticate(
    *,
    session_key: str,
    credential_json: dict,
    request,
    auth_service: Optional[AdministraNETAuth] = None,
) -> dict:
    stored = _pop_challenge("auth", session_key)
    if not stored:
        raise WebAuthnServiceError(
            "El desafío expiró o ya fue utilizado. Intentá de nuevo.",
            status=400,
        )

    if auth_service is None:
        auth_service = AdministraNETAuth()

    base_empresa = stored["base_empresa"]
    id_usuario = stored["id_usuario"]
    rp_id = stored.get("rp_id") or resolve_webauthn_rp(request)[0]
    origin = stored.get("origin") or resolve_webauthn_rp(request)[1]
    if not get_user_quick_auth_enabled(base_empresa, id_usuario):
        raise WebAuthnServiceError(
            "La autenticación rápida está desactivada para este usuario.",
            status=403,
        )

    challenge_bytes = _b64url_decode(stored["challenge"])

    cred_id_raw = credential_json.get("rawId") or credential_json.get("id")
    if isinstance(cred_id_raw, str):
        cred_id_bytes = _b64url_decode(cred_id_raw)
    else:
        raise WebAuthnServiceError("Credencial inválida.", status=400)

    try:
        db_cred = _active_credentials_qs(base_empresa, id_usuario).get(
            credential_id=cred_id_bytes,
        )
    except WebAuthnCredential.DoesNotExist:
        raise WebAuthnServiceError("Credencial no reconocida.", status=401)

    try:
        verified = verify_authentication_response(
            credential=credential_json,
            expected_challenge=challenge_bytes,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=bytes(db_cred.public_key),
            credential_current_sign_count=db_cred.sign_count,
            require_user_verification=True,
        )
    except Exception as e:
        logger.warning("verify_authentication_response falló: %s", e)
        raise WebAuthnServiceError(
            "No se pudo verificar el desbloqueo biométrico.",
            status=401,
        ) from e

    current_fp = auth_service.get_password_fingerprint(id_usuario, base_empresa)
    if not current_fp or current_fp != db_cred.password_fingerprint:
        revoke_all_credentials(base_empresa, id_usuario)
        raise WebAuthnServiceError(
            "La contraseña cambió. Iniciá sesión con contraseña y registrá un nuevo desbloqueo.",
            status=401,
        )

    db_cred.sign_count = verified.new_sign_count
    db_cred.last_used_at = timezone.now()
    db_cred.save(update_fields=["sign_count", "last_used_at"])

    from login.services.session_bootstrap import bootstrap_synap_session

    user_data = auth_service.get_user_by_id(id_usuario, base_empresa)
    if not user_data:
        raise WebAuthnServiceError("Usuario no disponible.", status=401)

    bootstrap_synap_session(
        request,
        user_data,
        base_empresa,
        session_age=settings.WEBAUTHN_SESSION_AGE,
        auth_service=auth_service,
        ip_address=request.META.get("REMOTE_ADDR", "127.0.0.1"),
    )
    return {"success": True}
