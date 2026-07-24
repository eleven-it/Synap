"""Lectura de configuración operativa de backup (singleton BackupSettings)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from django.conf import settings
from django.utils import timezone

from core.backup.models import BackupJob, BackupSettings, default_backup_schedule
from core.backup.services import secrets as backup_secrets

# Convención dow en schedule_json: 0 = lunes … 6 = domingo (datetime.weekday()).
DOW_LABELS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")


def get_backup_settings() -> BackupSettings:
    return BackupSettings.get_solo()


def _fallback(name: str, default):
    return getattr(settings, name, default)


def effective_local_root() -> str:
    bs = get_backup_settings()
    root = (bs.local_root or "").strip()
    if root:
        return root
    return str(_fallback("BACKUP_LOCAL_ROOT", "/var/lib/synap/backups"))


def effective_retention_days() -> int:
    bs = get_backup_settings()
    if bs.retention_days:
        return int(bs.retention_days)
    return int(_fallback("BACKUP_RETENTION_DAYS", 30))


def effective_pg_wal_archive_dir() -> str:
    bs = get_backup_settings()
    wal = (bs.pg_wal_archive_dir or "").strip()
    if wal:
        return wal
    return str(_fallback("BACKUP_PG_WAL_ARCHIVE_DIR", "") or "").strip()


def effective_sftp_enabled() -> bool:
    bs = get_backup_settings()
    if bs.sftp_host or bs.sftp_user:
        return bool(bs.sftp_enabled)
    return bool(_fallback("BACKUP_SFTP_ENABLED", False))


def effective_sftp_host() -> str:
    bs = get_backup_settings()
    host = (bs.sftp_host or "").strip()
    if host:
        return host
    return str(_fallback("BACKUP_SFTP_HOST", "") or "").strip()


def effective_sftp_port() -> int:
    bs = get_backup_settings()
    if bs.sftp_port:
        return int(bs.sftp_port)
    return int(_fallback("BACKUP_SFTP_PORT", 22))


def effective_sftp_user() -> str:
    bs = get_backup_settings()
    user = (bs.sftp_user or "").strip()
    if user:
        return user
    return str(_fallback("BACKUP_SFTP_USER", "") or "").strip()


def effective_sftp_remote_path() -> str:
    bs = get_backup_settings()
    path = (bs.sftp_remote_path or "").strip()
    if path:
        return path
    return str(_fallback("BACKUP_SFTP_REMOTE_PATH", "/synap/backups") or "/synap/backups")


def effective_sftp_key_path() -> str:
    bs = get_backup_settings()
    key = (bs.sftp_key_path or "").strip()
    if key:
        return key
    return str(_fallback("BACKUP_SFTP_KEY_PATH", "") or "").strip()


def sftp_password_plain(settings_obj: BackupSettings | None = None) -> str:
    bs = settings_obj or get_backup_settings()
    if bs.sftp_password_encrypted:
        return backup_secrets.decrypt_secret(bs.sftp_password_encrypted)
    return str(_fallback("BACKUP_SFTP_PASSWORD", "") or "").strip()


def set_sftp_password(settings_obj: BackupSettings, plain: str | None) -> None:
    value = (plain or "").strip()
    if not value:
        return
    settings_obj.sftp_password_encrypted = backup_secrets.encrypt_secret(value)


def normalize_schedule(rules: list | None) -> list:
    if not rules:
        return default_backup_schedule()
    normalized = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        try:
            dow = int(rule.get("dow"))
        except (TypeError, ValueError):
            continue
        if dow < 0 or dow > 6:
            continue
        time_str = str(rule.get("time") or "").strip()
        if len(time_str) != 5 or time_str[2] != ":":
            continue
        job_type = str(rule.get("job_type") or "").strip()
        if job_type not in (BackupJob.JOB_TYPE_FULL, BackupJob.JOB_TYPE_INCREMENTAL):
            continue
        normalized.append({"dow": dow, "time": time_str, "job_type": job_type})
    return normalized or default_backup_schedule()


def synap_weekday(dt: datetime) -> int:
    """0=lunes … 6=domingo en la zona horaria del datetime."""
    return dt.weekday()


def schedule_rule_matches(
    rule: dict,
    now: datetime,
    *,
    match_minute: bool = True,
) -> bool:
    if synap_weekday(now) != int(rule.get("dow")):
        return False
    time_str = str(rule.get("time") or "").strip()
    parts = time_str.split(":")
    if len(parts) != 2:
        return False
    try:
        rule_hour = int(parts[0])
        rule_minute = int(parts[1])
    except ValueError:
        return False
    if match_minute:
        return now.hour == rule_hour and now.minute == rule_minute
    return now.hour == rule_hour


def matching_schedule_rules(
    now: datetime | None = None,
    *,
    match_minute: bool = True,
) -> List[dict]:
    bs = get_backup_settings()
    now = now or timezone.localtime()
    rules = normalize_schedule(bs.schedule_json)
    return [r for r in rules if schedule_rule_matches(r, now, match_minute=match_minute)]


def has_recent_scheduled_job(
    base_mysql: str,
    job_type: str,
    *,
    within_minutes: int = 50,
) -> bool:
    cutoff = timezone.now() - timedelta(minutes=within_minutes)
    return BackupJob.objects.filter(
        scheduled=True,
        base_mysql=base_mysql,
        job_type=job_type,
        created_at__gte=cutoff,
    ).exists()


def next_schedule_hint(now: datetime | None = None) -> Optional[str]:
    """Texto orientativo del próximo slot programado (no sustituye cron)."""
    bs = get_backup_settings()
    if not bs.enabled_auto:
        return None
    now = now or timezone.localtime()
    rules = normalize_schedule(bs.schedule_json)
    if not rules:
        return None
    candidates: List[Tuple[datetime, dict]] = []
    for day_offset in range(8):
        day = (now + timedelta(days=day_offset)).replace(second=0, microsecond=0)
        for rule in rules:
            time_str = str(rule.get("time") or "00:00")
            parts = time_str.split(":")
            try:
                hour, minute = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                continue
            target_dow = int(rule.get("dow"))
            candidate = day.replace(hour=hour, minute=minute)
            while synap_weekday(candidate) != target_dow:
                candidate += timedelta(days=1)
            if candidate <= now:
                continue
            candidates.append((candidate, rule))
    if not candidates:
        return None
    candidate, rule = min(candidates, key=lambda x: x[0])
    dow_label = DOW_LABELS[int(rule["dow"])]
    tipo = "completo" if rule["job_type"] == BackupJob.JOB_TYPE_FULL else "incremental"
    return f"Próximo: {dow_label} {candidate.strftime('%d/%m/%Y %H:%M')} ({tipo})"
