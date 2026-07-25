"""Orquestador de jobs full/incremental (Postgres + MySQL)."""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from django.utils import timezone

from core.backup.models import BackupArtifact, BackupJob
from core.backup.services import config as backup_config
from core.backup.services import bootstrap as bootstrap_svc
from core.backup.services import manifest as manifest_svc
from core.backup.services import mysql_backup, notify as backup_notify, postgres_backup, prechecks, sftp_upload

logger = logging.getLogger(__name__)


def job_directory(job: BackupJob) -> Path:
    created = job.created_at or timezone.now()
    root = Path(backup_config.effective_local_root())
    return root / f"{created.year:04d}" / f"{created.month:02d}" / str(job.id)


def resolve_parent_full_job(base_mysql: str) -> Optional[BackupJob]:
    return (
        BackupJob.objects.filter(
            base_mysql=base_mysql,
            job_type=BackupJob.JOB_TYPE_FULL,
            status=BackupJob.STATUS_COMPLETED,
        )
        .order_by("-finished_at", "-created_at")
        .first()
    )


def resolve_incremental_parent(base_mysql: str, explicit_parent_id=None) -> Optional[BackupJob]:
    if explicit_parent_id:
        try:
            parent = BackupJob.objects.get(pk=explicit_parent_id)
            if parent.status == BackupJob.STATUS_COMPLETED:
                return parent
        except BackupJob.DoesNotExist:
            return None
    return resolve_parent_full_job(base_mysql)


def _parent_wal_files(parent: Optional[BackupJob]) -> Set[str]:
    if not parent or not parent.manifest_path:
        return set()
    try:
        data = manifest_svc.read_manifest(Path(parent.manifest_path))
    except Exception:
        return set()
    wal_range = data.get("postgres_wal_range") or {}
    files = wal_range.get("files") or []
    # Incluir también WAL de jobs incrementales encadenados
    for art in data.get("artifacts") or []:
        if art.get("engine") == BackupArtifact.ENGINE_POSTGRES_WAL:
            path = art.get("path") or ""
            if path:
                files.append(Path(path).name)
    return set(files)


def _register_artifacts(job: BackupJob, entries: List[manifest_svc.ManifestArtifact]) -> None:
    for entry in entries:
        abs_path = job_directory(job) / entry.path
        BackupArtifact.objects.create(
            job=job,
            engine=entry.engine,
            relative_path=entry.path,
            absolute_path=str(abs_path),
            sha256=entry.sha256,
            size_bytes=entry.size,
        )


def _artifact_entries_from_paths(
    engine: str, rel_paths: List[str], abs_paths: List[Path]
) -> List[manifest_svc.ManifestArtifact]:
    entries = []
    for rel, abs_p in zip(rel_paths, abs_paths):
        if abs_p.is_file():
            entries.append(
                manifest_svc.ManifestArtifact(
                    engine=engine,
                    path=rel,
                    sha256=manifest_svc.sha256_file(abs_p),
                    size=abs_p.stat().st_size,
                )
            )
    return entries


def run_job(job: BackupJob, *, dry_run: bool = False) -> BackupJob:
    job_dir = job_directory(job)
    job_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "backup.log"
    job.log_path = str(log_path)
    job.status = BackupJob.STATUS_RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "log_path"])

    engine_errors: Dict[str, str] = {}
    manifest_entries: List[manifest_svc.ManifestArtifact] = []
    mysql_marker = None
    postgres_wal_range = None
    mysql_ok = False
    postgres_ok = False
    bootstrap_notes: List[str] = []

    disk = prechecks.check_disk_space(job_dir)
    if not disk.ok:
        return _finalize_failed(job, disk.message, dry_run=dry_run)

    mysql_conn = prechecks.check_mysql_connectivity(job.base_mysql)
    if not mysql_conn.ok:
        return _finalize_failed(job, mysql_conn.message, dry_run=dry_run)

    if job.job_type == BackupJob.JOB_TYPE_INCREMENTAL:
        parent = job.parent_job or resolve_incremental_parent(job.base_mysql)
        if not parent:
            return _finalize_failed(
                job,
                "No hay un backup full completado para esta base MySQL. Ejecute un full primero.",
                dry_run=dry_run,
            )
        job.parent_job = parent
        job.save(update_fields=["parent_job"])

        binlog_check = prechecks.check_mysql_binlog_enabled(job.base_mysql)
        if not binlog_check.ok:
            return _finalize_failed(job, binlog_check.message, dry_run=dry_run)

        wal_check = prechecks.check_postgres_wal_archive_dir(for_incremental=True)
        if not wal_check.ok:
            engine_errors["postgres"] = wal_check.message
        else:
            parent_wal = _parent_wal_files(parent)
            pg_result = postgres_backup.run_wal_incremental(
                job_dir, parent_wal_files=parent_wal, dry_run=dry_run
            )
            if pg_result.success:
                postgres_ok = True
                postgres_wal_range = pg_result.wal_range
                manifest_entries.extend(
                    _artifact_entries_from_paths(
                        BackupArtifact.ENGINE_POSTGRES_WAL,
                        pg_result.relative_paths,
                        pg_result.absolute_paths,
                    )
                )
            else:
                engine_errors["postgres"] = pg_result.error

        start_file = parent.mysql_binlog_file
        start_pos = parent.mysql_binlog_pos
        if not start_file or start_pos is None:
            engine_errors["mysql"] = (
                "El backup full padre no tiene marcador binlog. "
                "Ejecute un nuevo full con log_bin=ON."
            )
        else:
            mysql_result = mysql_backup.run_mysqlbinlog_incremental(
                job.base_mysql,
                job_dir,
                start_file=start_file,
                start_pos=int(start_pos),
                dry_run=dry_run,
            )
            if mysql_result.success:
                mysql_ok = True
                mysql_marker = {
                    "file": mysql_result.binlog_file,
                    "position": mysql_result.binlog_pos,
                }
                job.mysql_binlog_file = mysql_result.binlog_file or ""
                job.mysql_binlog_pos = mysql_result.binlog_pos
                manifest_entries.extend(
                    _artifact_entries_from_paths(
                        BackupArtifact.ENGINE_MYSQL_BINLOG,
                        mysql_result.relative_paths,
                        mysql_result.absolute_paths,
                    )
                )
            else:
                engine_errors["mysql"] = mysql_result.error

    else:
        mysql_result = mysql_backup.run_mysqldump(
            job.base_mysql,
            job_dir,
            include_empresas=job.include_empresas_table,
            dry_run=dry_run,
        )
        if mysql_result.success:
            mysql_ok = True
            job.mysql_binlog_file = mysql_result.binlog_file or ""
            job.mysql_binlog_pos = mysql_result.binlog_pos
            mysql_marker = {
                "file": mysql_result.binlog_file,
                "position": mysql_result.binlog_pos,
            }
            manifest_entries.extend(
                _artifact_entries_from_paths(
                    BackupArtifact.ENGINE_MYSQL,
                    mysql_result.relative_paths,
                    mysql_result.absolute_paths,
                )
            )
        else:
            engine_errors["mysql"] = mysql_result.error

        pg_result = postgres_backup.run_pg_dump(job_dir, dry_run=dry_run)
        if pg_result.success:
            postgres_ok = True
            postgres_wal_range = pg_result.wal_range
            manifest_entries.extend(
                _artifact_entries_from_paths(
                    BackupArtifact.ENGINE_POSTGRES,
                    pg_result.relative_paths,
                    pg_result.absolute_paths,
                )
            )
        else:
            engine_errors["postgres"] = pg_result.error

        # Capa B: bootstrap (.env cifrado + AFIP + inventory) — solo full
        boot = bootstrap_svc.build_bootstrap_bundle(
            job_dir,
            job_id=str(job.id),
            base_mysql=job.base_mysql,
            dry_run=dry_run,
        )
        if boot.success and boot.relative_paths:
            manifest_entries.extend(
                _artifact_entries_from_paths(
                    BackupArtifact.ENGINE_BOOTSTRAP,
                    boot.relative_paths,
                    boot.absolute_paths,
                )
            )
        # Avisos (p. ej. sin frase → sin .env) no marcan fallo de engines de datos
        bootstrap_notes = list(boot.warnings or [])
        if not boot.success:
            bootstrap_notes.append(boot.error or "Error al generar paquete bootstrap.")

    manifest_path = job_dir / "manifest.json"
    manifest_data = manifest_svc.build_manifest_data(
        job_id=str(job.id),
        tipo=job.job_type,
        parent_job_id=str(job.parent_job_id) if job.parent_job_id else None,
        base_mysql=job.base_mysql,
        include_empresas_table=job.include_empresas_table,
        artifact_entries=manifest_entries,
        mysql_binlog_marker=mysql_marker,
        postgres_wal_range=postgres_wal_range,
        engine_errors=engine_errors,
    )
    manifest_svc.write_manifest(manifest_path, manifest_data)
    job.manifest_path = str(manifest_path)

    manifest_entries.append(
        manifest_svc.ManifestArtifact(
            engine=BackupArtifact.ENGINE_MANIFEST,
            path="manifest.json",
            sha256=manifest_svc.sha256_file(manifest_path),
            size=manifest_path.stat().st_size,
        )
    )

    _register_artifacts(job, manifest_entries)

    _write_log(log_path, job, engine_errors, mysql_ok, postgres_ok, bootstrap_notes=bootstrap_notes)

    if job.job_type == BackupJob.JOB_TYPE_INCREMENTAL:
        if mysql_ok and postgres_ok:
            job.status = BackupJob.STATUS_COMPLETED
            job.error_summary = ""
        elif mysql_ok or postgres_ok:
            job.status = BackupJob.STATUS_PARTIAL_FAILED
            job.error_summary = _format_engine_errors(engine_errors)
        else:
            job.status = BackupJob.STATUS_FAILED
            job.error_summary = _format_engine_errors(engine_errors)
    else:
        if mysql_ok and postgres_ok:
            job.status = BackupJob.STATUS_COMPLETED
            job.error_summary = ""
        elif mysql_ok or postgres_ok:
            job.status = BackupJob.STATUS_PARTIAL_FAILED
            job.error_summary = _format_engine_errors(engine_errors)
        else:
            job.status = BackupJob.STATUS_FAILED
            job.error_summary = _format_engine_errors(engine_errors)

    job.finished_at = timezone.now()
    job.save(
        update_fields=[
            "status",
            "error_summary",
            "finished_at",
            "manifest_path",
            "mysql_binlog_file",
            "mysql_binlog_pos",
        ]
    )

    if job.status == BackupJob.STATUS_COMPLETED:
        upload = sftp_upload.upload_job_directory(job_dir, str(job.id))
        if not backup_config.effective_sftp_enabled():
            job.remote_upload_status = BackupJob.REMOTE_SKIPPED
        elif upload.success:
            job.remote_upload_status = BackupJob.REMOTE_SUCCESS
        else:
            job.remote_upload_status = BackupJob.REMOTE_FAILED
            job.error_summary = (job.error_summary + "\n" if job.error_summary else "") + upload.message
        job.save(update_fields=["remote_upload_status", "error_summary"])
    elif job.status in (BackupJob.STATUS_PARTIAL_FAILED, BackupJob.STATUS_FAILED):
        job.remote_upload_status = BackupJob.REMOTE_SKIPPED
        job.save(update_fields=["remote_upload_status"])

    backup_notify.notify_backup_job(job, dry_run=dry_run)
    return job


def _format_engine_errors(errors: Dict[str, str]) -> str:
    parts = []
    for engine, msg in errors.items():
        label = {
            "mysql": "MySQL",
            "postgres": "PostgreSQL",
            "bootstrap": "Bootstrap",
        }.get(engine, engine)
        parts.append(f"{label}: {msg}")
    return "\n".join(parts)


def _finalize_failed(job: BackupJob, message: str, *, dry_run: bool = False) -> BackupJob:
    job.status = BackupJob.STATUS_FAILED
    job.error_summary = message
    job.finished_at = timezone.now()
    job.remote_upload_status = BackupJob.REMOTE_SKIPPED
    job.save(
        update_fields=["status", "error_summary", "finished_at", "remote_upload_status"]
    )
    backup_notify.notify_backup_job(job, dry_run=dry_run)
    return job


def _write_log(
    log_path: Path,
    job: BackupJob,
    engine_errors: Dict[str, str],
    mysql_ok: bool,
    postgres_ok: bool,
    bootstrap_notes: Optional[List[str]] = None,
) -> None:
    lines = [
        f"Job {job.id} tipo={job.job_type} base={job.base_mysql}",
        f"Inicio: {job.started_at}",
        f"MySQL OK: {mysql_ok}",
        f"Postgres OK: {postgres_ok}",
    ]
    if engine_errors:
        lines.append("Errores por engine:")
        for eng, msg in engine_errors.items():
            lines.append(f"  - {eng}: {msg}")
    if bootstrap_notes:
        lines.append("Avisos bootstrap:")
        for note in bootstrap_notes:
            lines.append(f"  - {note}")
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def prune_old_backups(retention_days: int | None = None) -> int:
    """Elimina directorios de jobs más antiguos que retention_days. Devuelve cantidad purgada."""
    days = retention_days or backup_config.effective_retention_days()
    root = Path(backup_config.effective_local_root())
    if not root.is_dir():
        return 0
    cutoff = timezone.now() - timedelta(days=days)
    purged = 0
    for job in BackupJob.objects.filter(created_at__lt=cutoff):
        job_dir = job_directory(job)
        if job_dir.is_dir():
            import shutil

            shutil.rmtree(job_dir, ignore_errors=True)
            purged += 1
    return purged
