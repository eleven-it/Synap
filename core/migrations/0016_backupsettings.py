# Generated manually — configuración backup DR en Postgres (singleton)

from django.db import migrations, models

import core.backup.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_backupjob_backupartifact"),
    ]

    operations = [
        migrations.CreateModel(
            name="BackupSettings",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "enabled_auto",
                    models.BooleanField(
                        default=False, verbose_name="Programación automática activa"
                    ),
                ),
                ("base_mysql", models.CharField(blank=True, default="", max_length=128)),
                (
                    "include_empresas",
                    models.BooleanField(
                        default=False,
                        verbose_name="Incluir base empresas en jobs programados full",
                    ),
                ),
                (
                    "local_root",
                    models.CharField(
                        default="/var/lib/synap/backups",
                        max_length=512,
                        verbose_name="Directorio local de backups",
                    ),
                ),
                (
                    "retention_days",
                    models.PositiveIntegerField(
                        default=30, verbose_name="Días de retención local"
                    ),
                ),
                (
                    "pg_wal_archive_dir",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=512,
                        verbose_name="Directorio WAL archivados (PostgreSQL)",
                    ),
                ),
                (
                    "sftp_enabled",
                    models.BooleanField(default=False, verbose_name="SFTP remoto habilitado"),
                ),
                ("sftp_host", models.CharField(blank=True, default="", max_length=255)),
                (
                    "sftp_port",
                    models.PositiveIntegerField(default=22, verbose_name="Puerto SFTP"),
                ),
                ("sftp_user", models.CharField(blank=True, default="", max_length=128)),
                (
                    "sftp_remote_path",
                    models.CharField(
                        blank=True,
                        default="/synap/backups",
                        max_length=512,
                        verbose_name="Ruta remota SFTP",
                    ),
                ),
                ("sftp_password_encrypted", models.TextField(blank=True, default="")),
                (
                    "sftp_key_path",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=512,
                        verbose_name="Ruta a clave privada SFTP (opcional)",
                    ),
                ),
                (
                    "schedule_json",
                    models.JSONField(
                        default=core.backup.models.default_backup_schedule,
                        help_text=(
                            "Lista de reglas {dow, time, job_type}. dow: 0=lunes … 6=domingo "
                            "(hora local Django)."
                        ),
                        verbose_name="Reglas de programación",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "updated_by_cod_usuario",
                    models.CharField(blank=True, default="", max_length=64),
                ),
            ],
            options={
                "verbose_name": "Configuración de backup",
                "verbose_name_plural": "Configuración de backup",
            },
        ),
    ]
