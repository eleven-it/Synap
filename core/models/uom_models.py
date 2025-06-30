from django.db import models
from django.utils.translation import gettext_lazy as _

class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=50)  # Ej: Unidad, Kilogramo, Litro
    code = models.CharField(max_length=10, unique=True)  # Ej: un, kg, l
    category = models.CharField(
        max_length=50,
        help_text=_("E.g. quantity, weight, volume, length, etc.")
    )
    ratio = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        help_text=_("Multiplicative factor with respect to the reference unit of the category.")
    )
    is_reference = models.BooleanField(
        default=False,
        help_text=_("Marks if this is the base unit of its category.")
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = _("Unit of Measure")
        verbose_name_plural = _("Units of Measure")