"""Paquete bootstrap DR: .env cifrado + AFIP + inventory (solo jobs full)."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cryptography.fernet import Fernet
from django.conf import settings

from core.backup.services import config as backup_config
from core.backup.services.manifest import sha256_file

logger = logging.getLogger(__name__)

ENGINE_BOOTSTRAP = "bootstrap"


@dataclass
class BootstrapResult:
    success: bool
    relative_paths: List[str] = field(default_factory=list)
    absolute_paths: List[Path] = field(default_factory=list)
    error: str = ""
    warnings: List[str] = field(default_factory=list)
    env_included: bool = False


def _fernet_from_passphrase(passphrase: str) -> Fernet:
    digest = hashlib.sha256(f"{passphrase}:synap-bootstrap-env-v1".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_env_bytes(plaintext: bytes, passphrase: str) -> bytes:
    return _fernet_from_passphrase(passphrase).encrypt(plaintext)


def decrypt_env_bytes(ciphertext: bytes, passphrase: str) -> bytes:
    return _fernet_from_passphrase(passphrase).decrypt(ciphertext)


def _git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(settings.BASE_DIR),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return (out or "").strip()
    except Exception:
        return ""


def _docker_compose_version() -> str:
    try:
        out = subprocess.check_output(
            ["docker", "compose", "version", "--short"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return (out or "").strip()
    except Exception:
        try:
            out = subprocess.check_output(
                ["docker", "--version"],
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=5,
            )
            return (out or "").strip()
        except Exception:
            return ""


def build_inventory(*, job_id: str, base_mysql: str) -> dict:
    db = settings.DATABASES.get("default") or {}
    mysql = settings.DATABASES.get("mysql") or {}
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "git_sha": _git_sha(),
        "docker_compose": _docker_compose_version(),
        "base_mysql_job": base_mysql,
        "postgres": {
            "NAME": db.get("NAME"),
            "HOST": db.get("HOST"),
            "PORT": str(db.get("PORT") or ""),
            "USER": db.get("USER"),
        },
        "mysql_settings": {
            "NAME": mysql.get("NAME"),
            "HOST": mysql.get("HOST"),
            "PORT": str(mysql.get("PORT") or ""),
            "USER": mysql.get("USER"),
        },
        "site_url": getattr(settings, "SITE_URL", "") or "",
        "environment": getattr(settings, "ENVIRONMENT", "") or "",
        "ports_hint": {
            "app": 8000,
            "postgres_host": 5435,
            "redis_host": 6381,
        },
        "runbook": "docs/general/RESTORE_RUNBOOK_SYNAP.md",
    }


def _afip_root() -> Path:
    certs = (getattr(settings, "FE_AFIP_CERT_STORAGE_DIR", "") or "").strip()
    if certs:
        return Path(certs).resolve().parent
    configured = (os.environ.get("SYNAP_AFIP_STORAGE") or "").strip()
    if configured:
        return Path(configured).resolve()
    return (Path(settings.BASE_DIR) / "private" / "afip").resolve()


def _copy_afip_tree(dest: Path) -> List[str]:
    """Copia certificados AFIP; devuelve rutas relativas bajo bootstrap/."""
    src = _afip_root()
    afip_dest = dest / "afip"
    copied: List[str] = []
    if not src.is_dir():
        return copied
    for root, _dirs, files in os.walk(src):
        for name in files:
            # Evitar basura temporal obvia
            if name.startswith(".") or name.endswith("~"):
                continue
            abs_src = Path(root) / name
            try:
                rel = abs_src.relative_to(src)
            except ValueError:
                continue
            target = afip_dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(abs_src, target)
            copied.append(f"bootstrap/afip/{rel.as_posix()}")
    return copied


def build_bootstrap_bundle(
    job_dir: Path,
    *,
    job_id: str,
    base_mysql: str,
    dry_run: bool = False,
) -> BootstrapResult:
    """
    Genera ``bootstrap/`` dentro del job full.

    - ``env.enc``: .env cifrado con frase de la UI (obligatoria para incluirlo).
    - ``inventory.json``: versiones/hosts sin secretos.
    - ``afip/``: certificados si existen.
    - ``RESTORE.md``: puntero al runbook.
    """
    warnings: List[str] = []
    bootstrap_dir = job_dir / "bootstrap"
    if dry_run:
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        inv = build_inventory(job_id=job_id, base_mysql=base_mysql)
        inv_path = bootstrap_dir / "inventory.json"
        inv_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
        readme = bootstrap_dir / "RESTORE.md"
        readme.write_text(
            "Paquete bootstrap (dry-run). Ver docs/general/RESTORE_RUNBOOK_SYNAP.md\n",
            encoding="utf-8",
        )
        rels = ["bootstrap/inventory.json", "bootstrap/RESTORE.md"]
        abs_paths = [bootstrap_dir / "inventory.json", readme]
        return BootstrapResult(
            success=True,
            relative_paths=rels,
            absolute_paths=abs_paths,
            env_included=False,
            warnings=["dry-run: no se cifró .env ni se copió AFIP"],
        )

    bootstrap_dir.mkdir(parents=True, exist_ok=True)
    relative_paths: List[str] = []
    absolute_paths: List[Path] = []

    # inventory.json
    inv = build_inventory(job_id=job_id, base_mysql=base_mysql)
    inv_path = bootstrap_dir / "inventory.json"
    inv_path.write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
    relative_paths.append("bootstrap/inventory.json")
    absolute_paths.append(inv_path)

    # RESTORE.md
    readme = bootstrap_dir / "RESTORE.md"
    readme.write_text(
        "\n".join(
            [
                "# Bootstrap Synap DR",
                "",
                "1. Descifre `env.enc` con la frase de cifrado (UI Copias de seguridad → Configuración).",
                "2. Guarde el resultado como `.env` en la raíz del repo.",
                "3. Copie `afip/` al volumen/ruta `SYNAP_AFIP_STORAGE` si aplica.",
                "4. Siga `docs/general/RESTORE_RUNBOOK_SYNAP.md`.",
                "",
                f"Job: {job_id}",
                f"Git SHA (si disponible): {inv.get('git_sha') or '—'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    relative_paths.append("bootstrap/RESTORE.md")
    absolute_paths.append(readme)

    # .env cifrado
    env_included = False
    passphrase = backup_config.bootstrap_passphrase_plain()
    env_path = Path(settings.BASE_DIR) / ".env"
    if not passphrase:
        warnings.append(
            "No hay frase de cifrado bootstrap en Configuración: "
            "no se incluyó .env. Configure la frase y vuelva a ejecutar un full."
        )
    elif not env_path.is_file():
        warnings.append(f"No se encontró archivo .env en {env_path}")
    else:
        plaintext = env_path.read_bytes()
        ciphertext = encrypt_env_bytes(plaintext, passphrase)
        enc_path = bootstrap_dir / "env.enc"
        enc_path.write_bytes(ciphertext)
        sha_path = bootstrap_dir / "env.sha256"
        sha_path.write_text(sha256_file(env_path) + "  .env\n", encoding="utf-8")
        relative_paths.extend(["bootstrap/env.enc", "bootstrap/env.sha256"])
        absolute_paths.extend([enc_path, sha_path])
        env_included = True

    # AFIP
    try:
        afip_rels = _copy_afip_tree(bootstrap_dir)
        for rel in afip_rels:
            relative_paths.append(rel)
            absolute_paths.append(job_dir / rel)
        if not afip_rels:
            warnings.append(
                "No se copiaron certificados AFIP "
                f"(directorio ausente o vacío: {_afip_root()})."
            )
    except Exception as exc:
        logger.warning("Copia AFIP bootstrap falló: %s", exc)
        warnings.append(f"No se pudo copiar AFIP: {exc}")

    return BootstrapResult(
        success=True,
        relative_paths=relative_paths,
        absolute_paths=absolute_paths,
        env_included=env_included,
        warnings=warnings,
    )
