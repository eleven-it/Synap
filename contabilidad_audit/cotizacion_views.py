"""Vistas HTML y API JSON — Cotización dólar BCRA."""
from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from core.decorators import administranet_login_required, tiene_permiso
from core.services.cotizacion_service import (
    aceptar,
    historial,
    obtener_vigente,
    registrar_manual,
    sugerir,
)
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

logger = logging.getLogger(__name__)

PERMISO_VER = "contabilidad.cotizacion.ver"
PERMISO_ACEPTAR = "contabilidad.cotizacion.aceptar"


def _usuario_identificador(request) -> str:
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return str(getattr(user, "cod_usuario", None) or getattr(user, "username", "") or "usuario")
    session_user = request.session.get("user", {})
    return str(session_user.get("cod_usuario") or session_user.get("nombre") or "usuario")


def _id_usuario_sesion(request) -> int | None:
    session_user = request.session.get("user", {}) or {}
    return to_int_or_none(session_user.get("id_usuario") or session_user.get("cod_usuario"))


def _base_empresa_sesion(request) -> str | None:
    session_user = request.session.get("user", {}) or {}
    return session_user.get("base_empresa")


def _json_error(mensaje: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"ok": False, "error": mensaje}, status=status)


@administranet_login_required
@tiene_permiso(PERMISO_VER)
def cotizacion_dolar_view(request):
    """Pantalla Synap: vigente, sugerido BCRA, historial."""
    base_empresa = _base_empresa_sesion(request)
    puede_aceptar = False
    user = getattr(request, "user", None)
    if user and hasattr(user, "tiene_permiso"):
        puede_aceptar = user.tiene_permiso(PERMISO_ACEPTAR) or (
            hasattr(user, "is_admin") and user.is_admin()
        )
    if (getattr(user, "cod_usuario", "") or "").lower() == "supervisor":
        puede_aceptar = True

    ctx = {
        "titulo_pagina": "Cotización dólar",
        "base_empresa": base_empresa or "",
        "puede_aceptar": puede_aceptar,
        "permiso_aceptar": PERMISO_ACEPTAR,
        "api_vigente": reverse("contabilidad_audit:cotizacion_api_vigente"),
        "api_sugerencia": reverse("contabilidad_audit:cotizacion_api_sugerencia"),
        "api_aceptar": reverse("contabilidad_audit:cotizacion_api_aceptar"),
        "api_manual": reverse("contabilidad_audit:cotizacion_api_manual"),
        "api_historial": reverse("contabilidad_audit:cotizacion_api_historial"),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
    }
    return render(request, "contabilidad_audit/cotizacion_dolar.html", ctx)


@administranet_login_required
@require_GET
def cotizacion_api_vigente(request):
    if not _permiso_ver(request):
        return _json_error("No tiene permiso para consultar la cotización.", 403)
    base = _base_empresa_sesion(request)
    if not base:
        return _json_error("No se pudo determinar la base de empresa de la sesión.", 400)
    try:
        data = obtener_vigente(base)
        return JsonResponse({"ok": True, **data})
    except Exception as exc:
        logger.exception("cotizacion_api_vigente: %s", exc)
        return _json_error("Error al consultar la cotización vigente.", 500)


@administranet_login_required
@require_GET
def cotizacion_api_sugerencia(request):
    if not _permiso_ver(request):
        return _json_error("No tiene permiso para consultar la cotización.", 403)
    base = _base_empresa_sesion(request)
    if not base:
        return _json_error("No se pudo determinar la base de empresa de la sesión.", 400)
    try:
        data = sugerir(base)
        return JsonResponse({"ok": True, **data})
    except Exception as exc:
        logger.exception("cotizacion_api_sugerencia: %s", exc)
        return _json_error("Error al obtener sugerencia BCRA.", 500)


@administranet_login_required
@require_http_methods(["POST"])
def cotizacion_api_aceptar(request):
    if not _permiso_aceptar(request):
        return _json_error("No tiene permiso para aceptar cotizaciones.", 403)
    base = _base_empresa_sesion(request)
    if not base:
        return _json_error("No se pudo determinar la base de empresa de la sesión.", 400)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Cuerpo JSON inválido.")
    valor = to_decimal_or_none(payload.get("valor"))
    if valor is None or valor <= 0:
        return _json_error("Debe indicar un valor de cotización positivo.")
    observacion = (payload.get("observacion") or "-").strip() or "-"
    try:
        data = aceptar(
            base,
            valor=float(valor),
            origen="bcra_sugerido",
            id_usuario=_id_usuario_sesion(request),
            observacion=observacion,
        )
        return JsonResponse({"ok": True, "mensaje": "Cotización aceptada correctamente.", **data})
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:
        logger.exception("cotizacion_api_aceptar: %s", exc)
        return _json_error("Error al aceptar la cotización.", 500)


@administranet_login_required
@require_http_methods(["POST"])
def cotizacion_api_manual(request):
    if not _permiso_aceptar(request):
        return _json_error("No tiene permiso para registrar cotizaciones manuales.", 403)
    base = _base_empresa_sesion(request)
    if not base:
        return _json_error("No se pudo determinar la base de empresa de la sesión.", 400)
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return _json_error("Cuerpo JSON inválido.")
    valor = to_decimal_or_none(payload.get("valor"))
    if valor is None or valor <= 0:
        return _json_error("Debe indicar un valor de cotización positivo.")
    observacion = (payload.get("observacion") or "-").strip() or "-"
    try:
        data = registrar_manual(
            base,
            valor=float(valor),
            id_usuario=_id_usuario_sesion(request),
            observacion=observacion,
        )
        return JsonResponse({"ok": True, "mensaje": "Cotización manual registrada.", **data})
    except ValueError as exc:
        return _json_error(str(exc))
    except Exception as exc:
        logger.exception("cotizacion_api_manual: %s", exc)
        return _json_error("Error al registrar la cotización manual.", 500)


@administranet_login_required
@require_GET
def cotizacion_api_historial(request):
    if not _permiso_ver(request):
        return _json_error("No tiene permiso para consultar el historial.", 403)
    base = _base_empresa_sesion(request)
    if not base:
        return _json_error("No se pudo determinar la base de empresa de la sesión.", 400)
    limite = to_int_or_none(request.GET.get("limite")) or 30
    try:
        filas = historial(base, limite=limite)
        return JsonResponse({"ok": True, "filas": filas})
    except Exception as exc:
        logger.exception("cotizacion_api_historial: %s", exc)
        return _json_error("Error al consultar el historial.", 500)


def _permiso_ver(request) -> bool:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if hasattr(user, "is_admin") and user.is_admin():
        return True
    if (getattr(user, "cod_usuario", "") or "").lower() == "supervisor":
        return True
    return hasattr(user, "tiene_permiso") and user.tiene_permiso(PERMISO_VER)


def _permiso_aceptar(request) -> bool:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if hasattr(user, "is_admin") and user.is_admin():
        return True
    if (getattr(user, "cod_usuario", "") or "").lower() == "supervisor":
        return True
    return hasattr(user, "tiene_permiso") and user.tiene_permiso(PERMISO_ACEPTAR)
