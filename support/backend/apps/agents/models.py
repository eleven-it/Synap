"""Perfil de agente (rol) vinculado a User de Django."""
from django.conf import settings
from django.db import models


class AgentRole(models.TextChoices):
    ADMIN = "admin", "Administrador"
    AGENT = "agent", "Agente"
    SUPERVISOR = "supervisor", "Supervisor"


class AgentProfile(models.Model):
    """Rol del usuario backoffice (Admin, Agente, Supervisor)."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_profile",
    )
    role = models.CharField(
        "Rol",
        max_length=20,
        choices=AgentRole.choices,
        default=AgentRole.AGENT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_agent_profile"
        verbose_name = "Perfil de agente"
        verbose_name_plural = "Perfiles de agente"

    def __str__(self) -> str:
        return f"{self.user.username} ({self.get_role_display()})"
