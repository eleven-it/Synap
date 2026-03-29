import hashlib
import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


def documento_fuente_upload_to(instance: "DocumentoFuente", filename: str) -> str:
    carpeta = uuid.uuid4().hex[:16]
    return f"factura_compra/{instance.expediente_id}/{carpeta}/{filename}"


class DocumentoFuente(models.Model):
    """Archivo capturado (imagen/PDF) asociado al expediente; pipeline OCR asíncrono."""

    class EstadoProcesamiento(models.TextChoices):
        PENDIENTE = "pendiente", _("OCR pendiente")
        PROCESANDO = "procesando", _("OCR en curso")
        COMPLETADO = "completado", _("OCR completado")
        FALLIDO = "fallido", _("OCR fallido")

    class TipoArchivo(models.TextChoices):
        IMAGEN = "imagen", _("Imagen")
        PDF = "pdf", _("PDF")

    expediente = models.ForeignKey(
        "factura_compra_captura.ExpedienteFacturaCompra",
        on_delete=models.CASCADE,
        related_name="documentos_fuente",
    )
    archivo = models.FileField(
        upload_to=documento_fuente_upload_to,
        max_length=512,
    )
    nombre_original = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    tamano_bytes = models.PositiveBigIntegerField(default=0)
    sha256_hex = models.CharField(max_length=64, blank=True, db_index=True)
    tipo_archivo = models.CharField(
        max_length=16,
        choices=TipoArchivo.choices,
        default=TipoArchivo.IMAGEN,
    )
    estado_procesamiento = models.CharField(
        max_length=20,
        choices=EstadoProcesamiento.choices,
        default=EstadoProcesamiento.PENDIENTE,
        db_index=True,
    )
    ocr_intento = models.PositiveIntegerField(default=0)
    ocr_error_codigo = models.CharField(max_length=64, blank=True)
    ocr_error_detalle = models.TextField(blank=True)
    resultado_ocr = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Documento fuente (factura compra)")
        verbose_name_plural = _("Documentos fuente (factura compra)")
        ordering = ["creado_en"]
        indexes = [
            models.Index(fields=["expediente", "estado_procesamiento"]),
        ]

    def __str__(self):
        return f"Doc {self.pk} exp={self.expediente_id} ({self.estado_procesamiento})"

    def calcular_sha256(self) -> str:
        h = hashlib.sha256()
        with self.archivo.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
