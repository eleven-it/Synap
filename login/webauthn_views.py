"""
Endpoints JSON WebAuthn bajo /login/api/webauthn/
"""
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from urllib.parse import urlparse

from core.utils.rate_limit import check_rate_limit
from login.services import webauthn_service as svc
from login.services.webauthn_config import (
    get_user_quick_auth_enabled,
    is_webauthn_enabled,
    set_user_quick_auth_enabled,
)

logger = logging.getLogger(__name__)

_RL_WEBAUTHN_MAX = 40
_WEBAUTHN_DISABLED = {"error": "WebAuthn deshabilitado"}


def _disabled_response():
    return JsonResponse(_WEBAUTHN_DISABLED, status=404)


def _require_enabled(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_webauthn_enabled():
            return _disabled_response()
        return view_func(request, *args, **kwargs)

    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


def _session_key(request) -> str:
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _parse_json_body(request) -> dict:
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _session_user(request):
    return request.session.get("user")


def _rate_limit_webauthn(request, *, key_prefix: str):
    return check_rate_limit(
        request,
        key_prefix=key_prefix,
        limit=_RL_WEBAUTHN_MAX,
        period_seconds=300,
        exceeded_body={
            "error": "Demasiados intentos. Espere unos minutos e intente de nuevo.",
        },
    )


@_require_enabled
def preference(request):
    if request.method not in ("GET", "POST"):
        return JsonResponse({"error": "Método no permitido"}, status=405)

    user = _session_user(request)
    if not user:
        return JsonResponse({"error": "Sesión requerida"}, status=401)

    base_empresa = user["base_empresa"]
    id_usuario = user["id_usuario"]

    if request.method == "GET":
        return JsonResponse(
            {"enabled": get_user_quick_auth_enabled(base_empresa, id_usuario)}
        )

    data = _parse_json_body(request)
    raw = data.get("enabled")
    if not isinstance(raw, bool):
        return JsonResponse(
            {"error": "El campo enabled (true/false) es requerido"},
            status=400,
        )
    saved = set_user_quick_auth_enabled(base_empresa, id_usuario, raw)
    return JsonResponse({"enabled": saved})


@require_POST
@_require_enabled
def register_options(request):
    user = _session_user(request)
    if not user:
        return JsonResponse({"error": "Sesión requerida"}, status=401)

    data = _parse_json_body(request)
    device_label = (data.get("device_label") or "").strip()

    try:
        options = svc.generate_register_options(
            session_key=_session_key(request),
            base_empresa=user["base_empresa"],
            id_usuario=user["id_usuario"],
            cod_usuario=user["cod_usuario"],
            nombre_completo=user.get("nombre_completo") or user.get("cod_usuario", ""),
            device_label=device_label,
            request=request,
        )
    except svc.WebAuthnServiceError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    return JsonResponse(options)


@require_POST
@_require_enabled
def register_verify(request):
    rl = _rate_limit_webauthn(request, key_prefix="webauthn_register_verify")
    if rl is not None:
        return rl

    user = _session_user(request)
    if not user:
        return JsonResponse({"error": "Sesión requerida"}, status=401)

    data = _parse_json_body(request)
    credential = data.get("credential") or data
    if not credential or not isinstance(credential, dict):
        return JsonResponse({"error": "Credencial requerida"}, status=400)

    try:
        svc.verify_register(
            session_key=_session_key(request),
            credential_json=credential,
            request=request,
        )
    except svc.WebAuthnServiceError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    return JsonResponse({"success": True})


@require_POST
@_require_enabled
def authenticate_options(request):
    data = _parse_json_body(request)
    base_empresa = (data.get("base_empresa") or "").strip()
    cod_usuario = (data.get("cod_usuario") or "").strip()
    if not base_empresa or not cod_usuario:
        return JsonResponse(
            {"error": "Empresa y usuario son requeridos"},
            status=400,
        )

    try:
        options = svc.generate_authenticate_options(
            session_key=_session_key(request),
            base_empresa=base_empresa,
            cod_usuario=cod_usuario,
            request=request,
        )
    except svc.WebAuthnServiceError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    return JsonResponse(options)


@require_POST
@_require_enabled
def authenticate_verify(request):
    rl = _rate_limit_webauthn(request, key_prefix="webauthn_auth_verify")
    if rl is not None:
        return rl

    data = _parse_json_body(request)
    credential = data.get("credential") or data
    if not credential or not isinstance(credential, dict):
        return JsonResponse({"error": "Credencial requerida"}, status=400)

    try:
        svc.verify_authenticate(
            session_key=_session_key(request),
            credential_json=credential,
            request=request,
        )
    except svc.WebAuthnServiceError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    next_url = request.GET.get("next")
    if next_url and urlparse(next_url).path.startswith("/"):
        return JsonResponse({"redirect": next_url})

    return JsonResponse({"redirect": reverse("core:dashboard")})


@require_GET
@_require_enabled
def credentials_list(request):
    user = _session_user(request)
    if not user:
        return JsonResponse({"error": "Sesión requerida"}, status=401)

    base_empresa = user["base_empresa"]
    id_usuario = user["id_usuario"]
    user_enabled = get_user_quick_auth_enabled(base_empresa, id_usuario)
    items = svc.list_credentials_for_user(base_empresa, id_usuario)
    return JsonResponse(
        {
            "credentials": items,
            "count": len(items),
            "max": getattr(settings, "WEBAUTHN_MAX_CREDENTIALS", 3),
            "user_enabled": user_enabled,
        }
    )


@require_POST
@_require_enabled
def credentials_revoke(request):
    user = _session_user(request)
    if not user:
        return JsonResponse({"error": "Sesión requerida"}, status=401)

    data = _parse_json_body(request)
    base_empresa = user["base_empresa"]
    id_usuario = user["id_usuario"]

    if data.get("all"):
        count = svc.revoke_all_credentials(base_empresa, id_usuario)
        return JsonResponse({"success": True, "revoked": count})

    credential_id = (data.get("credential_id") or "").strip()
    if not credential_id:
        return JsonResponse({"error": "credential_id requerido"}, status=400)

    try:
        ok = svc.revoke_credential(base_empresa, id_usuario, credential_id)
    except svc.WebAuthnServiceError as e:
        return JsonResponse({"error": e.message}, status=e.status)

    if not ok:
        return JsonResponse({"error": "Credencial no encontrada"}, status=404)

    return JsonResponse({"success": True})
