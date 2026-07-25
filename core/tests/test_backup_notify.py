"""Tests de notificaciones por correo del módulo backup DR."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from core.backup.models import BackupJob, BackupSettings
from core.backup.services import notify as backup_notify


class ParseRecipientsTests(SimpleTestCase):
    def test_parsea_coma_y_salto(self):
        raw = "a@x.com, b@y.com\nc@z.com;a@x.com\nbad"
        self.assertEqual(
            backup_notify.parse_notify_recipients(raw),
            ["a@x.com", "b@y.com", "c@z.com"],
        )


class ShouldNotifyTests(TestCase):
    def setUp(self):
        BackupSettings.objects.all().delete()
        self.bs = BackupSettings.get_solo()
        self.bs.notify_email_enabled = True
        self.bs.notify_email_to = "ops@empresa.com"
        self.bs.notify_on_success = False
        self.bs.notify_on_partial = True
        self.bs.notify_on_failure = True
        self.bs.save()

    def _job(self, **kwargs):
        defaults = {
            "id": uuid4(),
            "job_type": BackupJob.JOB_TYPE_FULL,
            "status": BackupJob.STATUS_COMPLETED,
            "base_mysql": "administranet",
            "remote_upload_status": BackupJob.REMOTE_SKIPPED,
            "started_at": timezone.now(),
            "finished_at": timezone.now(),
        }
        defaults.update(kwargs)
        return BackupJob(**defaults)

    def test_fallo_notifica(self):
        job = self._job(status=BackupJob.STATUS_FAILED, error_summary="sin disco")
        self.assertTrue(backup_notify.should_notify(job, self.bs))

    def test_ok_sin_flag_no_notifica(self):
        job = self._job(status=BackupJob.STATUS_COMPLETED)
        self.assertFalse(backup_notify.should_notify(job, self.bs))

    def test_sftp_fallido_usa_parcial(self):
        job = self._job(
            status=BackupJob.STATUS_COMPLETED,
            remote_upload_status=BackupJob.REMOTE_FAILED,
            error_summary="SFTP error",
        )
        self.assertTrue(backup_notify.should_notify(job, self.bs))


class NotifySendTests(TestCase):
    def setUp(self):
        BackupSettings.objects.all().delete()
        self.bs = BackupSettings.get_solo()
        self.bs.notify_email_enabled = True
        self.bs.notify_email_to = "ops@empresa.com"
        self.bs.notify_on_failure = True
        self.bs.save()
        self.job = BackupJob.objects.create(
            job_type=BackupJob.JOB_TYPE_FULL,
            status=BackupJob.STATUS_FAILED,
            base_mysql="administranet",
            error_summary="MySQL: conexión rechazada",
            remote_upload_status=BackupJob.REMOTE_SKIPPED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    @patch("core.backup.services.notify.enviar_correo_saliente")
    @patch("core.backup.services.notify.correo_saliente_configurado", return_value=True)
    def test_envia_mail_con_remediacion(self, _cfg, mock_send):
        mock_send.return_value = {"ok": True, "message": "ok", "recipients": ["ops@empresa.com"]}
        result = backup_notify.notify_backup_job(self.job)
        self.assertTrue(result["ok"])
        mock_send.assert_called_once()
        kwargs = mock_send.call_args.kwargs
        self.assertIn("ops@empresa.com", kwargs["to"])
        self.assertIn("FALLO", kwargs["subject"])
        self.assertIn("remediación", kwargs["body"].lower())
        self.assertIn(str(self.job.id), kwargs["body"])

    @patch("core.backup.services.notify.enviar_correo_saliente")
    def test_dry_run_no_envia(self, mock_send):
        self.assertIsNone(backup_notify.notify_backup_job(self.job, dry_run=True))
        mock_send.assert_not_called()
