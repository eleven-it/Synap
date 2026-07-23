"""Tests manifest JSON backup DR."""

import json
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from core.backup.services.manifest import (
    ManifestArtifact,
    build_manifest_data,
    read_manifest,
    sha256_file,
    write_manifest,
)


class BackupManifestTests(SimpleTestCase):
    def test_manifest_full_sha256_y_engines(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "mysql" / "empresa.sql.gz"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_bytes(b"dump-data")

            pg_path = Path(tmp) / "postgres" / "full.dump"
            pg_path.parent.mkdir(parents=True)
            pg_path.write_bytes(b"pgdump")

            entries = [
                ManifestArtifact(
                    engine="mysql",
                    path="mysql/empresa.sql.gz",
                    sha256=sha256_file(artifact_path),
                    size=artifact_path.stat().st_size,
                ),
                ManifestArtifact(
                    engine="postgres",
                    path="postgres/full.dump",
                    sha256=sha256_file(pg_path),
                    size=pg_path.stat().st_size,
                ),
            ]

            data = build_manifest_data(
                job_id="test-job-id",
                tipo="full",
                parent_job_id=None,
                base_mysql="mi_empresa_prod",
                include_empresas_table=False,
                artifact_entries=entries,
                mysql_binlog_marker={"file": "binlog.000001", "position": 154},
            )
            manifest_path = Path(tmp) / "manifest.json"
            payload = write_manifest(manifest_path, data)

            self.assertEqual(payload["tipo"], "full")
            self.assertIn("mysql", payload["engines"])
            self.assertIn("postgres", payload["engines"])
            self.assertEqual(len(payload["artifacts"]), 2)
            self.assertTrue(all(a["sha256"] for a in payload["artifacts"]))

            loaded = read_manifest(manifest_path)
            self.assertEqual(loaded["base_mysql"], "mi_empresa_prod")
            self.assertEqual(loaded["mysql_binlog_marker"]["file"], "binlog.000001")

    def test_manifest_incremental_parent_job_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            data = build_manifest_data(
                job_id="child-id",
                tipo="incremental",
                parent_job_id="parent-id",
                base_mysql="empresa",
                include_empresas_table=False,
                artifact_entries=[
                    ManifestArtifact(engine="mysql_binlog", path="x.sql", sha256="a", size=1),
                    ManifestArtifact(engine="postgres_wal", path="y", sha256="b", size=2),
                ],
            )
            write_manifest(manifest_path, data)
            loaded = read_manifest(manifest_path)
            self.assertEqual(loaded["parent_job_id"], "parent-id")
            self.assertEqual(set(loaded["engines"]), {"mysql_binlog", "postgres_wal"})
