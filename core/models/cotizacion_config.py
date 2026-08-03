"""Configuración de cotización BCRA por empresa (Postgres Synap)."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

TIPO_COTIZACION_CHOICES = (
    ("bcra_referencia", "BCRA referencia"),
    ("bcra_compra", "BCRA compra"),
    ("bcra_venta", "BCRA venta"),
    ("mid", "Promedio compra/venta"),
    ("manual_only", "Solo manual (sin sugerencia BCRA)"),
)


class CotizacionConfig(models.Model):
    """Parámetros de cotización dólar por base MySQL de empresa."""

    BASE_DEFAULT = "__default__"

    base_empresa = models.CharField(max_length=64, unique=True)
    id_cotizacion = models.PositiveIntegerField(default=1)
    tipo_cotizacion = models.CharField(
        max_length=32,
        choices=TIPO_COTIZACION_CHOICES,
        default="bcra_referencia",
    )
    auto_aceptar_job = models.BooleanField(default=False)
    timeout_seg = models.PositiveSmallIntegerField(default=5)
    actualizado_por = models.CharField(max_length=64, default="sistema")
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración cotización dólar"
        verbose_name_plural = "Configuraciones cotización dólar"

    def __str__(self) -> str:
        return f"Cotización {self.base_empresa}"

    def clean(self) -> None:
        super().clean()
        if self.tipo_cotizacion not in dict(TIPO_COTIZACION_CHOICES):
            raise ValidationError({"tipo_cotizacion": "Tipo de cotización no permitido."})
        if self.timeout_seg is not None and self.timeout_seg < 1:
            raise ValidationError({"timeout_seg": "El timeout debe ser al menos 1 segundo."})
