from django.db import models

class SystemConfiguration(models.Model):
    key = models.CharField(
        max_length=255, 
        unique=True, 
        help_text="La clave única para la configuración (ej: 'main.site.name')."
    )
    value = models.TextField(
        blank=True,
        help_text="El valor de la configuración."
    )
    description = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Descripción de lo que hace esta configuración."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indica si esta configuración está activa y en uso."
    )

    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"

    def __str__(self):
        return self.key
