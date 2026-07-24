"""Tick de cron: evalúa programación y lanza jobs de backup automáticos."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.backup.models import BackupJob
from core.backup.services import config as backup_config
from core.backup.services.orchestrator import resolve_parent_full_job

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Evalúa la programación de backup (BackupSettings) y lanza jobs automáticos. "
        "Invocar desde cron del host sin argumentos ni variables BACKUP_*."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--match-hour-only",
            action="store_true",
            help="Coincidir solo la hora (cron horario); por defecto HH:MM exacto.",
        )

    def handle(self, *args, **options):
        bs = backup_config.get_backup_settings()
        if not bs.enabled_auto:
            return

        base_mysql = (bs.base_mysql or "").strip()
        if not base_mysql:
            logger.warning(
                "backup_tick: programación activa pero base MySQL vacía; configure en UI."
            )
            return

        now = timezone.localtime()
        match_minute = not options.get("match_hour_only")
        rules = backup_config.matching_schedule_rules(now, match_minute=match_minute)
        if not rules:
            return

        for rule in rules:
            job_type = rule["job_type"]
            if backup_config.has_recent_scheduled_job(base_mysql, job_type):
                logger.info(
                    "backup_tick: omitido duplicado %s/%s (últimos 50 min)",
                    job_type,
                    base_mysql,
                )
                continue

            parent = None
            if job_type == BackupJob.JOB_TYPE_INCREMENTAL:
                parent = resolve_parent_full_job(base_mysql)
                if not parent:
                    logger.warning(
                        "backup_tick: sin full previo para %s; omitiendo incremental.",
                        base_mysql,
                    )
                    continue

            include_empresas = bool(bs.include_empresas) and job_type == BackupJob.JOB_TYPE_FULL
            job = BackupJob.objects.create(
                job_type=job_type,
                status=BackupJob.STATUS_QUEUED,
                base_mysql=base_mysql,
                include_empresas_table=include_empresas,
                parent_job=parent,
                scheduled=True,
            )
            self.stdout.write(
                f"Lanzando job programado {job.id} ({job_type}) base={base_mysql}"
            )
            self._launch_backup_subprocess(str(job.id))

    def _launch_backup_subprocess(self, job_id: str) -> None:
        manage_py = Path(settings.BASE_DIR) / "manage.py"
        cmd = [sys.executable, str(manage_py), "backup_run", f"--job-id={job_id}"]
        subprocess.Popen(
            cmd,
            cwd=str(settings.BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
