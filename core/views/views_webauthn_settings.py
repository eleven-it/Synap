"""Vistas de configuración global WebAuthn (UI + API guardar)."""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView

from login.services.webauthn_config import (
    is_webauthn_feature_enabled,
    set_webauthn_feature_enabled,
)

_PERMISO_CONFIG = "configuracion.sistema"


class WebAuthnSettingsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Pantalla «Acceso rápido PWA» en System Configuration."""

    template_name = "core/system_config/acceso_rapido_pwa.html"
    permission_required = _PERMISO_CONFIG

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        enabled = is_webauthn_feature_enabled()
        ctx["bootstrap"] = {
            "enabled": enabled,
            "urls": {
                "guardar": reverse("core:api_webauthn_settings_save"),
            },
        }
        return ctx


def _parse_json_body(request) -> dict:
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}
    return {key: request.POST.get(key) for key in request.POST}


@method_decorator(csrf_protect, name="dispatch")
class WebAuthnSettingsAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST guardar flag global → ``{ok, enabled}``."""

    permission_required = _PERMISO_CONFIG
    raise_exception = True

    def post(self, request, *args, **kwargs):
        data = _parse_json_body(request)
        raw = data.get("enabled")
        if isinstance(raw, bool):
            enabled = raw
        else:
            enabled = str(raw or "").strip().lower() in (
                "1",
                "true",
                "on",
                "yes",
                "si",
                "sí",
            )
        try:
            saved = set_webauthn_feature_enabled(enabled)
        except Exception as exc:  # pragma: no cover - defensivo
            return JsonResponse(
                {"ok": False, "error": f"No se pudo guardar: {exc}"},
                status=500,
            )
        return JsonResponse(
            {
                "ok": True,
                "enabled": saved,
                "message": (
                    "Acceso rápido PWA activado."
                    if saved
                    else "Acceso rápido PWA desactivado."
                ),
            }
        )
