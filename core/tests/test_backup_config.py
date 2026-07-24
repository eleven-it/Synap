"""Tests configuración backup (BackupSettings, schedule, cifrado)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from core.backup.models import BackupJob, BackupSettings, default_backup_schedule
from core.backup.services import config as backup_config
from core.backup.services.secrets import decrypt_secret, encrypt_secret


@override_settings(SECRET_KEY="test-secret-key-for-backup")
class BackupConfigTests(TestCase):
    def test_get_solo_crea_defaults(self):
        self.assertEqual(BackupSettings.objects.count(), 0)
        bs = BackupSettings.get_solo()
        self.assertEqual(bs.pk, 1)
        self.assertFalse(bs.enabled_auto)
        self.assertEqual(len(bs.schedule_json), 7)
        self.assertEqual(BackupSettings.objects.count(), 1)

    def test_default_schedule_lun_sab_incremental_dom_full(self):
        schedule = default_backup_schedule()
        by_dow = {r["dow"]: r for r in schedule}
        for dow in range(6):
            self.assertEqual(by_dow[dow]["job_type"], BackupJob.JOB_TYPE_INCREMENTAL)
            self.assertEqual(by_dow[dow]["time"], "02:00")
        self.assertEqual(by_dow[6]["job_type"], BackupJob.JOB_TYPE_FULL)
        self.assertEqual(by_dow[6]["time"], "03:00")

    def test_encrypt_decrypt_password(self):
        bs = BackupSettings.get_solo()
        plain = "mi-clave-sftp-secreta"
        backup_config.set_sftp_password(bs, plain)
        bs.save()
        bs.refresh_from_db()
        self.assertTrue(bs.sftp_password_encrypted)
        self.assertNotIn(plain, bs.sftp_password_encrypted)
        self.assertEqual(backup_config.sftp_password_plain(bs), plain)

    def test_set_sftp_password_blank_keeps_previous(self):
        bs = BackupSettings.get_solo()
        backup_config.set_sftp_password(bs, "primera")
        bs.save()
        backup_config.set_sftp_password(bs, None)
        self.assertEqual(backup_config.sftp_password_plain(bs), "primera")

    def test_schedule_match_lun_incremental(self):
        bs = BackupSettings.get_solo()
        bs.schedule_json = [{"dow": 0, "time": "02:00", "job_type": "incremental"}]
        bs.save()
        # Lunes 2026-07-27 02:00 ART (UTC-3)
        tz = ZoneInfo("America/Argentina/Buenos_Aires")
        monday = datetime(2026, 7, 27, 2, 0, tzinfo=tz)
        rules = backup_config.matching_schedule_rules(monday, match_minute=True)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["job_type"], BackupJob.JOB_TYPE_INCREMENTAL)

    def test_schedule_match_dom_full(self):
        bs = BackupSettings.get_solo()
        bs.schedule_json = [{"dow": 6, "time": "03:00", "job_type": "full"}]
        bs.save()
        tz = ZoneInfo("America/Argentina/Buenos_Aires")
        sunday = datetime(2026, 7, 26, 3, 0, tzinfo=tz)
        rules = backup_config.matching_schedule_rules(sunday, match_minute=True)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["job_type"], BackupJob.JOB_TYPE_FULL)

    def test_effective_local_root_from_settings_row(self):
        bs = BackupSettings.get_solo()
        bs.local_root = "/tmp/synap-backups-test"
        bs.save()
        self.assertEqual(backup_config.effective_local_root(), "/tmp/synap-backups-test")

    def test_secrets_roundtrip(self):
        enc = encrypt_secret("hola")
        self.assertEqual(decrypt_secret(enc), "hola")
