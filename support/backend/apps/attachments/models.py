"""Adjunto: metadata + bucket/key, content_type, size, hash opcional."""
from django.db import models
from apps.cases.models import Message


class Attachment(models.Model):
    """Metadata del adjunto. Archivo en S3; URLs firmadas bajo demanda."""
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    bucket = models.CharField("Bucket", max_length=255)
    storage_key = models.CharField("Key en storage", max_length=512)
    content_type = models.CharField("Content-Type", max_length=128)
    size_bytes = models.PositiveIntegerField("Tamaño bytes")
    original_name = models.CharField("Nombre original", max_length=255)
    content_hash = models.CharField("Hash (opcional)", max_length=64, blank=True)
    is_sensitive = models.BooleanField("Contenido sensible", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_attachment"
        verbose_name = "Adjunto"
        verbose_name_plural = "Adjuntos"
        indexes = [
            models.Index(fields=["message"]),
        ]

    def __str__(self) -> str:
        return self.original_name or self.storage_key
