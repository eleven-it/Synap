"""SFTP Mtrix: mock paramiko; fallo no borra el CSV local."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from mtrix.models import MtrixArtifact, MtrixConfig, MtrixJob
from mtrix.services import sftp as sftp_mod
from mtrix.services.crypto import encrypt_secret
from datetime import date

from mtrix.services.sftp import avanzar_marca_agua_vd, enviar_job


class SftpTests(TestCase):
    def test_no_usa_credenciales_de_backup(self):
        src = Path(sftp_mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("BACKUP_SFTP", src)
        self.assertNotIn("backup_config", src)
        self.assertNotIn("core.backup", src)

    def test_fallo_marca_failed_y_conserva_archivo(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with override_settings(MEDIA_ROOT=tmp.name):
            cfg = MtrixConfig.objects.create(
                base_empresa="emp_sftp",
                sftp_host="sftp.example",
                sftp_user="mtrix",
                sftp_password_encrypted=encrypt_secret("secret"),
                sftp_remote_path="/in",
            )
            job = MtrixJob.objects.create(
                base_empresa="emp_sftp",
                status=MtrixJob.Estado.COMPLETED,
            )
            rel_dir = Path(tmp.name) / "mtrix" / "emp_sftp" / str(job.id)
            rel_dir.mkdir(parents=True)
            local = rel_dir / "CI-INT12082026100000000.csv"
            local.write_bytes(b"header\r\nrow\r\n")
            art = MtrixArtifact.objects.create(
                job=job,
                tipo="CI",
                filename=local.name,
                relative_path=local.relative_to(tmp.name).as_posix(),
                size_bytes=local.stat().st_size,
                row_count=1,
            )
            with patch.object(sftp_mod, "paramiko", MagicMock()) as mock_paramiko:
                mock_paramiko.Transport.side_effect = OSError("conexión rechazada")
                result = enviar_job(job, cfg)
            self.assertFalse(result.success)
            art.refresh_from_db()
            self.assertEqual(art.sftp_status, MtrixArtifact.SftpStatus.FAILED)
            self.assertTrue(local.exists())

    def test_reenvio_sin_regenerar_usa_put(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with override_settings(MEDIA_ROOT=tmp.name):
            cfg = MtrixConfig.objects.create(
                base_empresa="emp_sftp2",
                sftp_host="sftp.example",
                sftp_user="mtrix",
                sftp_password_encrypted=encrypt_secret("secret"),
                sftp_remote_path="/in",
            )
            job = MtrixJob.objects.create(
                base_empresa="emp_sftp2",
                status=MtrixJob.Estado.COMPLETED,
            )
            rel_dir = Path(tmp.name) / "mtrix" / "emp_sftp2" / str(job.id)
            rel_dir.mkdir(parents=True)
            local = rel_dir / "PD-INT.csv"
            local.write_bytes(b"x")
            MtrixArtifact.objects.create(
                job=job,
                tipo="PD",
                filename=local.name,
                relative_path=local.relative_to(tmp.name).as_posix(),
                size_bytes=1,
                row_count=1,
            )
            mock_sftp = MagicMock()
            mock_transport = MagicMock()
            with patch.object(sftp_mod, "paramiko", MagicMock()) as mock_paramiko:
                mock_paramiko.Transport.return_value = mock_transport
                mock_paramiko.SFTPClient.from_transport.return_value = mock_sftp
                mock_sftp.stat.side_effect = OSError("no existe")
                result = enviar_job(job, cfg)
            self.assertTrue(result.success)
            mock_sftp.put.assert_called()
            self.assertTrue(local.exists())

    def test_sftp_ok_avanza_marca_y_no_retrocede(self):
        cfg = MtrixConfig.objects.create(base_empresa="emp_marca")
        job = MtrixJob.objects.create(
            base_empresa="emp_marca",
            status=MtrixJob.Estado.COMPLETED,
            fecha_hasta=date(2026, 8, 27),
        )
        MtrixArtifact.objects.create(
            job=job,
            tipo="VD",
            filename="VD.csv",
            relative_path="x",
            sftp_status=MtrixArtifact.SftpStatus.SUCCESS,
        )
        self.assertTrue(avanzar_marca_agua_vd(cfg, job))
        cfg.refresh_from_db()
        self.assertEqual(cfg.last_vd_enviado_hasta, date(2026, 8, 27))

        job_viejo = MtrixJob.objects.create(
            base_empresa="emp_marca",
            status=MtrixJob.Estado.COMPLETED,
            fecha_hasta=date(2026, 6, 1),
        )
        MtrixArtifact.objects.create(
            job=job_viejo,
            tipo="VD",
            filename="VD2.csv",
            relative_path="y",
            sftp_status=MtrixArtifact.SftpStatus.SUCCESS,
        )
        self.assertFalse(avanzar_marca_agua_vd(cfg, job_viejo))
        cfg.refresh_from_db()
        self.assertEqual(cfg.last_vd_enviado_hasta, date(2026, 8, 27))

    def test_sftp_fallido_no_avanza_marca(self):
        cfg = MtrixConfig.objects.create(base_empresa="emp_marca2")
        job = MtrixJob.objects.create(
            base_empresa="emp_marca2",
            status=MtrixJob.Estado.COMPLETED,
            fecha_hasta=date(2026, 8, 27),
        )
        MtrixArtifact.objects.create(
            job=job,
            tipo="VD",
            filename="VD.csv",
            relative_path="x",
            sftp_status=MtrixArtifact.SftpStatus.FAILED,
        )
        self.assertFalse(avanzar_marca_agua_vd(cfg, job))
        cfg.refresh_from_db()
        self.assertIsNone(cfg.last_vd_enviado_hasta)

    def test_sftp_sin_config_no_avanza_marca(self):
        cfg = MtrixConfig.objects.create(base_empresa="emp_marca3")
        job = MtrixJob.objects.create(
            base_empresa="emp_marca3",
            status=MtrixJob.Estado.COMPLETED,
            fecha_hasta=date(2026, 8, 27),
        )
        MtrixArtifact.objects.create(
            job=job,
            tipo="VD",
            filename="VD.csv",
            relative_path="x",
        )
        result = enviar_job(job, cfg)
        self.assertTrue(result.success)
        cfg.refresh_from_db()
        self.assertIsNone(cfg.last_vd_enviado_hasta)
