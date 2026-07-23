# -*- coding: utf-8 -*-
"""Vistas UI y API de backup DR Synap."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from core.backup.models import BackupArtifact, BackupJob
from core.decorators import administranet_login_required, tiene_permiso
from core.utils.administranet_types import to_int_or_none, str_or_default
from login.administranet_auth import AdministraNETAuth

logger = logging.getLogger(__name__)


def _list_mysql_bases():
    """Lista bases MySQL desde tabla empresas (login)."""
    auth = AdministraNETAuth()
    empresas = auth.get_empresas()
    bases = []
    seen = set()
    for emp in empresas:
        base = str_or_default(emp.get("base_empresa"), "").strip()
        if not base or base in seen:
            continue
        seen.add(base)
        bases.append(
            {
                "base_empresa": base,
                "nombre_empresa": str_or_default(emp.get("nombre_empresa"), base),
                "id_empresa": to_int_or_none(emp.get("id_empresa")),
            }
        )
    return bases


def _job_to_api_dict(job: BackupJob) -> dict:
    total_bytes = sum(a.size_bytes for a in job.artifacts.all())
    return {
        "id": str(job.id),
        "job_type": job.job_type,
        "status": job.status,
        "base_mysql": job.base_mysql,
        "include_empresas_table": job.include_empresas_table,
        "parent_job_id": str(job.parent_job_id) if job.parent_job_id else None,
        "scheduled": job.scheduled,
        "triggered_by_cod_usuario": job.triggered_by_cod_usuario,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "error_summary": job.error_summary,
        "remote_upload_status": job.remote_upload_status,
        "total_bytes": total_bytes,
        "manifest_path": job.manifest_path,
    }


def _launch_backup_subprocess(job_id: str) -> None:
    manage_py = Path(settings.BASE_DIR) / "manage.py"
    cmd = [sys.executable, str(manage_py), "backup_run", f"--job-id={job_id}"]
    subprocess.Popen(
        cmd,
        cwd=str(settings.BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


@require_GET
@administranet_login_required
@tiene_permiso("administrar.backup")
def backup_list_view(request):
    jobs = BackupJob.objects.prefetch_related("artifacts").all()[:100]
    bases = _list_mysql_bases()
    return render(
        request,
        "core/backups/list.html",
        {
            "jobs": jobs,
            "bases_mysql": bases,
            "sftp_enabled": getattr(settings, "BACKUP_SFTP_ENABLED", False),
        },
    )


@require_GET
@administranet_login_required
@tiene_permiso("administrar.backup")
def backup_detail_view(request, job_id):
    job = get_object_or_404(BackupJob.objects.prefetch_related("artifacts"), pk=job_id)
    log_content = ""
    if job.log_path and Path(job.log_path).is_file():
        log_content = Path(job.log_path).read_text(encoding="utf-8", errors="replace")
    return render(
        request,
        "core/backups/detail.html",
        {
            "job": job,
            "artifacts": job.artifacts.all(),
            "log_content": log_content,
        },
    )


@require_http_methods(["POST"])
@administranet_login_required
@tiene_permiso("administrar.backup")
def backup_launch_view(request):
    job_type = (request.POST.get("job_type") or BackupJob.JOB_TYPE_FULL).strip()
    base_mysql = (request.POST.get("base_mysql") or "").strip()
    include_empresas = request.POST.get("include_empresas") == "1"

    if not base_mysql:
        if request.headers.get("Accept") == "application/json":
            return JsonResponse(
                {"ok": False, "error": "Debe seleccionar una base MySQL de producción."},
                status=400,
            )
        return redirect(reverse("core:backup_list"))

    if job_type not in (BackupJob.JOB_TYPE_FULL, BackupJob.JOB_TYPE_INCREMENTAL):
        job_type = BackupJob.JOB_TYPE_FULL

    parent = None
    if job_type == BackupJob.JOB_TYPE_INCREMENTAL:
        from core.backup.services.orchestrator import resolve_parent_full_job

        parent = resolve_parent_full_job(base_mysql)
        if not parent:
            msg = "No hay backup full completado para esta base. Ejecute un full primero."
            if request.headers.get("Accept") == "application/json":
                return JsonResponse({"ok": False, "error": msg}, status=400)
            return redirect(reverse("core:backup_list"))

    session_user = request.session.get("user") or {}
    job = BackupJob.objects.create(
        job_type=job_type,
        status=BackupJob.STATUS_QUEUED,
        base_mysql=base_mysql,
        include_empresas_table=include_empresas and job_type == BackupJob.JOB_TYPE_FULL,
        parent_job=parent,
        triggered_by_id_usuario=to_int_or_none(session_user.get("id_usuario")),
        triggered_by_cod_usuario=str_or_default(session_user.get("cod_usuario"), ""),
        scheduled=False,
    )

    try:
        _launch_backup_subprocess(str(job.id))
    except Exception as exc:
        logger.exception("No se pudo lanzar subprocess backup_run: %s", exc)
        job.status = BackupJob.STATUS_FAILED
        job.error_summary = f"No se pudo iniciar el proceso de backup: {exc}"
        job.finished_at = timezone.now()
        job.save(update_fields=["status", "error_summary", "finished_at"])

    if request.headers.get("Accept") == "application/json":
        return JsonResponse({"ok": True, "job": _job_to_api_dict(job)})

    return redirect(reverse("core:backup_detail", kwargs={"job_id": job.id}))


@require_GET
@administranet_login_required
@tiene_permiso("administrar.backup")
def backup_job_api_view(request, job_id):
    job = get_object_or_404(BackupJob.objects.prefetch_related("artifacts"), pk=job_id)
    return JsonResponse({"ok": True, "job": _job_to_api_dict(job)})
