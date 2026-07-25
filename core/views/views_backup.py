# -*- coding: utf-8 -*-
"""Vistas UI y API de backup DR Synap."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from core.backup.models import BackupJob
from core.backup.services import config as backup_config
from core.backup.services.notify import parse_notify_recipients
from core.backup.services.sftp_upload import test_sftp_connection
from core.decorators import administranet_login_required, tiene_permiso
from core.utils.administranet_types import to_int_or_none, str_or_default
from login.administranet_auth import AdministraNETAuth

logger = logging.getLogger(__name__)

DOW_LABELS = backup_config.DOW_LABELS


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


def _schedule_rows_from_json(schedule_json):
    rules = backup_config.normalize_schedule(schedule_json)
    by_dow = {int(r["dow"]): r for r in rules}
    rows = []
    for dow in range(7):
        rule = by_dow.get(dow, {"dow": dow, "time": "02:00", "job_type": "incremental"})
        rows.append(
            {
                "dow": dow,
                "label": DOW_LABELS[dow],
                "time": rule.get("time", "02:00"),
                "job_type": rule.get("job_type", BackupJob.JOB_TYPE_INCREMENTAL),
                "enabled": dow in by_dow,
            }
        )
    return rows


_DIAS_CORTO = ("L", "M", "X", "J", "V", "S", "D")


def _comprimir_dias(dows: list) -> str:
    """Convierte [0,1,2,3,4,5] en 'L–S' y [0,2] en 'L, X' (Lun=0…Dom=6)."""
    dows = sorted(set(int(d) for d in dows))
    if not dows:
        return ""
    tramos = []
    inicio = prev = dows[0]
    for dow in dows[1:]:
        if dow == prev + 1:
            prev = dow
            continue
        tramos.append((inicio, prev))
        inicio = prev = dow
    tramos.append((inicio, prev))
    partes = []
    for a, b in tramos:
        if a == b:
            partes.append(_DIAS_CORTO[a])
        elif b == a + 1:
            partes.append(f"{_DIAS_CORTO[a]}, {_DIAS_CORTO[b]}")
        else:
            partes.append(f"{_DIAS_CORTO[a]}–{_DIAS_CORTO[b]}")
    return ", ".join(partes)


def _resumen_programacion(schedule_json) -> str:
    """Resumen legible: 'L–S incremental 02:00 · D completo 03:00'."""
    rules = backup_config.normalize_schedule(schedule_json)
    grupos: dict = {}
    for rule in rules:
        clave = (rule.get("job_type"), rule.get("time"))
        grupos.setdefault(clave, []).append(int(rule.get("dow")))
    partes = []
    for (job_type, time_str), dows in sorted(grupos.items(), key=lambda kv: min(kv[1])):
        tipo = "completo" if job_type == BackupJob.JOB_TYPE_FULL else "incremental"
        partes.append(f"{_comprimir_dias(dows)} {tipo} {time_str}")
    return " · ".join(partes)


def _parse_schedule_from_post(request) -> list:
    rules = []
    for dow in range(7):
        if request.POST.get(f"schedule_enabled_{dow}") != "1":
            continue
        time_str = (request.POST.get(f"schedule_time_{dow}") or "02:00").strip()
        job_type = (request.POST.get(f"schedule_type_{dow}") or BackupJob.JOB_TYPE_INCREMENTAL).strip()
        rules.append({"dow": dow, "time": time_str, "job_type": job_type})
    return backup_config.normalize_schedule(rules)


@require_GET
@administranet_login_required
@tiene_permiso("administrar.backup")
def backup_list_view(request):
    jobs = BackupJob.objects.prefetch_related("artifacts").all()[:100]
    bases = _list_mysql_bases()
    bs = backup_config.get_backup_settings()
    return render(
        request,
        "core/backups/list.html",
        {
            "jobs": jobs,
            "bases_mysql": bases,
            "backup_settings": bs,
            "sftp_enabled": backup_config.effective_sftp_enabled(),
            "schedule_hint": backup_config.next_schedule_hint(),
            "schedule_resumen": _resumen_programacion(bs.schedule_json),
        },
    )


@require_http_methods(["GET", "POST"])
@administranet_login_required
@tiene_permiso("administrar.backup")
def backup_config_view(request):
    bs = backup_config.get_backup_settings()
    bases = _list_mysql_bases()
    errors = []

    if request.method == "POST":
        bs.enabled_auto = request.POST.get("enabled_auto") == "1"
        bs.base_mysql = (request.POST.get("base_mysql") or "").strip()
        bs.include_empresas = request.POST.get("include_empresas") == "1"
        bs.local_root = (request.POST.get("local_root") or bs.local_root).strip()
        try:
            bs.retention_days = max(1, int(request.POST.get("retention_days") or bs.retention_days))
        except ValueError:
            errors.append("Los días de retención deben ser un número entero.")
        bs.pg_wal_archive_dir = (request.POST.get("pg_wal_archive_dir") or "").strip()
        bs.sftp_enabled = request.POST.get("sftp_enabled") == "1"
        bs.sftp_host = (request.POST.get("sftp_host") or "").strip()
        try:
            bs.sftp_port = max(1, int(request.POST.get("sftp_port") or 22))
        except ValueError:
            errors.append("El puerto SFTP debe ser un número entero.")
        bs.sftp_user = (request.POST.get("sftp_user") or "").strip()
        bs.sftp_remote_path = (request.POST.get("sftp_remote_path") or "/synap/backups").strip()
        bs.sftp_key_path = (request.POST.get("sftp_key_path") or "").strip()
        bs.schedule_json = _parse_schedule_from_post(request)

        # Password: casilla "borrar" tiene prioridad; si no, vacío = no cambiar.
        if request.POST.get("sftp_clear_password") == "1":
            bs.sftp_password_encrypted = ""
        else:
            new_password = (request.POST.get("sftp_password") or "").strip()
            backup_config.set_sftp_password(bs, new_password or None)

        if request.POST.get("bootstrap_clear_passphrase") == "1":
            bs.bootstrap_passphrase_encrypted = ""
        else:
            new_phrase = (request.POST.get("bootstrap_passphrase") or "").strip()
            backup_config.set_bootstrap_passphrase(bs, new_phrase or None)

        bs.notify_email_enabled = request.POST.get("notify_email_enabled") == "1"
        bs.notify_email_to = (request.POST.get("notify_email_to") or "").strip()
        bs.notify_on_success = request.POST.get("notify_on_success") == "1"
        bs.notify_on_partial = request.POST.get("notify_on_partial") == "1"
        bs.notify_on_failure = request.POST.get("notify_on_failure") == "1"
        if bs.notify_email_enabled and not parse_notify_recipients(bs.notify_email_to):
            errors.append(
                "Active las notificaciones solo si indica al menos un email válido "
                "(ej. admin@empresa.com)."
            )

        session_user = request.session.get("user") or {}
        bs.updated_by_cod_usuario = str_or_default(session_user.get("cod_usuario"), "")

        if not errors:
            bs.save()
            if request.headers.get("Accept") == "application/json":
                return JsonResponse({"ok": True, "message": "Configuración guardada."})
            messages.success(request, "Configuración de copias de seguridad guardada.")
            return redirect(reverse("core:backup_config"))

    schedule_rows = _schedule_rows_from_json(bs.schedule_json)
    return render(
        request,
        "core/backups/configuracion.html",
        {
            "backup_settings": bs,
            "bases_mysql": bases,
            "schedule_rows": schedule_rows,
            "dow_labels": DOW_LABELS,
            "errors": errors,
            "has_sftp_password": bool(bs.sftp_password_encrypted),
            "has_bootstrap_passphrase": bool(bs.bootstrap_passphrase_encrypted),
        },
    )


@require_http_methods(["POST"])
@administranet_login_required
@tiene_permiso("administrar.backup")
def backup_test_sftp_view(request):
    host = (request.POST.get("sftp_host") or "").strip()
    user = (request.POST.get("sftp_user") or "").strip()
    remote_path = (request.POST.get("sftp_remote_path") or "/synap/backups").strip()
    key_path = (request.POST.get("sftp_key_path") or "").strip()
    try:
        port = int(request.POST.get("sftp_port") or 22)
    except ValueError:
        return JsonResponse({"ok": False, "error": "Puerto SFTP inválido."}, status=400)

    password = (request.POST.get("sftp_password") or "").strip()
    if not password:
        password = backup_config.sftp_password_plain()

    result = test_sftp_connection(
        host=host,
        port=port,
        user=user,
        password=password,
        key_path=key_path,
        remote_path=remote_path,
    )
    if result.success:
        return JsonResponse({"ok": True, "message": result.message})
    return JsonResponse({"ok": False, "error": result.message}, status=400)


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
