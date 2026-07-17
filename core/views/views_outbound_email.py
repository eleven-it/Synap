"""Vistas de configuración de correo saliente (UI + APIs guardar/probar)."""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import TemplateView

from core.services.outbound_email import (
    correo_saliente_configurado,
    guardar_config_correo_saliente,
    leer_config_correo_saliente,
    probar_conexion_correo_saliente,
)

_PERMISO_CONFIG = "configuracion.sistema"


class OutboundEmailConfigView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Pantalla de configuración en ``/configuracion/correo-saliente/``."""

    template_name = "core/system_config/correo_saliente.html"
    permission_required = _PERMISO_CONFIG

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["bootstrap"] = {
            "config": leer_config_correo_saliente(),
            "configurado": correo_saliente_configurado(),
            "urls": {
                "guardar": reverse("core:api_outbound_email_save"),
                "probar": reverse("core:api_outbound_email_test"),
            },
        }
        return ctx


def _parse_json_body(request) -> dict:
    """Lee el cuerpo JSON (o form-data) de la request como dict."""
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}
    return {key: request.POST.get(key) for key in request.POST}


@method_decorator(csrf_protect, name="dispatch")
class OutboundEmailConfigAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST guardar configuración SMTP → ``{ok, ...config}``."""

    permission_required = _PERMISO_CONFIG
    raise_exception = True

    def post(self, request, *args, **kwargs):
        data = _parse_json_body(request)
        try:
            config = guardar_config_correo_saliente(data)
        except Exception as exc:  # pragma: no cover - defensivo
            return JsonResponse(
                {"ok": False, "error": f"No se pudo guardar: {exc}"}, status=500
            )
        return JsonResponse(
            {
                "ok": True,
                "message": "Configuración de correo saliente guardada.",
                "configurado": correo_saliente_configurado(),
                **config,
            }
        )


@method_decorator(csrf_protect, name="dispatch")
class OutboundEmailTestAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """POST probar conexión SMTP (opcional ``to_email``) → ``{ok, message}``."""

    permission_required = _PERMISO_CONFIG
    raise_exception = True

    def post(self, request, *args, **kwargs):
        data = _parse_json_body(request)
        to_email = (data.get("to_email") or "").strip() or None
        try:
            resultado = probar_conexion_correo_saliente(to_email=to_email)
        except Exception as exc:  # pragma: no cover - defensivo
            return JsonResponse(
                {"ok": False, "message": f"No se pudo probar la conexión: {exc}"},
                status=500,
            )
        status = 200 if resultado.get("ok") else 400
        return JsonResponse(resultado, status=status)
