"""Manifest JSON auditable para jobs de backup."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ManifestArtifact:
    engine: str
    path: str
    sha256: str
    size: int


@dataclass
class ManifestData:
    job_id: str
    created_at: str
    tipo: str
    parent_job_id: Optional[str]
    base_mysql: str
    include_empresas_table: bool
    engines: List[str] = field(default_factory=list)
    artifacts: List[ManifestArtifact] = field(default_factory=list)
    mysql_binlog_marker: Optional[Dict[str, Any]] = None
    postgres_wal_range: Optional[Dict[str, Any]] = None
    engine_errors: Dict[str, str] = field(default_factory=dict)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path, data: ManifestData) -> Dict[str, Any]:
    """Escribe manifest.json y devuelve el dict serializado."""
    payload: Dict[str, Any] = {
        "job_id": data.job_id,
        "created_at": data.created_at,
        "tipo": data.tipo,
        "parent_job_id": data.parent_job_id,
        "base_mysql": data.base_mysql,
        "include_empresas_table": data.include_empresas_table,
        "engines": list(data.engines),
        "artifacts": [
            {
                "engine": a.engine,
                "path": a.path,
                "sha256": a.sha256,
                "size": a.size,
            }
            for a in data.artifacts
        ],
        "mysql_binlog_marker": data.mysql_binlog_marker,
        "postgres_wal_range": data.postgres_wal_range,
        "engine_errors": data.engine_errors,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def read_manifest(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest_data(
    *,
    job_id: str,
    tipo: str,
    parent_job_id: Optional[str],
    base_mysql: str,
    include_empresas_table: bool,
    artifact_entries: List[ManifestArtifact],
    mysql_binlog_marker: Optional[Dict[str, Any]] = None,
    postgres_wal_range: Optional[Dict[str, Any]] = None,
    engine_errors: Optional[Dict[str, str]] = None,
) -> ManifestData:
    engines = sorted({a.engine for a in artifact_entries})
    return ManifestData(
        job_id=str(job_id),
        created_at=datetime.now(timezone.utc).isoformat(),
        tipo=tipo,
        parent_job_id=str(parent_job_id) if parent_job_id else None,
        base_mysql=base_mysql,
        include_empresas_table=include_empresas_table,
        engines=engines,
        artifacts=artifact_entries,
        mysql_binlog_marker=mysql_binlog_marker,
        postgres_wal_range=postgres_wal_range,
        engine_errors=engine_errors or {},
    )
