# -*- coding: utf-8 -*-
"""Vistas — evolución de precios (histórico)."""

from __future__ import annotations

from datetime import date, timedelta

from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from core.decorators import administranet_login_required
from core.utils.permissions import user_has_permission
from ventas.services.precios_articulo_legacy import LISTAS_VALIDAS
from ventas.services.precios_historial import (
    listar_historial_articulo,
    parse_historial_filtros,
    ranking_variaciones_precios,
)
from ventas.services.precios_terminados import (
    listar_marcas_catalogo_precios,
    listar_rubros_catalogo_precios,
    nombres_listas_precio,
    tipo_art_fab_desde_param,
    TIPO_PRODUCTO_TERMINADO,
)
from ventas.views_precios_terminados import _base_empresa

_PERMISO_VER = "ventas.precios_historial.ver"
_PERMISO_EDITAR = "ventas.precios_terminados.editar"


def _puede_ver_historial(request) -> bool:
    if "user" not in request.session:
        return False
    user = getattr(request, "user", None)
    return user_has_permission(user, _PERMISO_VER) or user_has_permission(user, _PERMISO_EDITAR)


def _requiere_historial(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if "user" not in request.session:
            return redirect("login:login")
        if not _puede_ver_historial(request):
            messages.error(request, "No tiene permiso para consultar el histórico de precios.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped


@_requiere_historial
def evolucion_precios_view(request):
    base_empresa = _base_empresa(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    filtros = parse_historial_filtros(request.GET)
    if not filtros.fecha_desde and not filtros.fecha_hasta:
        filtros.fecha_hasta = date.today()
        filtros.fecha_desde = filtros.fecha_hasta - timedelta(days=90)

    resultado = ranking_variaciones_precios(base_empresa, filtros)
    listas_nombres = nombres_listas_precio()
    tipo = TIPO_PRODUCTO_TERMINADO

    context = {
        "filtros": filtros,
        "filas": resultado.get("filas") or [],
        "totals": resultado.get("totals") or {},
        "fecha_desde": filtros.fecha_desde,
        "fecha_hasta": filtros.fecha_hasta,
        "listas_nombres": listas_nombres,
        "lista_label": listas_nombres.get(filtros.lista, f"Lista {filtros.lista}"),
        "marcas_catalogo": listar_marcas_catalogo_precios(base_empresa, tipo),
        "rubros_catalogo": listar_rubros_catalogo_precios(base_empresa, tipo),
        "marcas_incluidos": filtros.marcas_incluidos,
        "rubros_incluidos": filtros.rubros_incluidos,
        "solo_synap": filtros.solo_synap,
        "url_precios_terminados": reverse("ventas:precios_terminados"),
    }
    return render(request, "ventas/evolucion_precios.html", context)


@require_GET
@administranet_login_required
def api_precios_historial_articulo(request, id_articulo: int):
    if not _puede_ver_historial(request):
        return JsonResponse({"ok": False, "error": "sin_permiso"}, status=403)

    base_empresa = _base_empresa(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "sin_empresa"}, status=400)

    lista = 1
    try:
        lista = int(request.GET.get("lista") or 1)
    except (TypeError, ValueError):
        lista = 1
    if lista not in LISTAS_VALIDAS:
        lista = 1

    from core.utils.administranet_types import to_date_or_none

    fd = to_date_or_none(request.GET.get("fecha_desde"))
    fh = to_date_or_none(request.GET.get("fecha_hasta"))

    data = listar_historial_articulo(
        base_empresa,
        id_articulo,
        lista=lista,
        fecha_desde=fd,
        fecha_hasta=fh,
    )
    if data.get("error"):
        return JsonResponse({"ok": False, **data}, status=400)
    return JsonResponse({"ok": True, **data})
