"""Modelos PostgreSQL del módulo Mtrix."""

from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class MtrixConfig(models.Model):
    """Configuración de exportación MTRIX por empresa AdministraNET."""

    base_empresa = models.CharField(
        _("Base empresa"),
        max_length=64,
        unique=True,
        db_index=True,
    )
    fecha_personalizada = models.BooleanField(_("Fecha personalizada"), default=False)
    fecha_inicio = models.DateField(_("Fecha inicio"), null=True, blank=True)
    fecha_final = models.DateField(_("Fecha final"), null=True, blank=True)
    dias_a_procesar = models.PositiveIntegerField(_("Días a procesar"), default=5)
    codigo_proveedor_principal = models.CharField(
        _("Códigos de proveedor"),
        max_length=255,
        blank=True,
        help_text=_("Vacío = todos. Lista separada por comas, ej. 23,29,31. Un archivo por categoría."),
    )
    cnpj_fornecedor = models.CharField(_("CNPJ fornecedor"), max_length=20, blank=True)
    pvnf = models.BooleanField(
        _("Incluir todos los puntos de venta"),
        default=False,
        help_text=_("Si está inactivo, solo punto_venta.cont = Si (VD)."),
    )
    multiplicador_cantidad = models.IntegerField(_("Multiplicador cantidad"), default=1)
    multiplicador_precio = models.IntegerField(_("Multiplicador precio"), default=1)
    version_layout = models.PositiveIntegerField(_("Versión layout"), default=19)
    sftp_host = models.CharField(_("Host SFTP"), max_length=255, blank=True)
    sftp_port = models.PositiveIntegerField(_("Puerto SFTP"), default=22)
    sftp_user = models.CharField(_("Usuario SFTP"), max_length=128, blank=True)
    sftp_remote_path = models.CharField(_("Path remoto SFTP"), max_length=512, blank=True)
    sftp_password_encrypted = models.TextField(_("Contraseña SFTP cifrada"), blank=True)
    sftp_key_path = models.CharField(_("Ruta clave SFTP"), max_length=512, blank=True)
    sftp_enviar_automatico = models.BooleanField(
        _("Enviar por SFTP en cron"),
        default=False,
    )
    programador_activo = models.BooleanField(_("Programador activo"), default=False)
    schedule_json = models.JSONField(_("Programación"), default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Configuración Mtrix")
        verbose_name_plural = _("Configuraciones Mtrix")

    def __str__(self) -> str:
        return self.base_empresa


class MtrixJob(models.Model):
    """Corrida de generación MTRIX."""

    class Estado(models.TextChoices):
        QUEUED = "queued", _("En cola")
        RUNNING = "running", _("En curso")
        COMPLETED = "completed", _("Completado")
        FAILED = "failed", _("Fallido")

    class Origen(models.TextChoices):
        UI = "ui", _("Interfaz")
        CRON = "cron", _("Programado")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    base_empresa = models.CharField(_("Base empresa"), max_length=64, db_index=True)
    status = models.CharField(
        _("Estado"),
        max_length=16,
        choices=Estado.choices,
        default=Estado.QUEUED,
        db_index=True,
    )
    origen = models.CharField(
        _("Origen"),
        max_length=8,
        choices=Origen.choices,
        default=Origen.UI,
    )
    fecha_desde = models.DateField(_("Desde"), null=True, blank=True)
    fecha_hasta = models.DateField(_("Hasta"), null=True, blank=True)
    triggered_by = models.CharField(_("Disparado por"), max_length=64, blank=True)
    progreso = models.CharField(_("Progreso"), max_length=200, blank=True)
    error_summary = models.TextField(_("Error"), blank=True)
    log_text = models.TextField(_("Log"), blank=True)
    started_at = models.DateTimeField(_("Inicio"), null=True, blank=True)
    finished_at = models.DateTimeField(_("Fin"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Job Mtrix")
        verbose_name_plural = _("Jobs Mtrix")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["base_empresa"],
                condition=models.Q(status__in=["queued", "running"]),
                name="mtrix_job_un_activo_por_empresa",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.base_empresa} {self.status}"


class MtrixArtifact(models.Model):
    """CSV generado por un job."""

    class Tipo(models.TextChoices):
        CI = "CI", "CI"
        PD = "PD", "PD"
        ES = "ES", "ES"
        VD = "VD", "VD"
        FV = "FV", "FV"

    class SftpStatus(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        SUCCESS = "success", _("Enviado")
        FAILED = "failed", _("Fallido")
        SKIPPED = "skipped", _("Omitido")

    job = models.ForeignKey(
        MtrixJob,
        on_delete=models.CASCADE,
        related_name="artifacts",
        verbose_name=_("Job"),
    )
    tipo = models.CharField(_("Tipo"), max_length=4, choices=Tipo.choices)
    codigo_proveedor = models.CharField(_("Proveedor"), max_length=32, blank=True)
    filename = models.CharField(_("Nombre archivo"), max_length=255)
    relative_path = models.CharField(_("Ruta relativa"), max_length=512)
    size_bytes = models.PositiveIntegerField(_("Tamaño"), default=0)
    sha256 = models.CharField(_("SHA-256"), max_length=64, blank=True)
    row_count = models.PositiveIntegerField(_("Filas"), default=0)
    sftp_status = models.CharField(
        _("Estado SFTP"),
        max_length=16,
        choices=SftpStatus.choices,
        default=SftpStatus.PENDING,
    )
    sftp_message = models.CharField(_("Mensaje SFTP"), max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Artefacto Mtrix")
        verbose_name_plural = _("Artefactos Mtrix")
        ordering = ["created_at"]
