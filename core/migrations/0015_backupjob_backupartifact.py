# Generated manually for backup-dr-synap change

import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_moduleconfig_tiendanube_administranet"),
    ]

    operations = [
        migrations.CreateModel(
            name="BackupJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "job_type",
                    models.CharField(
                        choices=[("full", "Completo"), ("incremental", "Incremental")],
                        max_length=16,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "En cola"),
                            ("running", "En ejecución"),
                            ("completed", "Completado"),
                            ("partial_failed", "Fallo parcial"),
                            ("failed", "Fallido"),
                            ("cancelled", "Cancelado"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("base_mysql", models.CharField(max_length=128)),
                ("include_empresas_table", models.BooleanField(default=False)),
                ("triggered_by_id_usuario", models.IntegerField(blank=True, null=True)),
                (
                    "triggered_by_cod_usuario",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                ("scheduled", models.BooleanField(default=False)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("log_path", models.CharField(blank=True, default="", max_length=512)),
                (
                    "manifest_path",
                    models.CharField(blank=True, default="", max_length=512),
                ),
                (
                    "mysql_binlog_file",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("mysql_binlog_pos", models.BigIntegerField(blank=True, null=True)),
                ("error_summary", models.TextField(blank=True, default="")),
                (
                    "remote_upload_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendiente"),
                            ("success", "Éxito"),
                            ("failed", "Fallido"),
                            ("skipped", "Omitido"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "parent_job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="child_jobs",
                        to="core.backupjob",
                    ),
                ),
            ],
            options={
                "verbose_name": "Job de backup",
                "verbose_name_plural": "Jobs de backup",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="BackupArtifact",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "engine",
                    models.CharField(
                        choices=[
                            ("mysql", "MySQL"),
                            ("postgres", "PostgreSQL"),
                            ("mysql_binlog", "MySQL binlog"),
                            ("postgres_wal", "PostgreSQL WAL"),
                            ("manifest", "Manifest"),
                        ],
                        max_length=32,
                    ),
                ),
                ("relative_path", models.CharField(max_length=512)),
                ("absolute_path", models.CharField(max_length=1024)),
                ("sha256", models.CharField(blank=True, default="", max_length=64)),
                ("size_bytes", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artifacts",
                        to="core.backupjob",
                    ),
                ),
            ],
            options={
                "verbose_name": "Artefacto de backup",
                "verbose_name_plural": "Artefactos de backup",
                "ordering": ["engine", "relative_path"],
            },
        ),
    ]
