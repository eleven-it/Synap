"""Caso, Mensaje, ResumenIA y contador por empresa."""
from django.conf import settings
from django.db import models
from apps.companies.models import Company


class CaseStatus(models.TextChoices):
    INICIADO = "iniciado", "Iniciado"
    EN_ANALISIS_IA = "en_analisis_ia", "En análisis IA"
    ESPERANDO_RESPUESTA_USUARIO = "esperando_respuesta_usuario", "Esperando respuesta del usuario"
    DERIVADO_A_HUMANO = "derivado_a_humano", "Derivado a humano"
    ASIGNADO_A_AGENTE_HUMANO = "asignado_a_agente_humano", "Asignado a agente humano"
    EN_PROCESO_HUMANO = "en_proceso_humano", "En proceso (humano)"
    RESUELTO = "resuelto", "Resuelto"
    CERRADO = "cerrado", "Cerrado"
    REABIERTO = "reabierto", "Reabierto"


class CaseCounter(models.Model):
    """Contador de casos por empresa para numeración SUP-{PREFIJO}-000123."""
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="case_counter",
    )
    last_number = models.PositiveIntegerField("Último número", default=0)

    class Meta:
        db_table = "support_case_counter"
        verbose_name = "Contador de casos"

    def get_next_number(self) -> int:
        self.last_number += 1
        self.save(update_fields=["last_number"])
        return self.last_number


class Case(models.Model):
    """
    Caso de soporte. numero_display = SUP-{prefijo}-{numero_secuencial:06d}.
    SLA: inicio al asignar agente, pausa en esperando_respuesta_usuario.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="cases",
    )
    number_sequential = models.PositiveIntegerField("Número secuencial")
    number_display = models.CharField("Número display (SUP-...)", max_length=64, unique=True, db_index=True)
    status = models.CharField(
        "Estado",
        max_length=32,
        choices=CaseStatus.choices,
        default=CaseStatus.INICIADO,
        db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_cases",
    )
    # SLA runtime
    sla_started_at = models.DateTimeField("SLA inicio", null=True, blank=True)
    sla_due_at = models.DateTimeField("SLA límite", null=True, blank=True)
    sla_paused_since = models.DateTimeField("SLA pausado desde", null=True, blank=True)
    sla_warning_sent_at = models.DateTimeField("SLA warning enviado", null=True, blank=True)
    sla_breached_at = models.DateTimeField("SLA vencido", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_case"
        verbose_name = "Caso"
        verbose_name_plural = "Casos"
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["sla_due_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.number_display


class MessageSenderType(models.TextChoices):
    USER = "user", "Usuario"
    SYSTEM = "system", "Sistema"
    AGENT = "agent", "Agente"
    AI = "ai", "IA"
    SLA = "sla", "SLA"


class MessageDirection(models.TextChoices):
    INBOUND = "inbound", "Entrante"
    OUTBOUND = "outbound", "Saliente"


class Message(models.Model):
    """
    Mensaje en el timeline del caso. Inmutable (no updated_at).
    remitente: usuario, sistema, agente, ia, sla.
    Dedupe por canal: (channel_type, external_message_id) único cuando external_message_id no vacío.
    """
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    channel_type = models.CharField("Tipo canal", max_length=20, blank=True)
    external_channel_id = models.CharField("ID externo canal", max_length=255, blank=True)
    external_message_id = models.CharField(
        "ID mensaje en el canal (evita duplicados por webhook)",
        max_length=255,
        blank=True,
        db_index=True,
    )
    sender_type = models.CharField(
        "Remitente",
        max_length=20,
        choices=MessageSenderType.choices,
    )
    sender_user_id = models.PositiveIntegerField(
        "User ID si remitente=agent",
        null=True,
        blank=True,
    )
    content = models.TextField("Contenido")
    direction = models.CharField(
        "Dirección",
        max_length=10,
        choices=MessageDirection.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_message"
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"
        indexes = [
            models.Index(fields=["case", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["channel_type", "external_message_id"],
                name="support_message_channel_external_msg_uniq",
                condition=models.Q(external_message_id__gt=""),
            )
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.case_id} @ {self.created_at} ({self.sender_type})"


class CaseSummary(models.Model):
    """Resumen IA de un rango de mensajes del caso. Versionado."""
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="summaries",
    )
    from_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    to_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    summary_text = models.TextField("Texto del resumen")
    model_version = models.CharField("Modelo/versión", max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_case_summary"
        verbose_name = "Resumen IA"
        verbose_name_plural = "Resúmenes IA"
        indexes = [
            models.Index(fields=["case"]),
        ]
