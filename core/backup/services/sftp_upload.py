"""Upload remoto SFTP de artefactos de backup."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from core.backup.services import config as backup_config

try:
    import paramiko
except ImportError:  # pragma: no cover
    paramiko = None

logger = logging.getLogger(__name__)


@dataclass
class SftpUploadResult:
    success: bool
    message: str = ""


def _connect_sftp(
    *,
    host: str,
    port: int,
    user: str,
    password: str = "",
    key_path: str = "",
):
    if paramiko is None:
        raise RuntimeError("paramiko no está instalado.")
    transport = paramiko.Transport((host, port))
    if key_path:
        pkey = paramiko.RSAKey.from_private_key_file(key_path)
        transport.connect(username=user, pkey=pkey)
    else:
        transport.connect(username=user, password=password)
    return transport, paramiko.SFTPClient.from_transport(transport)


def test_sftp_connection(
    *,
    host: str,
    port: int,
    user: str,
    password: str = "",
    key_path: str = "",
    remote_path: str = "/synap/backups",
) -> SftpUploadResult:
    host = (host or "").strip()
    user = (user or "").strip()
    if not host or not user:
        return SftpUploadResult(
            success=False,
            message="Indique host y usuario SFTP.",
        )
    if paramiko is None:
        return SftpUploadResult(success=False, message="paramiko no está instalado.")

    transport = None
    sftp = None
    try:
        transport, sftp = _connect_sftp(
            host=host,
            port=port,
            user=user,
            password=password,
            key_path=(key_path or "").strip(),
        )
        remote_base = (remote_path or "/synap/backups").strip()
        _mkdir_p_sftp(sftp, remote_base)
        return SftpUploadResult(success=True, message=f"Conexión SFTP OK ({host}:{port}).")
    except Exception as exc:
        logger.exception("Test SFTP falló: %s", exc)
        return SftpUploadResult(success=False, message=f"Conexión SFTP falló: {exc}")
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


def upload_job_directory(job_dir: Path, job_id: str) -> SftpUploadResult:
    if not backup_config.effective_sftp_enabled():
        return SftpUploadResult(success=True, message="SFTP deshabilitado (skipped).")

    host = backup_config.effective_sftp_host()
    user = backup_config.effective_sftp_user()
    remote_base = backup_config.effective_sftp_remote_path()

    if not host or not user:
        return SftpUploadResult(
            success=False,
            message="SFTP habilitado pero faltan host o usuario en la configuración.",
        )

    if paramiko is None:
        return SftpUploadResult(success=False, message="paramiko no está instalado.")

    port = backup_config.effective_sftp_port()
    password = backup_config.sftp_password_plain()
    key_path = backup_config.effective_sftp_key_path()

    transport = None
    sftp = None
    try:
        transport, sftp = _connect_sftp(
            host=host,
            port=port,
            user=user,
            password=password,
            key_path=key_path,
        )

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
