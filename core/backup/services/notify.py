"""Notificaciones por correo del resultado de jobs de backup DR."""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from core.backup.models import BackupJob, BackupSettings
from core.backup.services import config as backup_config
from core.services.outbound_email import correo_saliente_configurado, enviar_correo_saliente

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_STATUS_LABEL = {
    BackupJob.STATUS_COMPLETED: "Completado",
    BackupJob.STATUS_PARTIAL_FAILED: "Parcial (con errores)",
    BackupJob.STATUS_FAILED: "Fallido",
    BackupJob.STATUS_CANCELLED: "Cancelado",
    BackupJob.STATUS_QUEUED: "En cola",
    BackupJob.STATUS_RUNNING: "En ejecución",
}

_REMOTE_LABEL = {
    BackupJob.REMOTE_SUCCESS: "SFTP OK",
    BackupJob.REMOTE_FAILED: "SFTP fallido",
    BackupJob.REMOTE_SKIPPED: "SFTP omitido",
    BackupJob.REMOTE_PENDING: "SFTP pendiente",
}


def parse_notify_recipients(raw: str | None) -> List[str]:
    text = (raw or "").replace(";", ",").replace("\n", ",").replace("\r", ",")
    seen = set()
    out: List[str] = []
    for part in text.split(","):
        addr = part.strip()
        if not addr or addr.lower() in seen:
            continue
        if not _EMAIL_RE.match(addr):
            continue
        seen.add(addr.lower())
        out.append(addr)
    return out


def should_notify(job: BackupJob, settings_obj: BackupSettings | None = None) -> bool:
    bs = settings_obj or backup_config.get_backup_settings()
    if not bs.notify_email_enabled:
        return False
    if not parse_notify_recipients(bs.notify_email_to):
        return False

    remote_failed = job.remote_upload_status == BackupJob.REMOTE_FAILED
    if job.status == BackupJob.STATUS_FAILED:
        return bool(bs.notify_on_failure)
    if job.status == BackupJob.STATUS_PARTIAL_FAILED:
        return bool(bs.notify_on_partial)
    if job.status == BackupJob.STATUS_COMPLETED:
        if remote_failed:
            return bool(bs.notify_on_partial)
        return bool(bs.notify_on_success)
    return False


def _job_detail_url(job: BackupJob) -> str:
    path = reverse("core:backup_detail", kwargs={"job_id": job.id})
    base = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    if base:
        return f"{base}{path}"
    return path


def _fmt_dt(value) -> str:
    if not value:
        return "—"
    local = timezone.localtime(value) if timezone.is_aware(value) else value
    return local.strftime("%d/%m/%Y %H:%M")


def _remediation_hints(job: BackupJob) -> List[str]:
    hints: List[str] = []
    summary = (job.error_summary or "").lower()
    if job.status == BackupJob.STATUS_FAILED:
        hints.append("Revise el detalle del job y el archivo backup.log del directorio local.")
    if "binlog" in summary or "log_bin" in summary:
        hints.append("MySQL: habilite binary log (log_bin=ON) y vuelva a ejecutar un full.")
    if "wal" in summary or "postgres" in summary:
        hints.append(
            "PostgreSQL: verifique archive_mode, archive_command y el directorio WAL en Configuración."
        )
    if "disco" in summary or "espacio" in summary or "disk" in summary:
        hints.append("Libere espacio en disco en el directorio local de backups.")
    if job.remote_upload_status == BackupJob.REMOTE_FAILED:
        hints.append(
            "SFTP falló: pruebe la conexión en Configuración y revise host/usuario/clave/ruta remota."
        )
        hints.append("Los dumps locales pueden estar OK; reintente solo la subida o un nuevo full.")
    if job.status == BackupJob.STATUS_PARTIAL_FAILED:
        hints.append(
            "Fallo parcial: un motor OK y otro no. Corrija el motor fallido y lance un nuevo job."
        )
    if not hints:
        hints.append("Abra el detalle del job en Synap para ver errores y artefactos.")
    return hints


def build_notification_email(job: BackupJob) -> tuple[str, str]:
    status_label = _STATUS_LABEL.get(job.status, job.status)
    remote_label = _REMOTE_LABEL.get(job.remote_upload_status, job.remote_upload_status or "—")
    tipo = "Completo" if job.job_type == BackupJob.JOB_TYPE_FULL else "Incremental"
    subject_prefix = {
        BackupJob.STATUS_COMPLETED: "[Synap Backup OK]",
        BackupJob.STATUS_PARTIAL_FAILED: "[Synap Backup PARCIAL]",
        BackupJob.STATUS_FAILED: "[Synap Backup FALLO]",
    }.get(job.status, "[Synap Backup]")
    if job.status == BackupJob.STATUS_COMPLETED and job.remote_upload_status == BackupJob.REMOTE_FAILED:
        subject_prefix = "[Synap Backup SFTP FALLO]"
    subject = f"{subject_prefix} {tipo} · {job.base_mysql} · {status_label}"

    lines = [
        "Notificación de copia de seguridad Synap",
        "",
        f"Estado: {status_label}",
        f"Tipo: {tipo}",
        f"Base MySQL: {job.base_mysql or '—'}",
        f"Job ID: {job.id}",
        f"Inicio: {_fmt_dt(job.started_at)}",
        f"Fin: {_fmt_dt(job.finished_at)}",
        f"Copia remota: {remote_label}",
        f"Detalle: {_job_detail_url(job)}",
        "",
    ]
    if job.error_summary:
        lines.append("Resumen de errores:")
        lines.append(job.error_summary.strip())
        lines.append("")
    lines.append("Acciones de remediación sugeridas:")
    for hint in _remediation_hints(job):
        lines.append(f"  - {hint}")
    lines.extend(
        [
            "",
            "Configure destinatarios y eventos en:",
            "  Copias de seguridad → Configuración → Notificaciones por correo",
            "",
            "— Synap Backup DR",
        ]
    )
    return subject, "\n".join(lines)


def notify_backup_job(job: BackupJob, *, dry_run: bool = False) -> Optional[dict]:
    """
    Envía mail si corresponde. Nunca propaga excepciones al orquestador.
    Devuelve el dict de envío o None si no se intentó.
    """
    if dry_run:
        return None
    try:
        bs = backup_config.get_backup_settings()
        if not should_notify(job, bs):
            return None
        recipients = parse_notify_recipients(bs.notify_email_to)
        if not correo_saliente_configurado():
            logger.warning(
                "Backup %s: notificación omitida (correo saliente no configurado).",
                job.id,
            )
            return {"ok": False, "message": "Correo saliente no configurado.", "recipients": recipients}

        subject, body = build_notification_email(job)
        result = enviar_correo_saliente(
            subject=subject,
            body=body,
            to=recipients,
            fail_silently=True,
        )
        if result.get("ok"):
            logger.info("Backup %s: notificación enviada a %s", job.id, recipients)
        else:
            logger.warning(
                "Backup %s: no se pudo notificar por correo: %s",
                job.id,
                result.get("message"),
            )
        return result
    except Exception as exc:
        logger.exception("Backup %s: error al notificar por correo: %s", job.id, exc)
        return {"ok": False, "message": str(exc), "recipients": []}
