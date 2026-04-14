# -*- coding: utf-8 -*-
import json
from calendar import monthrange
from datetime import date, datetime
from typing import Any, Dict, List
from urllib.parse import urlencode

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.decorators import tiene_permiso
from ventas.services.objetivos_mysql import (
    actualizar_descripcion_periodo_objetivos,
    anular_periodo_objetivos,
    buscar_vendedores,
    crear_periodo_objetivos,
    guardar_objetivos,
    listar_grupos_objetivos,
    listar_periodos_objetivos,
    obtener_periodo_objetivos,
)


def _usuario_puede_editar_objetivos(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "cod_usuario", None) and str(user.cod_usuario).lower() == "supervisor":
        return True
    fn = getattr(user, "tiene_permiso", None)
    return bool(fn and fn("ventas.editar"))


def _base_empresa_session(request) -> str:
    session_user = request.session.get("user", {}) or {}
    return (session_user.get("base_empresa") or "").strip()


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


@tiene_permiso("ventas.ver")
def objetivos_periodos_list_view(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    ok, err, periodos = listar_periodos_objetivos(base_empresa, solo_activos=True)

    today = date.today()
    last = monthrange(today.year, today.month)[1]
    default_fd = date(today.year, today.month, 1)
    default_fh = date(today.year, today.month, last)

    return render(
        request,
        "ventas/objetivos_periodos_list.html",
        {
            "base_empresa": base_empresa,
            "periodos": periodos if ok else [],
            "error_carga": err if not ok else "",
            "puede_editar": _usuario_puede_editar_objetivos(request.user),
            "fecha_desde_default": default_fd.isoformat(),
            "fecha_hasta_default": default_fh.isoformat(),
        },
    )


@tiene_permiso("ventas.ver")
def objetivos_periodo_nuevo_redirect_view(request):
    """Compatibilidad: la pantalla full-page pasó a modal en el listado."""
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    url = reverse("ventas:objetivos_periodos_list") + "?" + urlencode({"nuevo": "1"})
    return redirect(url)


@tiene_permiso("ventas.ver")
def objetivos_periodo_detalle_view(request, id_periodo: int):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    ok_p, err_p, periodo = obtener_periodo_objetivos(base_empresa, id_periodo)
    if not ok_p:
        messages.error(request, err_p or "Error al cargar el período.")
        return redirect("ventas:objetivos_periodos_list")
    if not periodo:
        messages.error(request, "Período no encontrado.")
        return redirect("ventas:objetivos_periodos_list")

    ok, err, rows = listar_grupos_objetivos(base_empresa, id_periodo)
    grupos: Dict[int, Dict[str, Any]] = {}
    for r in rows:
        cv = r["cod_viajante"]
        if cv not in grupos:
            grupos[cv] = {
                "cod_viajante": cv,
                "nombre_vendedor": r["nombre_vendedor"],
                "clientes": [],
            }
        grupos[cv]["clientes"].append(r)

    grupos_lista = sorted(grupos.values(), key=lambda g: (g["nombre_vendedor"] or "").upper())
    anulado = (periodo.get("anulado") or "No").strip() != "No"
    puede_editar = _usuario_puede_editar_objetivos(request.user) and not anulado

    return render(
        request,
        "ventas/objetivos_venta.html",
        {
            "base_empresa": base_empresa,
            "id_periodo": id_periodo,
            "periodo": periodo,
            "fecha_desde": periodo["fecha_desde"],
            "fecha_hasta": periodo["fecha_hasta"],
            "grupos": grupos_lista,
            "error_carga": err if not ok else "",
            "puede_editar": puede_editar,
            "periodo_anulado": anulado,
        },
    )


@require_POST
@tiene_permiso("ventas.editar")
def objetivos_periodo_anular_view(request, id_periodo: int):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    ok, err = anular_periodo_objetivos(base_empresa, id_periodo)
    if ok:
        messages.success(request, "Período anulado correctamente.")
    else:
        messages.error(request, err or "No se pudo anular el período.")
    return redirect("ventas:objetivos_periodos_list")


@require_POST
@tiene_permiso("ventas.editar")
def objetivos_venta_guardar_api(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "Sin base empresa."}, status=400)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    id_periodo = body.get("id_periodo")
    try:
        id_periodo_int = int(id_periodo)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "id_periodo requerido."}, status=400)

    filas: List[Dict[str, Any]] = body.get("filas") or []
    if not isinstance(filas, list):
        return JsonResponse({"ok": False, "error": "filas debe ser lista."}, status=400)

    ok, err = guardar_objetivos(base_empresa, id_periodo_int, filas)
    if not ok:
        return JsonResponse({"ok": False, "error": err}, status=400)
    return JsonResponse({"ok": True})


@require_POST
@tiene_permiso("ventas.editar")
def api_crear_periodo_objetivos(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "Sin base empresa."}, status=400)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    fd = _parse_date(body.get("fecha_desde", ""))
    fh = _parse_date(body.get("fecha_hasta", ""))
    if not fd or not fh:
        return JsonResponse({"ok": False, "error": "Indique fecha desde y hasta válidas."}, status=400)

    descripcion = body.get("descripcion")
    if descripcion is not None and not isinstance(descripcion, str):
        descripcion = str(descripcion)

    ok, err, new_id = crear_periodo_objetivos(base_empresa, fd, fh, descripcion=descripcion)
    if not ok or not new_id:
        return JsonResponse({"ok": False, "error": err or "No se pudo crear el período."}, status=400)

    detalle_url = reverse("ventas:objetivos_periodo_detalle", kwargs={"id_periodo": new_id})
    return JsonResponse({"ok": True, "id_periodo": new_id, "redirect": detalle_url})


@require_POST
@tiene_permiso("ventas.editar")
def api_actualizar_descripcion_periodo(request):
    """Actualiza la descripción visible del período (cabecera `viajantes_objetivos_periodo`)."""
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "Sin base empresa."}, status=400)
    try:
        body = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    id_periodo = body.get("id_periodo")
    try:
        id_periodo_int = int(id_periodo)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "id_periodo requerido."}, status=400)

    descripcion = body.get("descripcion")
    if descripcion is not None and not isinstance(descripcion, str):
        descripcion = str(descripcion)

    ok, err, desc_norm = actualizar_descripcion_periodo_objetivos(
        base_empresa, id_periodo_int, descripcion
    )
    if not ok or desc_norm is None:
        return JsonResponse({"ok": False, "error": err or "No se pudo guardar."}, status=400)
    return JsonResponse({"ok": True, "descripcion": desc_norm})


@require_GET
@tiene_permiso("ventas.ver")
def api_vendedores_buscar(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse({"results": [], "error": "Sin base empresa."}, status=400)
    q = request.GET.get("q", "")
    ok, rows = buscar_vendedores(base_empresa, q)
    if not ok:
        return JsonResponse({"results": [], "error": "No se pudo buscar."}, status=500)
    return JsonResponse({"results": rows})
