"""Tests upload SFTP mock."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase

from core.backup.models import BackupSettings
from core.backup.services.sftp_upload import SftpUploadResult, upload_job_directory


class BackupSftpTests(TestCase):
    def test_sftp_disabled_skipped(self):
        bs = BackupSettings.get_solo()
        bs.sftp_enabled = False
        bs.save()
        with tempfile.TemporaryDirectory() as tmp:
            result = upload_job_directory(Path(tmp), "job-1")
            self.assertTrue(result.success)
            self.assertIn("skipped", result.message.lower())

    @patch("core.backup.services.sftp_upload.paramiko")
    def test_sftp_upload_mock(self, mock_paramiko):
        bs = BackupSettings.get_solo()
        bs.sftp_enabled = True
        bs.sftp_host = "sftp.example.com"
        bs.sftp_user = "backup"
        bs.sftp_remote_path = "/synap/backups"
        from core.backup.services import config as backup_config

        backup_config.set_sftp_password(bs, "secret")
        bs.save()

        transport = MagicMock()
        mock_paramiko.Transport.return_value = transport
        sftp = MagicMock()
        mock_paramiko.SFTPClient.from_transport.return_value = sftp
        sftp.stat.side_effect = OSError()

        with tempfile.TemporaryDirectory() as tmp:
            job_dir = Path(tmp)
            (job_dir / "manifest.json").write_text("{}", encoding="utf-8")
            result = upload_job_directory(job_dir, "job-uuid")
            self.assertTrue(result.success)
            sftp.put.assert_called()
            self.assertTrue((job_dir / "manifest.json").is_file())

    @patch("core.backup.services.sftp_upload.paramiko")
    def test_sftp_fallo_preserva_local(self, mock_paramiko):
        bs = BackupSettings.get_solo()
        bs.sftp_enabled = True
        bs.sftp_host = "sftp.example.com"
        bs.sftp_user = "backup"
        from core.backup.services import config as backup_config

        backup_config.set_sftp_password(bs, "secret")
        bs.save()

        mock_paramiko.Transport.side_effect = Exception("conexión rechazada")
        with tempfile.TemporaryDirectory() as tmp:
            job_dir = Path(tmp)
            local_file = job_dir / "data.bin"
            local_file.write_bytes(b"local-copy")
            result = upload_job_directory(job_dir, "job-uuid")
            self.assertFalse(result.success)
            self.assertTrue(local_file.is_file())
