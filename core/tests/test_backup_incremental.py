"""Tests backup incremental encadenado."""

import tempfile
from unittest.mock import patch

from django.test import TestCase, override_settings

from core.backup.models import BackupArtifact, BackupJob
from core.backup.services.orchestrator import run_job


@override_settings(BACKUP_LOCAL_ROOT=tempfile.gettempdir())
class BackupIncrementalTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.settings_override = override_settings(BACKUP_LOCAL_ROOT=self.tmp)
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()

    @patch("core.backup.services.orchestrator.sftp_upload.upload_job_directory")
    @patch("core.backup.services.orchestrator.postgres_backup.run_wal_incremental")
    @patch("core.backup.services.orchestrator.mysql_backup.run_mysqlbinlog_incremental")
    @patch("core.backup.services.orchestrator.prechecks.check_mysql_connectivity")
    @patch("core.backup.services.orchestrator.prechecks.check_disk_space")
    @patch("core.backup.services.orchestrator.prechecks.check_postgres_wal_archive_dir")
    @patch("core.backup.services.orchestrator.prechecks.check_mysql_binlog_enabled")
    def test_incremental_exige_ambos_engines(
        self, mock_binlog, mock_wal_dir, mock_disk, mock_mysql_conn, mock_mysql_inc, mock_pg_wal, mock_sftp
    ):
        from core.backup.services import prechecks

        mock_disk.return_value = prechecks.PrecheckResult(ok=True)
        mock_mysql_conn.return_value = prechecks.PrecheckResult(ok=True)
        mock_binlog.return_value = prechecks.PrecheckResult(ok=True)
        mock_wal_dir.return_value = prechecks.PrecheckResult(ok=True)
        mock_sftp.return_value.__class__.__name__ = "SftpUploadResult"
        from core.backup.services.sftp_upload import SftpUploadResult

        mock_sftp.return_value = SftpUploadResult(success=True)

        from core.backup.services.mysql_backup import MySQLBackupResult
        from core.backup.services.postgres_backup import PostgresBackupResult

        mock_mysql_inc.return_value = MySQLBackupResult(
            success=True,
            relative_paths=["mysql_binlog/inc.sql"],
            absolute_paths=[],
            binlog_file="binlog.000002",
            binlog_pos=200,
        )
        mock_pg_wal.return_value = PostgresBackupResult(
            success=True,
            relative_paths=["postgres_wal/000000010000000000000002"],
            absolute_paths=[],
            wal_range={"files": ["000000010000000000000002"]},
        )

        parent = BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_FULL,
            status=BackupJob.STATUS_COMPLETED,
            base_mysql="empresa_test",
            mysql_binlog_file="binlog.000001",
            mysql_binlog_pos=100,
        )

        job = BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_INCREMENTAL,
            status=BackupJob.STATUS_QUEUED,
            base_mysql="empresa_test",
            parent_job=parent,
        )

        with patch(
            "core.backup.services.orchestrator._artifact_entries_from_paths",
            return_value=[
                __import__(
                    "core.backup.services.manifest", fromlist=["ManifestArtifact"]
                ).ManifestArtifact(
                    engine=BackupArtifact.ENGINE_MYSQL_BINLOG,
                    path="mysql_binlog/inc.sql",
                    sha256="abc",
                    size=3,
                ),
                __import__(
                    "core.backup.services.manifest", fromlist=["ManifestArtifact"]
                ).ManifestArtifact(
                    engine=BackupArtifact.ENGINE_POSTGRES_WAL,
                    path="postgres_wal/wal1",
                    sha256="def",
                    size=4,
                ),
            ],
        ):
            run_job(job, dry_run=True)

        job.refresh_from_db()
        self.assertEqual(job.status, BackupJob.STATUS_COMPLETED)
        self.assertTrue(job.manifest_path)
        import json
        from pathlib import Path

        manifest = json.loads(Path(job.manifest_path).read_text(encoding="utf-8"))
        self.assertEqual(manifest["parent_job_id"], str(parent.id))
        engines = set(manifest["engines"])
        self.assertIn("mysql_binlog", engines)
        self.assertIn("postgres_wal", engines)

    @patch("core.backup.services.orchestrator.sftp_upload.upload_job_directory")
    @patch("core.backup.services.orchestrator.postgres_backup.run_wal_incremental")
    @patch("core.backup.services.orchestrator.mysql_backup.run_mysqlbinlog_incremental")
    @patch("core.backup.services.orchestrator.prechecks.check_mysql_connectivity")
    @patch("core.backup.services.orchestrator.prechecks.check_disk_space")
    @patch("core.backup.services.orchestrator.prechecks.check_postgres_wal_archive_dir")
    @patch("core.backup.services.orchestrator.prechecks.check_mysql_binlog_enabled")
    def test_partial_failed_si_postgres_falla(
        self, mock_binlog, mock_wal_dir, mock_disk, mock_mysql_conn, mock_mysql_inc, mock_pg_wal, mock_sftp
    ):
        from core.backup.services import prechecks
        from core.backup.services.mysql_backup import MySQLBackupResult
        from core.backup.services.postgres_backup import PostgresBackupResult
        from core.backup.services.sftp_upload import SftpUploadResult

        mock_disk.return_value = prechecks.PrecheckResult(ok=True)
        mock_mysql_conn.return_value = prechecks.PrecheckResult(ok=True)
        mock_binlog.return_value = prechecks.PrecheckResult(ok=True)
        mock_wal_dir.return_value = prechecks.PrecheckResult(ok=True)
        mock_sftp.return_value = SftpUploadResult(success=True)
        mock_mysql_inc.return_value = MySQLBackupResult(
            success=True,
            relative_paths=["mysql_binlog/inc.sql"],
            absolute_paths=[],
            binlog_file="binlog.000002",
            binlog_pos=200,
        )
        mock_pg_wal.return_value = PostgresBackupResult(
            success=False,
            relative_paths=[],
            absolute_paths=[],
            error="No hay segmentos WAL nuevos",
        )

        parent = BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_FULL,
            status=BackupJob.STATUS_COMPLETED,
            base_mysql="empresa_test",
            mysql_binlog_file="binlog.000001",
            mysql_binlog_pos=100,
        )
        job = BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_INCREMENTAL,
            status=BackupJob.STATUS_QUEUED,
            base_mysql="empresa_test",
            parent_job=parent,
        )

        with patch(
            "core.backup.services.orchestrator._artifact_entries_from_paths",
            return_value=[
                __import__(
                    "core.backup.services.manifest", fromlist=["ManifestArtifact"]
                ).ManifestArtifact(
                    engine=BackupArtifact.ENGINE_MYSQL_BINLOG,
                    path="mysql_binlog/inc.sql",
                    sha256="abc",
                    size=3,
                ),
            ],
        ):
            run_job(job, dry_run=True)

        job.refresh_from_db()
        self.assertEqual(job.status, BackupJob.STATUS_PARTIAL_FAILED)
        self.assertIn("PostgreSQL", job.error_summary)
