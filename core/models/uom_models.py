from django.db import models

class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=50)  # Ej: Unidad, Kilogramo, Litro
    code = models.CharField(max_length=10, unique=True)  # Ej: un, kg, l
    category = models.CharField(
        max_length=50,
        help_text="Ej: cantidad, peso, volumen, longitud, etc."
    )
    ratio = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        help_text="Factor multiplicador respecto a la unidad de referencia de la categoría."
    )
    is_reference = models.BooleanField(
        default=False,
        help_text="Marca si esta es la unidad base de su categoría."
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"