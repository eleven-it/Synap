"""Backup MySQL (mysqldump + mysqlbinlog incremental)."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from django.conf import settings

from core.backup.services.prechecks import get_mysql_binlog_position

logger = logging.getLogger(__name__)


@dataclass
class MySQLBackupResult:
    success: bool
    relative_paths: List[str]
    absolute_paths: List[Path]
    error: str = ""
    binlog_file: str = ""
    binlog_pos: Optional[int] = None


def _mysql_connection_args() -> List[str]:
    cfg = settings.DATABASES["mysql"]
    args = [
        "-h",
        str(cfg.get("HOST") or "localhost"),
        "-P",
        str(cfg.get("PORT") or 3306),
        "-u",
        str(cfg.get("USER") or ""),
    ]
    password = cfg.get("PASSWORD") or ""
    if password:
        args.append(f"-p{password}")
    return args


def run_mysqldump(
    base_mysql: str,
    job_dir: Path,
    *,
    include_empresas: bool = False,
    dry_run: bool = False,
) -> MySQLBackupResult:
    job_dir.mkdir(parents=True, exist_ok=True)
    rel_main = f"mysql/{base_mysql}.sql.gz"
    out_main = job_dir / rel_main
    out_main.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        out_main.write_bytes(b"DUMMY")
        paths = [rel_main]
        abs_paths = [out_main]
        if include_empresas:
            rel_emp = "mysql/empresas.sql.gz"
            (job_dir / rel_emp).write_bytes(b"DUMMY")
            paths.append(rel_emp)
            abs_paths.append(job_dir / rel_emp)
        return MySQLBackupResult(success=True, relative_paths=paths, absolute_paths=abs_paths)

    cmd = [
        "mysqldump",
        "--single-transaction",
        "--routines",
        "--triggers",
        *_mysql_connection_args(),
        base_mysql,
    ]
    try:
        with out_main.open("wb") as out_fh:
            proc = subprocess.run(
                cmd,
                stdout=out_fh,
                stderr=subprocess.PIPE,
                check=False,
            )
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip()
            return MySQLBackupResult(
                success=False,
                relative_paths=[],
                absolute_paths=[],
                error=f"mysqldump falló para {base_mysql}: {err or proc.returncode}",
            )
    except FileNotFoundError:
        return MySQLBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error="mysqldump no está instalado (instale default-mysql-client).",
        )
    except Exception as exc:
        return MySQLBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error=str(exc),
        )

    rel_paths = [rel_main]
    abs_paths = [out_main]

    if include_empresas:
        rel_emp = "mysql/empresas.sql.gz"
        out_emp = job_dir / rel_emp
        cmd_emp = ["mysqldump", "--single-transaction", *_mysql_connection_args(), "empresas"]
        try:
            with out_emp.open("wb") as out_fh:
                proc = subprocess.run(cmd_emp, stdout=out_fh, stderr=subprocess.PIPE, check=False)
            if proc.returncode != 0:
                err = proc.stderr.decode("utf-8", errors="replace").strip()
                return MySQLBackupResult(
                    success=False,
                    relative_paths=rel_paths,
                    absolute_paths=abs_paths,
                    error=f"mysqldump de empresas falló: {err or proc.returncode}",
                )
            rel_paths.append(rel_emp)
            abs_paths.append(out_emp)
        except Exception as exc:
            return MySQLBackupResult(
                success=False,
                relative_paths=rel_paths,
                absolute_paths=abs_paths,
                error=f"Error al respaldar base empresas: {exc}",
            )

    binlog_file, binlog_pos, binlog_err = get_mysql_binlog_position(base_mysql)
    if binlog_err:
        logger.warning("No se capturó marcador binlog post-full: %s", binlog_err)

    return MySQLBackupResult(
        success=True,
        relative_paths=rel_paths,
        absolute_paths=abs_paths,
        binlog_file=binlog_file or "",
        binlog_pos=binlog_pos,
    )


def run_mysqlbinlog_incremental(
    base_mysql: str,
    job_dir: Path,
    *,
    start_file: str,
    start_pos: int,
    dry_run: bool = False,
) -> MySQLBackupResult:
    job_dir.mkdir(parents=True, exist_ok=True)
    rel_path = f"mysql_binlog/incremental_{start_file}_{start_pos}.sql"
    out_path = job_dir / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        out_path.write_text("-- incremental dummy\n", encoding="utf-8")
        bf, bp, _ = get_mysql_binlog_position(base_mysql)
        return MySQLBackupResult(
            success=True,
            relative_paths=[rel_path],
            absolute_paths=[out_path],
            binlog_file=bf or start_file,
            binlog_pos=bp or start_pos + 1,
        )

    cfg = settings.DATABASES["mysql"]
    cmd = [
        "mysqlbinlog",
        "--read-from-remote-server",
        f"--host={cfg.get('HOST') or 'localhost'}",
        f"--port={cfg.get('PORT') or 3306}",
        f"--user={cfg.get('USER') or ''}",
        f"--start-position={start_pos}",
        start_file,
    ]
    password = cfg.get("PASSWORD") or ""
    if password:
        cmd.insert(-1, f"--password={password}")

    try:
        with out_path.open("wb") as out_fh:
            proc = subprocess.run(cmd, stdout=out_fh, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace").strip()
            return MySQLBackupResult(
                success=False,
                relative_paths=[],
                absolute_paths=[],
                error=f"mysqlbinlog falló: {err or proc.returncode}",
            )
    except FileNotFoundError:
        return MySQLBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error="mysqlbinlog no está instalado (instale default-mysql-client).",
        )
    except Exception as exc:
        return MySQLBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error=str(exc),
        )

    binlog_file, binlog_pos, _ = get_mysql_binlog_position(base_mysql)
    return MySQLBackupResult(
        success=True,
        relative_paths=[rel_path],
        absolute_paths=[out_path],
        binlog_file=binlog_file or start_file,
        binlog_pos=binlog_pos or start_pos,
    )
