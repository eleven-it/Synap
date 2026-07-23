"""Tests prechecks backup (binlog, WAL)."""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from core.backup.services import prechecks


class BackupPrechecksTests(SimpleTestCase):
    @patch("core.backup.services.prechecks.get_connection")
    def test_log_bin_off_error_espanol(self, mock_conn):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("log_bin", "OFF")
        conn = MagicMock()
        conn.cursor.return_value = cursor
        mock_conn.return_value.__enter__.return_value = conn
        mock_conn.return_value.__exit__.return_value = None

        result = prechecks.check_mysql_binlog_enabled("empresa")
        self.assertFalse(result.ok)
        self.assertIn("log_bin=OFF", result.message)
        self.assertIn("binary log", result.message.lower())

    @override_settings(BACKUP_PG_WAL_ARCHIVE_DIR="")
    def test_wal_dir_vacio_fallo_explicito(self):
        result = prechecks.check_postgres_wal_archive_dir(for_incremental=True)
        self.assertFalse(result.ok)
        self.assertIn("BACKUP_PG_WAL_ARCHIVE_DIR", result.message)

    @override_settings(BACKUP_PG_WAL_ARCHIVE_DIR="/tmp/no-existe-wal-synap-test")
    def test_wal_dir_no_existe(self):
        result = prechecks.check_postgres_wal_archive_dir(for_incremental=True)
        self.assertFalse(result.ok)
        self.assertIn("no existe", result.message.lower())
