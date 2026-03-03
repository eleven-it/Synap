"""Modelos de integraciones si se necesitan (ej. CopilotConversation para historial agente-IA)."""
from django.conf import settings
from django.db import models
from apps.cases.models import Case


class CopilotMessage(models.Model):
    """Mensaje del chat agente ↔ IA (copiloto) en contexto opcional de caso."""
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="copilot_messages",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="copilot_messages",
    )
    role = models.CharField("Rol", max_length=10, choices=[("user", "Usuario"), ("assistant", "IA")])
    content = models.TextField("Contenido")
    created_at = models.DateTimeField(auto_now_add=True)
    # Guardar conocimiento: si True, este mensaje se convirtió en chunk (human_note/resolved_case)
    saved_to_knowledge = models.BooleanField("Guardado como conocimiento", default=False)
    knowledge_chunk_id = models.PositiveIntegerField(
        "ID del chunk creado (referencia a support_knowledge_chunk)",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "support_copilot_message"
        verbose_name = "Mensaje copiloto"
        ordering = ["created_at"]
