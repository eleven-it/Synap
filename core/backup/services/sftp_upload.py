"""Upload remoto SFTP de artefactos de backup."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

try:
    import paramiko
except ImportError:  # pragma: no cover
    paramiko = None

logger = logging.getLogger(__name__)


@dataclass
class SftpUploadResult:
    success: bool
    message: str = ""


def upload_job_directory(job_dir: Path, job_id: str) -> SftpUploadResult:
    if not getattr(settings, "BACKUP_SFTP_ENABLED", False):
        return SftpUploadResult(success=True, message="SFTP deshabilitado (skipped).")

    host = (getattr(settings, "BACKUP_SFTP_HOST", "") or "").strip()
    user = (getattr(settings, "BACKUP_SFTP_USER", "") or "").strip()
    remote_base = (getattr(settings, "BACKUP_SFTP_REMOTE_PATH", "") or "/synap/backups").strip()

    if not host or not user:
        return SftpUploadResult(
            success=False,
            message="SFTP habilitado pero faltan BACKUP_SFTP_HOST o BACKUP_SFTP_USER.",
        )

    if paramiko is None:
        return SftpUploadResult(success=False, message="paramiko no está instalado.")

    port = int(getattr(settings, "BACKUP_SFTP_PORT", 22) or 22)
    password = (getattr(settings, "BACKUP_SFTP_PASSWORD", "") or "").strip()
    key_path = (getattr(settings, "BACKUP_SFTP_KEY_PATH", "") or "").strip()

    transport = None
    sftp = None
    try:
        transport = paramiko.Transport((host, port))
        if key_path:
            pkey = paramiko.RSAKey.from_private_key_file(key_path)
            transport.connect(username=user, pkey=pkey)
        else:
            transport.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        remote_job_dir = f"{remote_base.rstrip('/')}/{job_id}"
        _mkdir_p_sftp(sftp, remote_job_dir)

        for local_file in sorted(job_dir.rglob("*")):
            if not local_file.is_file():
                continue
            rel = local_file.relative_to(job_dir).as_posix()
            remote_path = f"{remote_job_dir}/{rel}"
            remote_parent = "/".join(remote_path.split("/")[:-1])
            if remote_parent:
                _mkdir_p_sftp(sftp, remote_parent)
            sftp.put(str(local_file), remote_path)

        return SftpUploadResult(success=True, message=f"Upload SFTP OK → {remote_job_dir}")
    except Exception as exc:
        logger.exception("SFTP upload falló para job %s: %s", job_id, exc)
        return SftpUploadResult(success=False, message=f"Upload SFTP falló: {exc}")
    finally:
        if sftp is not None:
            try:
                sftp.close()
            except Exception:
                pass
        if transport is not None:
            try:
                transport.close()
            except Exception:
                pass


def _mkdir_p_sftp(sftp, remote_dir: str) -> None:
    parts = [p for p in remote_dir.split("/") if p]
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else f"/{part}"
        try:
            sftp.stat(current)
        except OSError:
            sftp.mkdir(current)
