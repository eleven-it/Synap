from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class EventoAuditoriaInterno(models.Model):
    expediente = models.ForeignKey(
        "factura_compra_captura.ExpedienteFacturaCompra",
        on_delete=models.CASCADE,
        related_name="eventos_auditoria",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="eventos_auditoria_expediente_compra",
    )
    tipo_evento = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Evento auditoría interno (expediente compra)")
        verbose_name_plural = _("Eventos auditoría interno (expediente compra)")
        ordering = ["creado_en"]

    def __str__(self):
        return f"{self.tipo_evento} @ {self.creado_en}"
