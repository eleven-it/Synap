"""Tests del paquete bootstrap DR (.env cifrado + inventory)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from core.backup.models import BackupSettings
from core.backup.services import config as backup_config
from core.backup.services.bootstrap import (
    build_bootstrap_bundle,
    decrypt_env_bytes,
    encrypt_env_bytes,
)


class BootstrapCryptoTests(SimpleTestCase):
    def test_roundtrip_env_cifrado(self):
        plain = b"SECRET_KEY=abc\nDB_PASSWORD=x\n"
        phrase = "frase-de-prueba-larga"
        enc = encrypt_env_bytes(plain, phrase)
        self.assertNotEqual(enc, plain)
        self.assertEqual(decrypt_env_bytes(enc, phrase), plain)


class BootstrapBundleTests(TestCase):
    def setUp(self):
        BackupSettings.objects.all().delete()
        self.bs = BackupSettings.get_solo()

    def test_full_incluye_env_si_hay_frase(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            env_file = base / ".env"
            env_file.write_text("SECRET_KEY=test\nDB_HOST=mysql\n", encoding="utf-8")
            job_dir = base / "job"
            job_dir.mkdir()
            backup_config.set_bootstrap_passphrase(self.bs, "mi-frase-segura-123")
            self.bs.save()

            with patch("core.backup.services.bootstrap.settings") as mock_settings:
                mock_settings.BASE_DIR = base
                mock_settings.DATABASES = {
                    "default": {"NAME": "mydatabase", "HOST": "db", "PORT": "5432", "USER": "u"},
                    "mysql": {"NAME": "administranet", "HOST": "192.168.0.2", "PORT": "30804", "USER": "a"},
                }
                mock_settings.SITE_URL = "https://synap.test"
                mock_settings.ENVIRONMENT = "development"
                mock_settings.FE_AFIP_CERT_STORAGE_DIR = str(base / "afip" / "certs")
                (base / "afip" / "certs").mkdir(parents=True)
                (base / "afip" / "certs" / "x.crt").write_text("cert", encoding="utf-8")

                result = build_bootstrap_bundle(
                    job_dir, job_id="job-1", base_mysql="administranet", dry_run=False
                )

            self.assertTrue(result.success)
            self.assertTrue(result.env_included)
            self.assertIn("bootstrap/env.enc", result.relative_paths)
            self.assertIn("bootstrap/inventory.json", result.relative_paths)
            enc = (job_dir / "bootstrap" / "env.enc").read_bytes()
            plain = decrypt_env_bytes(enc, "mi-frase-segura-123")
            self.assertIn(b"SECRET_KEY=test", plain)

    def test_sin_frase_omite_env_con_aviso(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".env").write_text("SECRET_KEY=x\n", encoding="utf-8")
            job_dir = base / "job"
            job_dir.mkdir()
            self.bs.bootstrap_passphrase_encrypted = ""
            self.bs.save()

            with patch("core.backup.services.bootstrap.settings") as mock_settings:
                mock_settings.BASE_DIR = base
                mock_settings.DATABASES = {"default": {}, "mysql": {}}
                mock_settings.SITE_URL = ""
                mock_settings.ENVIRONMENT = "development"
                mock_settings.FE_AFIP_CERT_STORAGE_DIR = str(base / "missing" / "certs")

                # bootstrap_passphrase_plain lee BackupSettings de DB
                with patch(
                    "core.backup.services.bootstrap.backup_config.bootstrap_passphrase_plain",
                    return_value="",
                ):
                    result = build_bootstrap_bundle(
                        job_dir, job_id="job-2", base_mysql="demo", dry_run=False
                    )

            self.assertTrue(result.success)
            self.assertFalse(result.env_included)
            self.assertTrue(any("frase" in w.lower() for w in result.warnings))
            self.assertTrue((job_dir / "bootstrap" / "inventory.json").is_file())
