"""Backup PostgreSQL (pg_dump full + copia WAL incremental)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from django.conf import settings

from core.backup.services import config as backup_config

logger = logging.getLogger(__name__)


@dataclass
class PostgresBackupResult:
    success: bool
    relative_paths: List[str]
    absolute_paths: List[Path]
    error: str = ""
    wal_range: Optional[Dict[str, object]] = None


def _pg_env() -> dict:
    cfg = settings.DATABASES["default"]
    env = os.environ.copy()
    if cfg.get("PASSWORD"):
        env["PGPASSWORD"] = str(cfg["PASSWORD"])
    return env


def _pg_connection_args() -> List[str]:
    cfg = settings.DATABASES["default"]
    return [
        "-h",
        str(cfg.get("HOST") or "localhost"),
        "-p",
        str(cfg.get("PORT") or 5432),
        "-U",
        str(cfg.get("USER") or ""),
        str(cfg.get("NAME") or "postgres"),
    ]


def run_pg_dump(job_dir: Path, *, dry_run: bool = False) -> PostgresBackupResult:
    job_dir.mkdir(parents=True, exist_ok=True)
    rel_path = "postgres/full.dump"
    out_path = job_dir / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        out_path.write_bytes(b"PGDMP")
        return PostgresBackupResult(
            success=True,
            relative_paths=[rel_path],
            absolute_paths=[out_path],
            wal_range={"mode": "full_logical"},
        )

    cmd = ["pg_dump", "-Fc", *_pg_connection_args()]
    try:
        with out_path.open("wb") as out_fh:
            proc = subprocess.run(
                cmd,
                stdout=out_fh,
                stderr=subprocess.PIPE,
                env=_pg_env(),
                check=False,
            )
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip()
            return PostgresBackupResult(
                success=False,
                relative_paths=[],
                absolute_paths=[],
                error=f"pg_dump falló: {err or proc.returncode}",
            )
    except FileNotFoundError:
        return PostgresBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error="pg_dump no está instalado (instale postgresql-client).",
        )
    except Exception as exc:
        return PostgresBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error=str(exc),
        )

    return PostgresBackupResult(
        success=True,
        relative_paths=[rel_path],
        absolute_paths=[out_path],
        wal_range={"mode": "full_logical"},
    )


def _list_wal_segments(wal_dir: Path) -> List[Path]:
    files = []
    for pattern in ("*.wal", "[0-9A-F]*"):
        files.extend(wal_dir.glob(pattern))
    return sorted({p for p in files if p.is_file()}, key=lambda p: p.name)


def run_wal_incremental(
    job_dir: Path,
    *,
    parent_wal_files: Optional[Set[str]] = None,
    dry_run: bool = False,
) -> PostgresBackupResult:
    wal_dir_str = backup_config.effective_pg_wal_archive_dir()
    if not wal_dir_str:
        return PostgresBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error=(
                "El directorio WAL archivado no está configurado. "
                "Configúrelo en /core/backups/configuracion/ y archive_mode en PostgreSQL."
            ),
        )
    wal_dir = Path(wal_dir_str)
    if not wal_dir.is_dir():
        return PostgresBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error=f"El directorio WAL archivado no existe: {wal_dir}",
        )

    parent_set = parent_wal_files or set()
    segments = _list_wal_segments(wal_dir)
    new_segments = [s for s in segments if s.name not in parent_set]

    if not new_segments and not dry_run:
        return PostgresBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error=(
                f"No hay segmentos WAL nuevos en {wal_dir}. "
                "Verifique archive_mode y archive_command en PostgreSQL."
            ),
        )

    dest_dir = job_dir / "postgres_wal"
    dest_dir.mkdir(parents=True, exist_ok=True)
    rel_paths: List[str] = []
    abs_paths: List[Path] = []

    if dry_run:
        dummy = dest_dir / "000000010000000000000001"
        dummy.write_bytes(b"WAL")
        rel_paths.append(f"postgres_wal/{dummy.name}")
        abs_paths.append(dummy)
        return PostgresBackupResult(
            success=True,
            relative_paths=rel_paths,
            absolute_paths=abs_paths,
            wal_range={"files": [dummy.name], "source_dir": str(wal_dir)},
        )

    for seg in new_segments:
        target = dest_dir / seg.name
        shutil.copy2(seg, target)
        rel_paths.append(f"postgres_wal/{seg.name}")
        abs_paths.append(target)

    return PostgresBackupResult(
        success=True,
        relative_paths=rel_paths,
        absolute_paths=abs_paths,
        wal_range={
            "files": [p.name for p in new_segments],
            "source_dir": str(wal_dir),
        },
    )
