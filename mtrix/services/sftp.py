"""SFTP del portal MTRIX (credenciales por empresa, no backup)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from datetime import date

from mtrix.models import MtrixArtifact, MtrixConfig, MtrixJob
from mtrix.services.crypto import decrypt_secret

try:
    import paramiko
except ImportError:  # pragma: no cover
    paramiko = None

logger = logging.getLogger(__name__)


@dataclass
class SftpResult:
    success: bool
    message: str = ""


def _connect(host: str, port: int, user: str, password: str = "", key_path: str = ""):
    if paramiko is None:
        raise RuntimeError("paramiko no está instalado.")
    transport = paramiko.Transport((host, int(port or 22)))
    if key_path:
        pkey = paramiko.RSAKey.from_private_key_file(key_path)
        transport.connect(username=user, pkey=pkey)
    else:
        transport.connect(username=user, password=password)
    return transport, paramiko.SFTPClient.from_transport(transport)


def _mkdir_p(sftp, remote_path: str) -> None:
    parts = [p for p in remote_path.replace("\\", "/").split("/") if p]
    current = "" if not remote_path.startswith("/") else "/"
    for part in parts:
        current = f"{current.rstrip('/')}/{part}"
        try:
            sftp.stat(current)
        except OSError:
            sftp.mkdir(current)


def test_connection(cfg: MtrixConfig) -> SftpResult:
    host = (cfg.sftp_host or "").strip()
    user = (cfg.sftp_user or "").strip()
    if not host or not user:
        return SftpResult(False, "Indique host y usuario SFTP.")
    if paramiko is None:
        return SftpResult(False, "paramiko no está instalado.")
    transport = None
    sftp = None
    try:
        transport, sftp = _connect(
            host,
            cfg.sftp_port or 22,
            user,
            decrypt_secret(cfg.sftp_password_encrypted or ""),
            (cfg.sftp_key_path or "").strip(),
        )
        remote = (cfg.sftp_remote_path or "/").strip() or "/"
        _mkdir_p(sftp, remote)
        return SftpResult(True, f"Conexión SFTP OK ({host}:{cfg.sftp_port or 22}).")
    except Exception as exc:
        logger.exception("Test SFTP Mtrix falló: %s", exc)
        return SftpResult(False, f"Conexión SFTP falló: {exc}")
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


def avanzar_marca_agua_vd(cfg: MtrixConfig, job: MtrixJob) -> bool:
    """Avanza last_vd_enviado_hasta si el envío de la ventana fue OK. No retrocede."""
    if not job.fecha_hasta:
        return False
    arts = list(job.artifacts.all())
    if any(a.sftp_status == MtrixArtifact.SftpStatus.FAILED for a in arts):
        return False
    if arts and all(a.sftp_status == MtrixArtifact.SftpStatus.SKIPPED for a in arts):
        return False
    vds = [a for a in arts if a.tipo == MtrixArtifact.Tipo.VD]
    if vds and any(a.sftp_status != MtrixArtifact.SftpStatus.SUCCESS for a in vds):
        return False
    nuevo = job.fecha_hasta
    if hasattr(nuevo, "isoformat"):
        pass
    else:
        nuevo = date.fromisoformat(str(nuevo)[:10])
    if cfg.last_vd_enviado_hasta and nuevo < cfg.last_vd_enviado_hasta:
        return False
    cfg.last_vd_enviado_hasta = nuevo
    cfg.save(update_fields=["last_vd_enviado_hasta"])
    return True


def enviar_job(job: MtrixJob, cfg: MtrixConfig) -> SftpResult:
    host = (cfg.sftp_host or "").strip()
    user = (cfg.sftp_user or "").strip()
    if not host or not user:
        for art in job.artifacts.all():
            art.sftp_status = MtrixArtifact.SftpStatus.SKIPPED
            art.sftp_message = "SFTP no configurado."
            art.save(update_fields=["sftp_status", "sftp_message"])
        return SftpResult(True, "SFTP no configurado (omitido).")
    if paramiko is None:
        return SftpResult(False, "paramiko no está instalado.")
    transport = None
    sftp = None
    try:
        transport, sftp = _connect(
            host,
            cfg.sftp_port or 22,
            user,
            decrypt_secret(cfg.sftp_password_encrypted or ""),
            (cfg.sftp_key_path or "").strip(),
        )
        remote = (cfg.sftp_remote_path or "/").strip() or "/"
        _mkdir_p(sftp, remote)
        media = Path(settings.MEDIA_ROOT)
        for art in job.artifacts.all():
            local = media / art.relative_path
            if not local.exists():
                art.sftp_status = MtrixArtifact.SftpStatus.FAILED
                art.sftp_message = "Archivo local no encontrado."
                art.save(update_fields=["sftp_status", "sftp_message"])
                continue
            dest = f"{remote.rstrip('/')}/{art.filename}"
            sftp.put(str(local), dest)
            art.sftp_status = MtrixArtifact.SftpStatus.SUCCESS
            art.sftp_message = dest
            art.save(update_fields=["sftp_status", "sftp_message"])
        if job.artifacts.filter(sftp_status=MtrixArtifact.SftpStatus.FAILED).exists():
            return SftpResult(False, "Envío SFTP incompleto: hay archivos con error.")
        avanzar_marca_agua_vd(cfg, job)
        return SftpResult(True, "Archivos enviados por SFTP.")
    except Exception as exc:
        logger.exception("Upload SFTP Mtrix falló: %s", exc)
        for art in job.artifacts.exclude(sftp_status=MtrixArtifact.SftpStatus.SUCCESS):
            art.sftp_status = MtrixArtifact.SftpStatus.FAILED
            art.sftp_message = str(exc)[:500]
            art.save(update_fields=["sftp_status", "sftp_message"])
        return SftpResult(False, f"Envío SFTP falló: {exc}")
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
