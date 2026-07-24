"""Ejecuta jobs de backup full/incremental."""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.backup.models import BackupJob
from core.backup.services import config as backup_config
from core.backup.services.orchestrator import prune_old_backups, resolve_parent_full_job, run_job

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ejecuta backup full o incremental (Postgres Synap + MySQL AdministraNET)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=[BackupJob.JOB_TYPE_FULL, BackupJob.JOB_TYPE_INCREMENTAL],
            default=BackupJob.JOB_TYPE_FULL,
            help="Tipo de backup",
        )
        parser.add_argument("--job-id", dest="job_id", default="", help="UUID de job existente")
        parser.add_argument("--base-mysql", dest="base_mysql", default="", help="Base MySQL prod")
        parser.add_argument(
            "--include-empresas",
            action="store_true",
            help="Incluir dump de la base empresas (solo full)",
        )
        parser.add_argument(
            "--scheduled",
            action="store_true",
            help="Job programado por cron (sin usuario UI)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula dumps sin tocar engines reales",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Purgar backups locales más antiguos que la retención configurada en UI",
        )

    def handle(self, *args, **options):
        if options["prune"]:
            count = prune_old_backups()
            self.stdout.write(self.style.SUCCESS(f"Purgados {count} jobs antiguos."))
            if not options.get("job_id") and not options.get("scheduled"):
                return

        job = self._resolve_job(options)
        self.stdout.write(f"Ejecutando job {job.id} ({job.job_type}) base={job.base_mysql}...")
        try:
            run_job(job, dry_run=options["dry_run"])
        except Exception as exc:
            logger.exception("backup_run falló: %s", exc)
            job.status = BackupJob.STATUS_FAILED
            job.error_summary = str(exc)
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "error_summary", "finished_at"])
            raise CommandError(str(exc)) from exc

        job.refresh_from_db()
        if job.status == BackupJob.STATUS_COMPLETED:
            self.stdout.write(self.style.SUCCESS(f"Backup completado: {job.id}"))
        elif job.status == BackupJob.STATUS_PARTIAL_FAILED:
            self.stdout.write(self.style.WARNING(f"Backup parcial: {job.error_summary}"))
        else:
            raise CommandError(job.error_summary or f"Backup falló ({job.status})")

    def _resolve_job(self, options) -> BackupJob:
        job_id = (options.get("job_id") or "").strip()
        if job_id:
            try:
                return BackupJob.objects.get(pk=job_id)
            except BackupJob.DoesNotExist as exc:
                raise CommandError(f"Job no encontrado: {job_id}") from exc

        base_mysql = (options.get("base_mysql") or "").strip()
        if not base_mysql:
            base_mysql = (backup_config.get_backup_settings().base_mysql or "").strip()
        if not base_mysql:
            raise CommandError(
                "Indique --base-mysql o configure la base MySQL en /core/backups/configuracion/."
            )

        job_type = options["type"]
        parent = None
        if job_type == BackupJob.JOB_TYPE_INCREMENTAL:
            parent = resolve_parent_full_job(base_mysql)
            if not parent:
                raise CommandError(
                    "No hay backup full completado para esta base. Ejecute --type full primero."
                )

        return BackupJob.objects.create(
            job_type=job_type,
            status=BackupJob.STATUS_QUEUED,
            base_mysql=base_mysql,
            include_empresas_table=bool(options.get("include_empresas"))
            or (
                bool(options.get("scheduled"))
                and backup_config.get_backup_settings().include_empresas
                and job_type == BackupJob.JOB_TYPE_FULL
            ),
            parent_job=parent,
            scheduled=bool(options.get("scheduled")),
        )
