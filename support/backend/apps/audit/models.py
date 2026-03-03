"""Evento de auditoría append-only."""
from django.conf import settings
from django.db import models
from apps.companies.models import Company
from apps.cases.models import Case


class AuditEventType(models.TextChoices):
    CREACION_CASO = "creacion_caso", "Creación caso"
    CAMBIO_ESTADO = "cambio_estado", "Cambio estado"
    ASIGNACION = "asignacion", "Asignación"
    MENSAJE_RECIBIDO = "mensaje_recibido", "Mensaje recibido"
    MENSAJE_ENVIADO = "mensaje_enviado", "Mensaje enviado"
    ACCION_IA = "accion_ia", "Acción IA"
    SLA_INICIO = "sla_inicio", "SLA inicio"
    SLA_PAUSA = "sla_pausa", "SLA pausa"
    SLA_REANUDACION = "sla_reanudacion", "SLA reanudación"
    SLA_WARNING = "sla_warning", "SLA warning"
    SLA_VENCIDO = "sla_vencido", "SLA vencido"
    REAPERTURA = "reapertura", "Reapertura"
    ADJUNTO_DESCARGA = "adjunto_descarga", "Descarga adjunto"
    ACCESO_CASO = "acceso_caso", "Acceso caso"
    # Configuración producto (Admin)
    CONFIG_UPDATED = "config.updated", "Config actualizada"
    CONFIG_TESTED = "config.tested", "Config probada"
    CONFIG_ACTIVATED = "config.activated", "Config activada"
    CONFIG_DEACTIVATED = "config.deactivated", "Config desactivada"


class AuditEvent(models.Model):
    """Event log append-only. Solo inserciones."""
    case = models.ForeignKey(
        Case,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event_type = models.CharField(
        "Tipo evento",
        max_length=32,
        choices=AuditEventType.choices,
        db_index=True,
    )
    payload = models.JSONField("Payload", default=dict)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_audit_event"
        verbose_name = "Evento auditoría"
        verbose_name_plural = "Eventos auditoría"
        indexes = [
            models.Index(fields=["case", "created_at"]),
            models.Index(fields=["company", "event_type", "created_at"]),
        ]
        ordering = ["-created_at"]


class IdempotencyRecord(models.Model):
    """
    Clave de idempotencia por (caso, clave, actor). Si se repite la misma acción,
    se devuelve el mismo resultado sin repetir efectos.
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    action_key = models.CharField("Clave idempotencia (UUID)", max_length=64, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="idempotency_records",
    )
    status_code = models.PositiveSmallIntegerField("Código HTTP guardado")
    response_payload = models.JSONField("Payload resumido de la respuesta", default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_idempotency_record"
        verbose_name = "Registro idempotencia"
        constraints = [
            models.UniqueConstraint(
                fields=["case", "action_key", "actor"],
                name="support_idempotency_case_key_actor_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["case", "action_key", "actor"]),
        ]
