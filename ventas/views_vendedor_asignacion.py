# -*- coding: utf-8 -*-
"""Vistas asignación vendedor ↔ cliente / marca."""

from __future__ import annotations

import json
from typing import Any

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from core.decorators import tiene_permiso
from ventas.services.vendedor_asignacion_mysql import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    asignar_items_bulk,
    buscar_vendedores_activos,
    listar_items_asignacion,
    listar_resumen_vendedores,
)

_MENSAJES_ERROR = {
    "modo_invalido": "Modo de asignación no válido.",
    "vendedor_requerido": "Seleccioná un vendedor.",
    "filtro_invalido": "Filtro no válido.",
    "sin_items": "No hay ítems seleccionados.",
    "items_no_validos": "Los ítems no son válidos o no están activos.",
    "vendedor_invalido": "El vendedor no existe o está anulado.",
    "json_invalido": "Cuerpo JSON inválido.",
}


def _base_empresa_session(request) -> str:
    session_user = request.session.get("user", {}) or {}
    return (session_user.get("base_empresa") or "").strip()


def _session_user(request) -> dict:
    return request.session.get("user", {}) or {}


def _usuario_puede_editar(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "cod_usuario", None) and str(user.cod_usuario).lower() == "supervisor":
        return True
    fn = getattr(user, "tiene_permiso", None)
    return bool(fn and fn("ventas.editar"))


def _modo_request(request) -> str:
    modo = (request.GET.get("modo") or request.POST.get("modo") or "cliente").strip().lower()
    return modo if modo in ("cliente", "marca") else "cliente"


def _page_size(raw: Any) -> int:
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return max(5, min(n, MAX_PAGE_SIZE))


def _error_json(code: str, status: int = 400) -> JsonResponse:
    return JsonResponse(
        {"ok": False, "error": _MENSAJES_ERROR.get(code, code), "code": code},
        status=status,
    )


@tiene_permiso("ventas.ver")
def vendedor_asignacion_view(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    modo = _modo_request(request)
    if modo not in ("cliente", "marca"):
        modo = "cliente"

    return render(
        request,
        "ventas/vendedor_asignacion.html",
        {
            "base_empresa": base_empresa,
            "modo_inicial": modo,
            "puede_editar": _usuario_puede_editar(request.user),
            "page_size_default": DEFAULT_PAGE_SIZE,
        },
    )


@require_GET
@tiene_permiso("ventas.ver")
def api_vendedor_asignacion_resumen(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return _error_json("sin_base", 400)
    modo = _modo_request(request)
    if modo not in ("cliente", "marca"):
        return _error_json("modo_invalido")
    q = request.GET.get("q", "")
    try:
        ok, err, vendedores, sin_asignar = listar_resumen_vendedores(base_empresa, modo, q=q)
    except ValueError:
        return _error_json("modo_invalido")
    if not ok:
        return JsonResponse({"ok": False, "error": err or "Error al cargar."}, status=500)
    return JsonResponse(
        {
            "ok": True,
            "vendedores": vendedores,
            "sin_asignar": sin_asignar,
        }
    )


@require_GET
@tiene_permiso("ventas.ver")
def api_vendedor_asignacion_items(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return _error_json("sin_base", 400)
    modo = _modo_request(request)
    if modo not in ("cliente", "marca"):
        return _error_json("modo_invalido")

    filtro = (request.GET.get("filtro") or "asignados").strip().lower()
    q = request.GET.get("q", "")
    page = max(1, int(request.GET.get("page", 1) or 1))
    page_size = _page_size(request.GET.get("page_size", DEFAULT_PAGE_SIZE))
    id_vendedor_raw = request.GET.get("id_vendedor")
    id_vendedor = int(id_vendedor_raw) if id_vendedor_raw not in (None, "", "null") else None

    try:
        ok, err, items, total = listar_items_asignacion(
            base_empresa,
            modo,
            id_vendedor=id_vendedor,
            filtro=filtro,
            q=q,
            page=page,
            page_size=page_size,
        )
    except ValueError:
        return _error_json("modo_invalido")
    if not ok:
        code = err if err in _MENSAJES_ERROR else "error"
        return JsonResponse({"ok": False, "error": _MENSAJES_ERROR.get(err, err), "code": code}, status=400)
    total_pages = max(1, (total + page_size - 1) // page_size)
    return JsonResponse(
        {
            "ok": True,
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
    )


@require_GET
@tiene_permiso("ventas.ver")
def api_vendedor_asignacion_vendedores_buscar(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return _error_json("sin_base", 400)
    q = request.GET.get("q", "")
    ok, err, rows = buscar_vendedores_activos(base_empresa, q=q, limit=30)
    if not ok:
        return JsonResponse({"ok": False, "error": err or "Error al buscar."}, status=500)
    return JsonResponse({"ok": True, "results": rows})


@require_POST
@tiene_permiso("ventas.editar")
def api_vendedor_asignacion_asignar(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return _error_json("sin_base", 400)
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_json("json_invalido")

    modo = (body.get("modo") or "cliente").strip().lower()
    if modo not in ("cliente", "marca"):
        return _error_json("modo_invalido")

    ids_raw = body.get("ids") or body.get("ids_item") or []
    if not isinstance(ids_raw, list):
        return _error_json("sin_items")

    id_vendedor = body.get("id_vendedor")
    if id_vendedor in ("", "null"):
        id_vendedor = None

    try:
        ok, err, afectados = asignar_items_bulk(
            base_empresa,
            modo,
            ids_raw,
            id_vendedor,
            sess_user=_session_user(request),
        )
    except ValueError:
        return _error_json("modo_invalido")

    if not ok:
        return JsonResponse(
            {"ok": False, "error": _MENSAJES_ERROR.get(err, err), "code": err},
            status=400,
        )
    return JsonResponse({"ok": True, "afectados": afectados})
