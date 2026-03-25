import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ExpedienteFacturaCompra(models.Model):
    """Aggregate root — ciclo interno hasta aprobación/rechazo (sin posting legacy en Fase 1)."""

    class Estado(models.TextChoices):
        BORRADOR = "borrador", _("Borrador")
        OCR_COMPLETADO = "ocr_completado", _("OCR completado")
        EN_REVISION = "en_revision", _("En revisión")
        LISTO_PARA_APROBAR = "listo_para_aprobar", _("Listo para aprobar")
        APROBACION_SOLICITADA = "aprobacion_solicitada", _("Aprobación solicitada")
        APROBADO = "aprobado", _("Aprobado")
        RECHAZADO = "rechazado", _("Rechazado")
        ERROR_POSTING = "error_posting", _("Error en posting")

    class OrigenDatos(models.TextChoices):
        MANUAL = "MANUAL", _("Manual")
        REMITO = "REMITO", _("Remito")
        OC = "OC", _("Orden de compra")
        VALE = "VALE", _("Vale")

    class PostingStatus(models.TextChoices):
        NOT_ATTEMPTED = "not_attempted", _("No intentado")
        IN_PROGRESS = "in_progress", _("En curso")
        POSTED = "posted", _("Posteado")
        FAILED = "failed", _("Fallido")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.PROTECT,
        related_name="expedientes_factura_compra",
    )
    sucursal_codigo_legacy = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Código sucursal legacy (opcional)"),
    )
    estado = models.CharField(
        max_length=32,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        db_index=True,
    )
    origen_datos = models.CharField(
        max_length=16,
        choices=OrigenDatos.choices,
        default=OrigenDatos.MANUAL,
    )
    codigo_proveedor_legacy = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Código proveedor AdministraNET"),
    )
    metadata = models.JSONField(default=dict, blank=True)
    posting_status = models.CharField(
        max_length=24,
        choices=PostingStatus.choices,
        default=PostingStatus.NOT_ATTEMPTED,
    )
    posting_attempt = models.PositiveIntegerField(default=0)
    idempotency_key_last = models.CharField(max_length=128, blank=True)
    legacy_codigo_movimiento = models.PositiveIntegerField(null=True, blank=True)
    legacy_nro_comprobante = models.CharField(max_length=64, blank=True)
    rechazo_motivo = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="expedientes_factura_compra_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Expediente factura de compra")
        verbose_name_plural = _("Expedientes factura de compra")
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["estado", "empresa"]),
        ]
        permissions = [
            ("crear", "Puede crear expedientes de factura de compra"),
            ("ver", "Puede ver expedientes de factura de compra"),
            ("editar", "Puede editar expedientes de factura de compra"),
            ("revisar", "Puede enviar a revisión y marcar listo para aprobar"),
            ("aprobar", "Puede aprobar expedientes (posting stub o real)"),
            ("rechazar", "Puede rechazar expedientes"),
            ("reintentar_posting", "Puede reintentar posting tras error"),
        ]

    def __str__(self):
        return f"Expediente {self.id} ({self.get_estado_display()})"
