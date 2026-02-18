"""Modelo Empresa (referencia Synap + prefijo numeración)."""
from django.db import models


class Company(models.Model):
    """
    Empresa. synap_id referencia al ERP (integración solo vía API).
    prefijo se usa para numeración de casos: SUP-{prefijo}-000123.
    """
    synap_id = models.CharField("ID Synap", max_length=64, unique=True, db_index=True)
    prefix = models.CharField("Prefijo numeración", max_length=32)
    language = models.CharField("Idioma", max_length=10, default="es")
    is_active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_company"
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self) -> str:
        return f"{self.prefix} ({self.synap_id})"
