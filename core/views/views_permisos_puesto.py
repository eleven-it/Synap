# core/views/views_permisos_puesto.py
"""Asignación de permisos Synap y menú AdministraNET por puesto (solo usuario supervisor)."""

import json
import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from core.decorators import solo_usuario_supervisor
from core.services.administranet_permisos_menu import AdministraNETPermisosMenuService
from core.services.administranet_permisos_sistema import AdministraNETPermisosSistemaService
from core.services.administranet_puestos import AdministraNETPuestosService
from core.services.synap_permisos import (
    SynapPermisosService,
    backfill_synap_permisos_desde_legacy,
)
from core.services.synap_permisos_seed import asegurar_synap_schema_si_procede

logger = logging.getLogger(__name__)

TAB_SYNAP = "synap"
TAB_MENU = "menu"
TAB_SISTEMA = "sistema"
TABS_VALIDOS = (TAB_SYNAP, TAB_MENU, TAB_SISTEMA)

MODULOS_ATAJO = (
    ("Ventas", "ventas"),
    ("Compras", "compras"),
    ("Stock", "stock"),
    ("Reportes", "reports"),
    ("Self-Checkout / TPV", "self_checkout"),
    ("Producción (MPR)", "mpr"),
    ("Logística", "logistica"),
    ("Facturación AFIP", "fe_afip"),
    ("IA", "ia"),
)


def _base_empresa_desde_sesion(request) -> str:
    session_user = request.session.get("user", {})
    return (session_user.get("base_empresa") or "").strip()


def _obtener_puesto_o_redirect(base_empresa: str, id_puesto: int, request):
    puestos_service = AdministraNETPuestosService()
    puesto = puestos_service.obtener_puesto(base_empresa, id_puesto)
    if not puesto:
        messages.error(request, "Puesto no encontrado.")
        return None
    return puesto


@solo_usuario_supervisor
def permisos_puesto_lista_view(request):
    """Listado de puestos con enlace a la gestión unificada de permisos."""
    base_empresa = _base_empresa_desde_sesion(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    q = request.GET.get("q", "").strip()
    permisos_service = AdministraNETPermisosSistemaService()
    puestos = permisos_service.listar_puestos(
        base_empresa=base_empresa,
        busqueda=q if q else None,
    )

    paginator = Paginator(puestos, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    backfill_resultado = request.session.pop("synap_backfill_resultado", None)

    return render(
        request,
        "core/permisos_puesto_lista.html",
        {
            "puestos": page_obj,
            "q": q,
            "base_empresa": base_empresa,
            "backfill_resultado": backfill_resultado,
        },
    )


@solo_usuario_supervisor
@require_POST
@csrf_protect
def permisos_puesto_backfill_view(request):
    """
    Ejecuta el backfill de permisos legacy → synap_* para la empresa logueada.

    Con `dry_run` (checkbox) solo simula. Reutiliza la misma lógica que el comando
    `backfill_synap_permisos_from_legacy`.
    """
    base_empresa = _base_empresa_desde_sesion(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:permisos_puesto_lista")

    dry_run = (request.POST.get("dry_run") or "").strip().lower() in ("1", "si", "true", "on")
    force = (request.POST.get("force") or "").strip().lower() in ("1", "si", "true", "on")

    resultado = backfill_synap_permisos_desde_legacy(base_empresa, dry_run=dry_run, force=force)

    if resultado.get("success"):
        messages.success(request, resultado.get("message", "Backfill completado."))
    else:
        messages.error(request, resultado.get("message", "No se pudo ejecutar el backfill."))

    # Guardar el detalle por puesto para mostrarlo en el listado tras el redirect.
    request.session["synap_backfill_resultado"] = {
        "success": bool(resultado.get("success")),
        "dry_run": bool(resultado.get("dry_run")),
        "force": bool(resultado.get("force")),
        "message": resultado.get("message", ""),
        "detalles": list(resultado.get("detalles") or []),
        "total_revisados": resultado.get("total_revisados", 0),
        "total_puestos": resultado.get("total_puestos", 0),
        "total_roles": resultado.get("total_roles", 0),
        "total_asignaciones": resultado.get("total_asignaciones", 0),
    }

    return redirect("core:permisos_puesto_lista")


@solo_usuario_supervisor
@csrf_protect
def permisos_puesto_gestionar_view(request, id_puesto: int):
    """
    Pestañas: Synap (permiso_sistema_puesto), Menú VB6 (permisos), enlace a permisos_sistema legacy.
    """
    base_empresa = _base_empresa_desde_sesion(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:permisos_puesto_lista")

    puesto = _obtener_puesto_o_redirect(base_empresa, id_puesto, request)
    if not puesto:
        return redirect("core:permisos_puesto_lista")

    tab = (request.GET.get("tab") or TAB_SYNAP).strip().lower()
    if tab not in TABS_VALIDOS:
        tab = TAB_SYNAP

    try:
        asegurar_synap_schema_si_procede(base_empresa)
    except Exception as exc:
        logger.warning("Asegurar esquema Synap al abrir gestión puesto: %s", exc)

    permiso_synap_svc = SynapPermisosService()
    menu_svc = AdministraNETPermisosMenuService()

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip().lower()
        if accion == "guardar_menu" or tab == TAB_MENU:
            permisos_seleccionados = set(request.POST.getlist("permisos"))
            if menu_svc.guardar_permisos_puesto(
                base_empresa, id_puesto, permisos_seleccionados
            ):
                messages.success(
                    request,
                    f"Permisos de menú AdministraNET guardados para «{puesto.get('nombre', '')}».",
                )
            else:
                messages.error(request, "No se pudieron guardar los permisos del menú.")
            return redirect(
                f"{reverse('core:permisos_puesto_gestionar', args=[id_puesto])}?tab=menu"
            )

    q_synap = request.GET.get("q", "").strip()
    grupo_synap = request.GET.get("grupo", "").strip() or None

    permisos_synap = permiso_synap_svc.listar_permisos(
        base_empresa=base_empresa,
        busqueda=q_synap if q_synap else None,
        grupo=grupo_synap,
        id_puesto=id_puesto,
    )
    permisos_por_modulo: dict = {}
    for perm in permisos_synap:
        modulo = perm.get("grupo_permiso") or "Sin módulo"
        permisos_por_modulo.setdefault(modulo, []).append(perm)
    permisos_agrupados = sorted(permisos_por_modulo.items(), key=lambda x: x[0])

    grupos = permiso_synap_svc.obtener_grupos(base_empresa)
    rol_synap = permiso_synap_svc.obtener_resumen_rol_puesto(base_empresa, id_puesto)
    estructura_menu = menu_svc.obtener_estructura_menu()
    permisos_menu_actuales = menu_svc.obtener_permisos_puesto(base_empresa, id_puesto)

    url_sistema = reverse("core:editar_permisos_puesto", args=[id_puesto])

    return render(
        request,
        "core/permisos_puesto_gestionar.html",
        {
            "puesto": puesto,
            "id_puesto": id_puesto,
            "base_empresa": base_empresa,
            "tab_activa": tab,
            "permisos_agrupados": permisos_agrupados,
            "total_permisos_synap": len(permisos_synap),
            "q_synap": q_synap,
            "grupo_synap": grupo_synap or "",
            "grupos": grupos,
            "rol_synap": rol_synap,
            "estructura_menu": estructura_menu,
            "permisos_actuales": permisos_menu_actuales,
            "modulos_atajo": MODULOS_ATAJO,
            "url_sistema_legacy": url_sistema,
        },
    )


@solo_usuario_supervisor
@require_POST
@csrf_protect
def permisos_puesto_toggle_synap_view(request, id_puesto: int):
    """API JSON: activa/desactiva un permiso Synap para el puesto indicado."""
    base_empresa = _base_empresa_desde_sesion(request)
    if not base_empresa:
        return JsonResponse(
            {"success": False, "error": "Empresa no determinada"},
            status=400,
        )

    puesto = _obtener_puesto_o_redirect(base_empresa, id_puesto, request)
    if not puesto:
        return JsonResponse({"success": False, "error": "Puesto no encontrado"}, status=404)

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)

    id_permiso = data.get("id_permiso")
    valor = (data.get("valor") or "").strip()
    if valor not in ("Si", "No"):
        return JsonResponse({"success": False, "error": 'Valor debe ser "Si" o "No"'}, status=400)
    try:
        id_permiso_int = int(id_permiso)
    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "error": "id_permiso inválido"},
            status=400,
        )

    svc = SynapPermisosService()
    if svc.actualizar_valor_permiso(
        base_empresa, id_permiso_int, valor, id_puesto, puesto.get("nombre", "")
    ):
        return JsonResponse({"success": True, "valor": valor})
    return JsonResponse(
        {"success": False, "error": "No se pudo actualizar el permiso"},
        status=500,
    )


@solo_usuario_supervisor
@require_POST
@csrf_protect
def permisos_puesto_modulo_synap_view(request, id_puesto: int):
    """Activa o desactiva todos los permisos de un módulo Synap para el puesto."""
    base_empresa = _base_empresa_desde_sesion(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:permisos_puesto_lista")

    puesto = _obtener_puesto_o_redirect(base_empresa, id_puesto, request)
    if not puesto:
        return redirect("core:permisos_puesto_lista")

    prefijo = (request.POST.get("prefijo_modulo") or "").strip().lower()
    activar = (request.POST.get("activar") or "").strip().lower() in ("1", "si", "true", "on")

    if not prefijo:
        messages.error(request, "Módulo no indicado.")
    else:
        svc = SynapPermisosService()
        n = svc.establecer_modulo_para_puesto(
            base_empresa, id_puesto, prefijo, activar, puesto.get("nombre", "")
        )
        accion_txt = "activados" if activar else "desactivados"
        messages.success(
            request,
            f"Se {accion_txt} {n} permiso(s) Synap del módulo «{prefijo}» para «{puesto.get('nombre', '')}».",
        )

    tab = request.POST.get("tab") or TAB_SYNAP
    return redirect(
        f"{reverse('core:permisos_puesto_gestionar', args=[id_puesto])}?tab={tab}"
    )
