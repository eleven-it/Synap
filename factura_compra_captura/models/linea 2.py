from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class LineaExpedienteCompra(models.Model):
    expediente = models.ForeignKey(
        "factura_compra_captura.ExpedienteFacturaCompra",
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    orden = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    id_art_legacy = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("ID artículo legacy"),
    )
    codgasto_legacy = models.PositiveIntegerField(null=True, blank=True)
    cantidad = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    precio_unitario = models.DecimalField(max_digits=18, decimal_places=4, default=Decimal("0"))
    codigo_movimiento_oc = models.PositiveIntegerField(null=True, blank=True)
    codigo_movimiento_remito = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = _("Línea expediente compra")
        verbose_name_plural = _("Líneas expediente compra")
        ordering = ["expediente", "orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["expediente", "orden"],
                name="uniq_linea_expediente_orden",
            ),
        ]

    def __str__(self):
        return f"Línea {self.orden} exp {self.expediente_id}"
