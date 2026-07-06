"""Vistas del módulo Migración Odoo — solo usuario supervisor."""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods, require_POST

from core.decorators import administranet_login_required, solo_usuario_supervisor
from core.utils.empresa_sesion import session_base_empresa_from_request
from odoo_migracion.models import MigrationJob, MigrationEntityMapping, OdooConnection
from odoo_migracion.services.api_key_rotation import rotate_api_key, test_connection
from odoo_migracion.services.coexistence import COEXISTENCE_RULES
from odoo_migracion.services.discovery import run_discovery
from odoo_migracion.services.domains import DOMAIN_SPECS, ordered_domain_keys
from odoo_migracion.services.migration_orchestrator import run_full_domain
from odoo_migracion.services.odoo_client import OdooApiError
from odoo_migracion.services.ui_context import build_migration_overview, enrich_job_for_ui
from odoo_migracion.services.validation import run_validation
from odoo_migracion.view_helpers import panel_context, resolve_conexion


def _base_empresa_sesion(request) -> str:
    return (session_base_empresa_from_request(request) or "").strip()


@require_http_methods(["GET"])
@administranet_login_required
@solo_usuario_supervisor
def dashboard(request):
    base_empresa = _base_empresa_sesion(request)
    ctx = panel_context(
        base_empresa=base_empresa,
        conexion_id=request.GET.get("conexion_id"),
        run_discovery_flag=True,
    )
    conexiones = ctx["conexiones"]
    jobs = MigrationJob.objects.select_related("conexion")
    if ctx["conexion_sel"]:
        jobs = jobs.filter(conexion=ctx["conexion_sel"])
    jobs = jobs.order_by("-created_at")[:15]
    job_rows = []
    conteos = ctx.get("discovery_conteos") or {}
    for job in jobs:
        job_rows.append(enrich_job_for_ui(job, conteos.get(job.dominio)))

    alertas_vencimiento = [c for c in conexiones if c.api_key_proxima_a_vencer()]
    return render(
        request,
        "odoo_migracion/dashboard.html",
        {
            **ctx,
            "jobs": job_rows,
            "alertas_vencimiento": alertas_vencimiento,
        },
    )


@require_http_methods(["GET"])
@administranet_login_required
@solo_usuario_supervisor
def conexion_list(request):
    base_empresa = _base_empresa_sesion(request)
    qs = OdooConnection.objects.all().order_by("nombre")
    if base_empresa:
        qs = qs.filter(base_empresa=base_empresa)
    return render(
        request,
        "odoo_migracion/conexion_list.html",
        {"conexiones": qs, "base_empresa": base_empresa},
    )


@require_http_methods(["GET", "POST"])
@administranet_login_required
@solo_usuario_supervisor
def conexion_form(request, pk=None):
    base_empresa = _base_empresa_sesion(request)
    instancia = get_object_or_404(OdooConnection, pk=pk) if pk else None

    if request.method == "POST":
        nombre = (request.POST.get("nombre") or "").strip()
        be = (request.POST.get("base_empresa") or base_empresa or "").strip()
        base_url = (request.POST.get("base_url") or "").strip()
        database = (request.POST.get("database") or "").strip()
        api_key = (request.POST.get("api_key") or "").strip()
        api_key_label = (request.POST.get("api_key_label") or "").strip()
        timeout = int(request.POST.get("timeout_seconds") or 60)
        activo = request.POST.get("activo") == "on"

        if not nombre or not be or not base_url:
            messages.error(request, _("Complete nombre, base empresa y URL Odoo."))
        else:
            if instancia is None:
                instancia = OdooConnection()
            instancia.nombre = nombre
            instancia.base_empresa = be
            instancia.base_url = base_url
            instancia.database = database
            instancia.timeout_seconds = max(5, min(timeout, 600))
            instancia.activo = activo
            if api_key_label:
                instancia.api_key_label = api_key_label
            if api_key:
                instancia.set_api_key(api_key)
            instancia.save()
            messages.success(request, _("Conexión guardada."))
            return redirect("odoo_migracion:conexion_list")

    return render(
        request,
        "odoo_migracion/conexion_form.html",
        {
            "conexion": instancia,
            "base_empresa": base_empresa,
            "es_edicion": instancia is not None,
        },
    )


@require_POST
@administranet_login_required
@solo_usuario_supervisor
def conexion_test(request, pk):
    conexion = get_object_or_404(OdooConnection, pk=pk)
    result = test_connection(conexion)
    if result.get("success"):
        messages.success(request, _("Conexión Odoo verificada correctamente."))
    else:
        messages.error(request, result.get("error", _("Error al probar conexión.")))
    return redirect("odoo_migracion:conexion_list")


@require_POST
@administranet_login_required
@solo_usuario_supervisor
def conexion_rotate_key(request, pk):
    conexion = get_object_or_404(OdooConnection, pk=pk)
    try:
        result = rotate_api_key(conexion)
        vence = result.get("expires_at")
        if vence:
            try:
                from datetime import date as date_cls

                vence_fmt = date_format(date_cls.fromisoformat(vence), "d/m/Y")
            except (TypeError, ValueError):
                vence_fmt = vence
            messages.success(
                request,
                _("API key rotada. Vence el %(fecha)s.") % {"fecha": vence_fmt},
            )
        else:
            messages.success(request, _("API key rotada."))
        if result.get("warning"):
            messages.warning(request, result["warning"])
    except OdooApiError as exc:
        messages.error(request, str(exc))
    return redirect("odoo_migracion:conexion_list")


@require_http_methods(["GET"])
@administranet_login_required
@solo_usuario_supervisor
def job_list(request):
    base_empresa = _base_empresa_sesion(request)
    ctx = panel_context(
        base_empresa=base_empresa,
        conexion_id=request.GET.get("conexion_id"),
        run_discovery_flag=True,
    )
    jobs_qs = MigrationJob.objects.select_related("conexion").order_by("-created_at")
    if ctx["conexion_sel"]:
        jobs_qs = jobs_qs.filter(conexion=ctx["conexion_sel"])
    jobs_qs = jobs_qs[:100]
    conteos = ctx.get("discovery_conteos") or {}
    job_rows = [enrich_job_for_ui(j, conteos.get(j.dominio)) for j in jobs_qs]
    return render(
        request,
        "odoo_migracion/job_list.html",
        {**ctx, "job_rows": job_rows},
    )


@require_http_methods(["GET"])
@administranet_login_required
@solo_usuario_supervisor
def discovery_view(request):
    base_empresa = _base_empresa_sesion(request)
    report = None
    if base_empresa:
        try:
            report = run_discovery(base_empresa)
        except Exception as exc:
            messages.error(request, _("Error al inventariar: %s") % exc)
    ctx = panel_context(base_empresa=base_empresa, run_discovery_flag=False)
    if report:
        ctx["overview"] = build_migration_overview(
            conexion=ctx["conexion_sel"],
            base_empresa=base_empresa,
            discovery_conteos=report.conteos,
            anomalias_count=len(report.anomalias),
        )
    return render(
        request,
        "odoo_migracion/discovery.html",
        {"base_empresa": base_empresa, "report": report, **ctx},
    )


@require_http_methods(["GET", "POST"])
@administranet_login_required
@solo_usuario_supervisor
def wizard_migracion(request):
    base_empresa = _base_empresa_sesion(request)
    ctx = panel_context(
        base_empresa=base_empresa,
        conexion_id=request.POST.get("conexion_id") if request.method == "POST" else request.GET.get("conexion_id"),
        run_discovery_flag=True,
    )
    conexiones = ctx["conexiones"]

    if request.method == "POST":
        conexion_id = request.POST.get("conexion_id")
        dominio = (request.POST.get("dominio") or "").strip()
        batch_size = int(request.POST.get("batch_size") or 100)
        conexion = get_object_or_404(OdooConnection, pk=conexion_id, activo=True)
        if dominio == "all":
            keys = ordered_domain_keys()
        elif dominio:
            keys = [dominio]
        else:
            messages.error(request, _("Seleccione un dominio."))
            return redirect("odoo_migracion:wizard")

        jobs_creados = []
        for key in keys:
            try:
                job = run_full_domain(conexion, key, batch_size=max(1, min(batch_size, 500)))
                jobs_creados.append(job)
            except OdooApiError as exc:
                messages.error(request, _("Error en dominio %(d)s: %(e)s") % {"d": key, "e": exc})
                break
        if jobs_creados:
            messages.success(
                request,
                _("Migración iniciada: %(n)s job(s).") % {"n": len(jobs_creados)},
            )
            return redirect("odoo_migracion:job_list")

    dominios = sorted(DOMAIN_SPECS, key=lambda s: s.orden)
    return render(
        request,
        "odoo_migracion/wizard.html",
        {
            **ctx,
            "dominios": dominios,
            "reglas": COEXISTENCE_RULES,
        },
    )


@require_http_methods(["GET"])
@administranet_login_required
@solo_usuario_supervisor
def validacion_view(request):
    base_empresa = _base_empresa_sesion(request)
    conexion_id = request.GET.get("conexion_id")
    ctx = panel_context(
        base_empresa=base_empresa,
        conexion_id=conexion_id,
        run_discovery_flag=True,
    )
    report = None
    conexion_sel = ctx["conexion_sel"]
    if conexion_sel:
        try:
            report = run_validation(conexion_sel)
        except Exception as exc:
            messages.error(request, _("Error en validación: %s") % exc)
    return render(
        request,
        "odoo_migracion/validacion.html",
        {
            **ctx,
            "conexion_sel": conexion_sel,
            "report": report,
        },
    )


@require_http_methods(["GET"])
@administranet_login_required
@solo_usuario_supervisor
def mapping_list(request):
    base_empresa = _base_empresa_sesion(request)
    conexion_id = request.GET.get("conexion_id")
    entity_type = request.GET.get("entity_type", "")
    ctx = panel_context(
        base_empresa=base_empresa,
        conexion_id=conexion_id,
        run_discovery_flag=False,
    )
    qs = MigrationEntityMapping.objects.select_related("conexion").order_by("-updated_at")
    if ctx["conexion_sel"]:
        qs = qs.filter(conexion=ctx["conexion_sel"])
    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    summary_ok = qs.filter(sync_state=MigrationEntityMapping.SyncState.OK).count()
    summary_pend = qs.filter(sync_state=MigrationEntityMapping.SyncState.PENDIENTE).count()
    summary_err = qs.filter(sync_state=MigrationEntityMapping.SyncState.ERROR).count()
    return render(
        request,
        "odoo_migracion/mapping_list.html",
        {
            **ctx,
            "mappings": qs[:500],
            "entity_type": entity_type,
            "entity_types": ordered_domain_keys(),
            "summary_ok": summary_ok,
            "summary_pend": summary_pend,
            "summary_err": summary_err,
        },
    )
