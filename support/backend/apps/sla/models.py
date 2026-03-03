"""ConfigSLA: empresa + tipo de caso, tiempo_respuesta_minutos, warning_pct."""
from django.db import models
from apps.companies.models import Company


class SLAConfig(models.Model):
    """Configuración SLA por empresa y tipo de caso."""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="sla_configs",
    )
    case_type = models.CharField("Tipo de caso", max_length=64, default="default")
    response_time_minutes = models.PositiveIntegerField("Tiempo respuesta (min)")
    warning_pct = models.PositiveSmallIntegerField("Porcentaje warning (70 u 80)", default=80)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_sla_config"
        verbose_name = "Configuración SLA"
        verbose_name_plural = "Configuraciones SLA"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "case_type"],
                name="support_sla_config_company_case_type_unique",
            )
        ]

    def __str__(self) -> str:
        return f"{self.company.prefix} / {self.case_type}"
