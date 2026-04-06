from django.db import models


class EcomMigrationCheckpoint(models.Model):
    """Marca de avance por submódulo migrado desde PHP (PostgreSQL)."""

    module_slug = models.SlugField("módulo", max_length=64, unique=True, db_index=True)
    notes = models.TextField("notas", blank=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "checkpoint de migración e-com"
        verbose_name_plural = "checkpoints de migración e-com"

    def __str__(self) -> str:
        return self.module_slug


class EcomMailQueue(models.Model):
    """Cola async de envío de mails para relays e-com."""

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_ERROR = "error"
    STATUS_CHOICES = (
        (STATUS_PENDING, "pendiente"),
        (STATUS_SENT, "enviado"),
        (STATUS_ERROR, "error"),
    )

    created_at = models.DateTimeField("creado", auto_now_add=True)
    updated_at = models.DateTimeField("actualizado", auto_now=True)
    status = models.CharField("estado", max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveIntegerField("intentos", default=0)
    last_error = models.TextField("último error", blank=True)

    base_empresa = models.CharField("base empresa", max_length=64, db_index=True)
    to_email = models.EmailField("destinatario")
    subject = models.CharField("asunto", max_length=255)
    body_text = models.TextField("cuerpo texto")
    body_html = models.TextField("cuerpo html", blank=True)
    payload_json = models.JSONField("payload", default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "cola mail e-com"
        verbose_name_plural = "cola mails e-com"

    def __str__(self) -> str:
        return f"{self.to_email} [{self.status}]"
