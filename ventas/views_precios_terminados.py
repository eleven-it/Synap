# -*- coding: utf-8 -*-
"""Vistas — actualización masiva de precios productos terminados."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.decorators import tiene_permiso
from core.utils.permissions import user_has_permission
from ventas.services.precios_terminados import (
    PAGE_SIZE,
    TIPO_PRODUCTO_2DA,
    TIPO_PRODUCTO_TERMINADO,
    aplicar_cambio_masivo,
    build_filtros_query_string,
    buscar_articulos_codigo_precios,
    guardar_lote,
    listar_marcas_catalogo_precios,
    listar_precios_terminados,
    listar_proveedores_catalogo_precios,
    listar_rubros_catalogo_precios,
    listar_subrubros_catalogo_precios,
    nombres_listas_precio,
    parse_precios_terminados_filtros,
    preview_cambio_masivo,
    resolver_articulos_seleccionados,
)

logger = logging.getLogger(__name__)

_PERMISO = "ventas.precios_terminados.editar"
_PERMISO_HISTORIAL = "ventas.precios_historial.ver"


def _base_empresa(request) -> str:
    session_user = request.session.get("user", {}) or {}
    return (session_user.get("base_empresa") or "").strip()


def _id_usuario(request) -> int | None:
    session_user = request.session.get("user", {}) or {}
    return session_user.get("id_usuario") or session_user.get("cod_usuario")


def _parse_json_body(request) -> Dict[str, Any]:
    try:
        if not request.body:
            return {}
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _catalogos_context(base_empresa: str, filtros) -> Dict[str, Any]:
    tipo = filtros.tipo_producto
    listas_nombres = nombres_listas_precio()
    listas_catalogo = [
        {"value": i, "label": listas_nombres[i]}
        for i in sorted(listas_nombres.keys())
    ]
    articulos_sel = resolver_articulos_seleccionados(
        base_empresa, filtros.codigos_incluidos, tipo
    )
    codigos_catalogo = [
        {"value": a["id_articulo"], "label": a["codigo_display"]}
        for a in articulos_sel
        if a.get("id_articulo") is not None
    ]
    return {
        "marcas_catalogo": listar_marcas_catalogo_precios(base_empresa, tipo),
        "proveedores_catalogo": listar_proveedores_catalogo_precios(base_empresa, tipo),
        "rubros_catalogo": listar_rubros_catalogo_precios(base_empresa, tipo),
        "subrubros_catalogo": listar_subrubros_catalogo_precios(
            base_empresa,
            tipo,
            rubros_incluidos=filtros.rubros_incluidos or None,
        ),
        "listas_catalogo": listas_catalogo,
        "codigos_catalogo": codigos_catalogo,
    }


@tiene_permiso(_PERMISO)
def precios_terminados_view(request):
    base_empresa = _base_empresa(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    filtros = parse_precios_terminados_filtros(request.GET)
    cambio_tipo = request.GET.get("cambio_tipo") == "1"
    if cambio_tipo:
        messages.info(request, "Cambiaste el tipo de producto; los filtros se actualizaron.")

    resultado = listar_precios_terminados(base_empresa, filtros)
    filas = resultado.get("filas") or []
    total_count = int(resultado.get("total_count") or 0)
    total_pages = int(resultado.get("total_pages") or 0)

    qs_base = build_filtros_query_string(filtros, page=1)
    qs_tipo_terminado = build_filtros_query_string(
        filtros.__class__(tipo_producto=TIPO_PRODUCTO_TERMINADO, listas_incluidas=filtros.listas_incluidas),
        reset_secundarios=True,
    )
    qs_tipo_2da = build_filtros_query_string(
        filtros.__class__(tipo_producto=TIPO_PRODUCTO_2DA, listas_incluidas=filtros.listas_incluidas),
        reset_secundarios=True,
    )

    page = filtros.page
    pagination_pages: List[int] = []
    if total_pages > 0:
        start = max(1, page - 2)
        end = min(total_pages, page + 2)
        pagination_pages = list(range(start, end + 1))

    filtros_json = {
        "tipo_producto": filtros.tipo_producto,
        "marcas_incluidos": filtros.marcas_incluidos,
        "codigos_incluidos": filtros.codigos_incluidos,
        "proveedores_incluidos": filtros.proveedores_incluidos,
        "rubros_incluidos": filtros.rubros_incluidos,
        "subrubros_incluidos": filtros.subrubros_incluidos,
        "listas_incluidas": filtros.listas_incluidas,
    }
    listas_nombres = nombres_listas_precio()
    tabla_config = {
        "listasIncluidas": filtros.listas_incluidas,
        "listasNombres": listas_nombres,
        "filtrosSnapshot": filtros_json,
        "puedeVerHistorial": user_has_permission(request.user, _PERMISO_HISTORIAL)
        or user_has_permission(request.user, _PERMISO),
        "urls": {
            "guardar": reverse("ventas:precios_terminados_guardar"),
            "masivoPreview": reverse("ventas:precios_terminados_masivo_preview"),
            "masivoAplicar": reverse("ventas:precios_terminados_masivo_aplicar"),
            "historialArticulo": reverse(
                "ventas:api_precios_historial_articulo",
                kwargs={"id_articulo": 0},
            ),
        },
    }
    listas_header = [
        {"id": i, "nombre": listas_nombres.get(i, f"Lista {i}")}
        for i in filtros.listas_incluidas
    ]

    context = {
        "filtros": filtros,
        "filas": filas,
        "filas_json": json.dumps(filas, ensure_ascii=False),
        "total_count": total_count,
        "total_pages": total_pages,
        "page": page,
        "page_size": PAGE_SIZE,
        "pagination_pages": pagination_pages,
        "listas_incluidas": filtros.listas_incluidas,
        "listas_header": listas_header,
        "listas_nombres": listas_nombres,
        "tipo_producto": filtros.tipo_producto,
        "tipo_label": "2da selección" if filtros.tipo_producto == TIPO_PRODUCTO_2DA else "Terminado",
        "qs_base": qs_base,
        "qs_tipo_terminado": qs_tipo_terminado,
        "qs_tipo_2da": qs_tipo_2da,
        "marcas_incluidos": filtros.marcas_incluidos,
        "proveedores_incluidos": filtros.proveedores_incluidos,
        "rubros_incluidos": filtros.rubros_incluidos,
        "subrubros_incluidos": filtros.subrubros_incluidos,
        "listas_incluidas_selected": filtros.listas_incluidas,
        "tabla_config": tabla_config,
        "num_columnas_tabla": 4 + len(filtros.listas_incluidas) * 2,
    }
    context.update(_catalogos_context(base_empresa, filtros))
    return render(request, "ventas/precios_terminados_tabla.html", context)


@tiene_permiso(_PERMISO)
@require_GET
def api_precios_terminados_articulos_buscar(request):
    base_empresa = _base_empresa(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "sin_empresa"}, status=400)

    q = (request.GET.get("q") or "").strip()
    tipo = (request.GET.get("tipo_producto") or TIPO_PRODUCTO_TERMINADO).strip().lower()
    excluir_raw = request.GET.get("excluir") or ""
    excluir: List[int] = []
    for part in excluir_raw.split(","):
        part = part.strip()
        if part.isdigit():
            excluir.append(int(part))

    items = buscar_articulos_codigo_precios(
        base_empresa,
        q,
        tipo,
        excluir_ids=excluir or None,
    )
    return JsonResponse({"ok": True, "articulos": items})


@tiene_permiso(_PERMISO)
@require_POST
def precios_terminados_guardar_view(request):
    base_empresa = _base_empresa(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "sin_empresa"}, status=400)

    payload = _parse_json_body(request)
    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        return JsonResponse({"ok": False, "error": "sin_items"}, status=400)

    res = guardar_lote(base_empresa, items, id_usuario=_id_usuario(request))
    status = 200 if res.get("ok") else 400
    return JsonResponse(res, status=status)


@tiene_permiso(_PERMISO)
@require_POST
def precios_terminados_masivo_preview_view(request):
    base_empresa = _base_empresa(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "sin_empresa"}, status=400)

    payload = _parse_json_body(request)
    filtros_data = payload.get("filtros") or {}
    operacion = payload.get("operacion") or {}
    ids_articulos = payload.get("ids_articulos")

    f = parse_precios_terminados_filtros(_DictParams(filtros_data))
    preview = preview_cambio_masivo(
        base_empresa, f, operacion, ids_articulos=ids_articulos
    )
    if not preview.get("ok", True):
        return JsonResponse(preview, status=400)
    return JsonResponse({"ok": True, **preview})


@tiene_permiso(_PERMISO)
@require_POST
def precios_terminados_masivo_aplicar_view(request):
    base_empresa = _base_empresa(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "sin_empresa"}, status=400)

    payload = _parse_json_body(request)
    filtros_data = payload.get("filtros") or {}
    operacion = payload.get("operacion") or {}
    ids_articulos = payload.get("ids_articulos")

    f = parse_precios_terminados_filtros(_DictParams(filtros_data))
    res = aplicar_cambio_masivo(
        base_empresa,
        f,
        operacion,
        id_usuario=_id_usuario(request),
        ids_articulos=ids_articulos,
    )
    status = 200 if res.get("ok") else 400
    return JsonResponse(res, status=status)


class _DictParams:
    """Adaptador mínimo para reutilizar parse_precios_terminados_filtros con dict."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)

    def getlist(self, key):
        val = self._data.get(key)
        if val is None:
            return []
        if isinstance(val, list):
            return [str(v) for v in val]
        return [str(val)]
