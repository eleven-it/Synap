"""Tests comando backup_tick (programación automática)."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from core.backup.models import BackupJob, BackupSettings
from core.management.commands.backup_tick import Command


class BackupTickTests(TestCase):
    def setUp(self):
        self.bs = BackupSettings.get_solo()
        self.bs.enabled_auto = True
        self.bs.base_mysql = "empresa_prod"
        self.bs.schedule_json = [{"dow": 0, "time": "02:00", "job_type": "incremental"}]
        self.bs.save()

    @patch("core.management.commands.backup_tick.Command._launch_backup_subprocess")
    def test_disabled_exits_quietly(self, mock_launch):
        self.bs.enabled_auto = False
        self.bs.save()
        Command().handle()
        mock_launch.assert_not_called()
        self.assertEqual(BackupJob.objects.count(), 0)

    @patch("core.management.commands.backup_tick.Command._launch_backup_subprocess")
    def test_empty_base_mysql_no_job(self, mock_launch):
        self.bs.base_mysql = ""
        self.bs.save()
        Command().handle()
        mock_launch.assert_not_called()

    @patch("core.management.commands.backup_tick.Command._launch_backup_subprocess")
    @patch("core.management.commands.backup_tick.timezone.localtime")
    def test_launches_on_schedule_match(self, mock_localtime, mock_launch):
        BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_FULL,
            status=BackupJob.STATUS_COMPLETED,
            base_mysql="empresa_prod",
            mysql_binlog_file="bin.001",
            mysql_binlog_pos=100,
        )
        tz = ZoneInfo("America/Argentina/Buenos_Aires")
        mock_localtime.return_value = datetime(2026, 7, 27, 2, 0, tzinfo=tz)
        Command().handle()
        self.assertEqual(BackupJob.objects.filter(scheduled=True).count(), 1)
        job = BackupJob.objects.get(scheduled=True)
        self.assertEqual(job.job_type, BackupJob.JOB_TYPE_INCREMENTAL)
        self.assertEqual(job.base_mysql, "empresa_prod")
        mock_launch.assert_called_once()

    @patch("core.management.commands.backup_tick.Command._launch_backup_subprocess")
    @patch("core.management.commands.backup_tick.timezone.localtime")
    def test_skips_duplicate_within_50_minutes(self, mock_localtime, mock_launch):
        tz = ZoneInfo("America/Argentina/Buenos_Aires")
        now = datetime(2026, 7, 27, 2, 0, tzinfo=tz)
        mock_localtime.return_value = now
        BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_INCREMENTAL,
            status=BackupJob.STATUS_RUNNING,
            base_mysql="empresa_prod",
            scheduled=True,
        )
        Command().handle()
        mock_launch.assert_not_called()
        self.assertEqual(BackupJob.objects.filter(scheduled=True).count(), 1)

    @patch("core.management.commands.backup_tick.Command._launch_backup_subprocess")
    @patch("core.management.commands.backup_tick.timezone.localtime")
    def test_incremental_requires_parent_full(self, mock_localtime, mock_launch):
        tz = ZoneInfo("America/Argentina/Buenos_Aires")
        mock_localtime.return_value = datetime(2026, 7, 27, 2, 0, tzinfo=tz)
        Command().handle()
        mock_launch.assert_not_called()
        self.assertEqual(BackupJob.objects.count(), 0)

    @patch("core.management.commands.backup_tick.Command._launch_backup_subprocess")
    @patch("core.management.commands.backup_tick.timezone.localtime")
    def test_incremental_with_parent_launches(self, mock_localtime, mock_launch):
        BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_FULL,
            status=BackupJob.STATUS_COMPLETED,
            base_mysql="empresa_prod",
            mysql_binlog_file="bin.001",
            mysql_binlog_pos=100,
        )
        tz = ZoneInfo("America/Argentina/Buenos_Aires")
        mock_localtime.return_value = datetime(2026, 7, 27, 2, 0, tzinfo=tz)
        Command().handle()
        mock_launch.assert_called_once()
        job = BackupJob.objects.filter(scheduled=True, job_type=BackupJob.JOB_TYPE_INCREMENTAL).get()
        self.assertIsNotNone(job.parent_job_id)
