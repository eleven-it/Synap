import uuid

from django.db import models


class BackupJob(models.Model):
    """Job de backup full o incremental (Postgres + MySQL)."""

    JOB_TYPE_FULL = "full"
    JOB_TYPE_INCREMENTAL = "incremental"
    JOB_TYPE_CHOICES = [
        (JOB_TYPE_FULL, "Completo"),
        (JOB_TYPE_INCREMENTAL, "Incremental"),
    ]

    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_PARTIAL_FAILED = "partial_failed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "En cola"),
        (STATUS_RUNNING, "En ejecución"),
        (STATUS_COMPLETED, "Completado"),
        (STATUS_PARTIAL_FAILED, "Fallo parcial"),
        (STATUS_FAILED, "Fallido"),
        (STATUS_CANCELLED, "Cancelado"),
    ]

    REMOTE_PENDING = "pending"
    REMOTE_SUCCESS = "success"
    REMOTE_FAILED = "failed"
    REMOTE_SKIPPED = "skipped"
    REMOTE_UPLOAD_CHOICES = [
        (REMOTE_PENDING, "Pendiente"),
        (REMOTE_SUCCESS, "Éxito"),
        (REMOTE_FAILED, "Fallido"),
        (REMOTE_SKIPPED, "Omitido"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=16, choices=JOB_TYPE_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True
    )
    base_mysql = models.CharField(max_length=128)
    include_empresas_table = models.BooleanField(default=False)
    parent_job = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_jobs",
    )
    triggered_by_id_usuario = models.IntegerField(null=True, blank=True)
    triggered_by_cod_usuario = models.CharField(max_length=64, blank=True, default="")
    scheduled = models.BooleanField(default=False)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    log_path = models.CharField(max_length=512, blank=True, default="")
    manifest_path = models.CharField(max_length=512, blank=True, default="")
    mysql_binlog_file = models.CharField(max_length=255, blank=True, default="")
    mysql_binlog_pos = models.BigIntegerField(null=True, blank=True)
    error_summary = models.TextField(blank=True, default="")
    remote_upload_status = models.CharField(
        max_length=16,
        choices=REMOTE_UPLOAD_CHOICES,
        default=REMOTE_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Job de backup"
        verbose_name_plural = "Jobs de backup"

    def __str__(self):
        return f"{self.job_type} {self.base_mysql} ({self.status})"

    @property
    def total_size_bytes(self) -> int:
        return sum(a.size_bytes for a in self.artifacts.all())


class BackupArtifact(models.Model):
    """Artefacto generado por un job de backup."""

    ENGINE_MYSQL = "mysql"
    ENGINE_POSTGRES = "postgres"
    ENGINE_MYSQL_BINLOG = "mysql_binlog"
    ENGINE_POSTGRES_WAL = "postgres_wal"
    ENGINE_MANIFEST = "manifest"
    ENGINE_CHOICES = [
        (ENGINE_MYSQL, "MySQL"),
        (ENGINE_POSTGRES, "PostgreSQL"),
        (ENGINE_MYSQL_BINLOG, "MySQL binlog"),
        (ENGINE_POSTGRES_WAL, "PostgreSQL WAL"),
        (ENGINE_MANIFEST, "Manifest"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(BackupJob, on_delete=models.CASCADE, related_name="artifacts")
    engine = models.CharField(max_length=32, choices=ENGINE_CHOICES)
    relative_path = models.CharField(max_length=512)
    absolute_path = models.CharField(max_length=1024)
    sha256 = models.CharField(max_length=64, blank=True, default="")
    size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["engine", "relative_path"]
        verbose_name = "Artefacto de backup"
        verbose_name_plural = "Artefactos de backup"

    def __str__(self):
        return f"{self.engine}: {self.relative_path}"
