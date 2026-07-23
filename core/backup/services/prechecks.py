"""Prechecks operativos antes de ejecutar backup."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from django.conf import settings

from core.mysql_pool import get_connection


@dataclass
class PrecheckResult:
    ok: bool
    message: str = ""


def check_disk_space(target_dir: Path, min_free_mb: int = 512) -> PrecheckResult:
    target_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(str(target_dir))
    free_mb = usage.free // (1024 * 1024)
    if free_mb < min_free_mb:
        return PrecheckResult(
            ok=False,
            message=(
                f"Espacio insuficiente en {target_dir}: "
                f"quedan {free_mb} MB libres (mínimo {min_free_mb} MB)."
            ),
        )
    return PrecheckResult(ok=True)


def check_mysql_connectivity(base_mysql: str) -> PrecheckResult:
    base = (base_mysql or "").strip()
    if not base:
        return PrecheckResult(ok=False, message="Debe seleccionar una base MySQL de producción.")
    try:
        with get_connection(base) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
        return PrecheckResult(ok=True)
    except Exception as exc:
        return PrecheckResult(
            ok=False,
            message=f"No se pudo conectar a MySQL ({base}): {exc}",
        )


def check_mysql_binlog_enabled(base_mysql: str) -> PrecheckResult:
    try:
        with get_connection(base_mysql) as conn:
            cur = conn.cursor()
            cur.execute("SHOW VARIABLES LIKE 'log_bin'")
            row = cur.fetchone()
            cur.close()
        if not row or str(row[1]).upper() != "ON":
            return PrecheckResult(
                ok=False,
                message=(
                    "El binary log de MySQL está desactivado (log_bin=OFF). "
                    "Habilítelo para backups incrementales."
                ),
            )
        return PrecheckResult(ok=True)
    except Exception as exc:
        return PrecheckResult(
            ok=False,
            message=f"No se pudo verificar log_bin en MySQL: {exc}",
        )


def check_postgres_wal_archive_dir(for_incremental: bool = False) -> PrecheckResult:
    wal_dir = (getattr(settings, "BACKUP_PG_WAL_ARCHIVE_DIR", "") or "").strip()
    if not wal_dir:
        return PrecheckResult(
            ok=False,
            message=(
                "BACKUP_PG_WAL_ARCHIVE_DIR no está configurado. "
                "Configure archive_mode y archive_command en PostgreSQL."
            ),
        )
    path = Path(wal_dir)
    if not path.is_dir():
        return PrecheckResult(
            ok=False,
            message=f"El directorio WAL archivado no existe: {wal_dir}",
        )
    if for_incremental:
        wal_files = list(path.glob("*.wal")) + list(path.glob("[0-9]*"))
        if not wal_files:
            return PrecheckResult(
                ok=False,
                message=(
                    f"No hay segmentos WAL archivados en {wal_dir}. "
                    "Verifique archive_mode y archive_command en PostgreSQL."
                ),
            )
    return PrecheckResult(ok=True)


def get_mysql_binlog_position(base_mysql: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Devuelve (file, position, error)."""
    try:
        with get_connection(base_mysql) as conn:
            cur = conn.cursor()
            cur.execute("SHOW MASTER STATUS")
            row = cur.fetchone()
            cur.close()
        if not row:
            return None, None, "SHOW MASTER STATUS no devolvió filas (¿log_bin desactivado?)."
        return str(row[0]), int(row[1]), None
    except Exception as exc:
        return None, None, str(exc)
