from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from ia.services.secrets import decrypt_secret, encrypt_secret

def _(text):
    return text


class ProviderKind(models.TextChoices):
    OPENAI = "openai", _("OpenAI")
    ANTHROPIC = "anthropic", _("Anthropic / Claude")
    OPENAI_COMPATIBLE = "openai_compatible", _("OpenAI-compatible")
    LOCAL = "local", _("Local / SML")


class ConversationStatus(models.TextChoices):
    ACTIVE = "active", _("Activa")
    ARCHIVED = "archived", _("Archivada")
    CLOSED = "closed", _("Cerrada")


class ConversationChannel(models.TextChoices):
    WEB = "web", _("Web")
    PWA = "pwa", _("PWA")
    MOBILE = "mobile", _("Mobile")
    DESKTOP = "desktop", _("Desktop")
    API = "api", _("API")


class MessageRole(models.TextChoices):
    USER = "user", _("Usuario")
    ASSISTANT = "assistant", _("Asistente")
    SYSTEM = "system", _("Sistema")
    TOOL = "tool", _("Herramienta")


class ExecutionStatus(models.TextChoices):
    SUCCESS = "success", _("Éxito")
    ERROR = "error", _("Error")
    REJECTED = "rejected", _("Rechazada")
    PARTIAL = "partial", _("Parcial")


class ToolExecutionStatus(models.TextChoices):
    SUCCESS = "success", _("Éxito")
    ERROR = "error", _("Error")
    REJECTED = "rejected", _("Rechazada")


class MemoryScope(models.TextChoices):
    TENANT = "tenant", _("Tenant")
    AGENT = "agent", _("Agente")
    USER = "user", _("Usuario")
    CONVERSATION = "conversation", _("Conversación")


class MemoryType(models.TextChoices):
    PROFILE = "profile", _("Perfil")
    EPISODIC = "episodic", _("Episódica")
    SEMANTIC = "semantic", _("Semántica")
    WORKING = "working", _("Trabajo")


class MemorySensitivity(models.TextChoices):
    LOW = "low", _("Baja")
    INTERNAL = "internal", _("Interna")
    RESTRICTED = "restricted", _("Restringida")


class LlmProviderConfig(models.Model):
    """Configuración de proveedor/model gateway con secreto cifrado en BD."""

    name = models.CharField(max_length=100, unique=True, verbose_name=_("Nombre"))
    provider_kind = models.CharField(
        max_length=32,
        choices=ProviderKind.choices,
        verbose_name=_("Tipo de proveedor"),
    )
    base_url = models.URLField(blank=True, verbose_name=_("Base URL"))
    api_key_env_var = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Variable de entorno para API key"),
        help_text=_("Campo legacy. La configuración principal debe cargarse por UI."),
    )
    encrypted_api_key = models.TextField(blank=True, verbose_name=_("API key cifrada"))
    api_key_last4 = models.CharField(max_length=8, blank=True, verbose_name=_("Últimos 4"))
    organization_id = models.CharField(max_length=120, blank=True, verbose_name=_("Organization / Workspace"))
    available_models = models.JSONField(default=list, blank=True, verbose_name=_("Modelos disponibles"))
    extra_config = models.JSONField(default=dict, blank=True, verbose_name=_("Configuración extra"))
    is_active = models.BooleanField(default=True, verbose_name=_("Activo"))
    supports_structured_output = models.BooleanField(default=True)
    supports_tool_use = models.BooleanField(default=True)
    supports_streaming = models.BooleanField(default=True)
    supports_vision = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Actualizado"))

    class Meta:
        verbose_name = _("Configuración de proveedor LLM")
        verbose_name_plural = _("Configuraciones de proveedores LLM")
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.provider_kind})"

    @property
    def is_configured(self) -> bool:
        return bool(self.encrypted_api_key)

    @property
    def masked_api_key(self) -> str:
        if not self.api_key_last4:
            return ""
        return f"••••••••{self.api_key_last4}"

    def set_api_key(self, raw_api_key: str) -> None:
        raw_api_key = (raw_api_key or "").strip()
        if not raw_api_key:
            self.encrypted_api_key = ""
            self.api_key_last4 = ""
            return
        self.encrypted_api_key = encrypt_secret(raw_api_key)
        self.api_key_last4 = raw_api_key[-4:]

    def get_api_key(self) -> str:
        if self.encrypted_api_key:
            return decrypt_secret(self.encrypted_api_key)
        return ""


class AgentDefinition(models.Model):
    """Definición persistente de un agente IA."""

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ia_agents",
        verbose_name=_("Empresa"),
        help_text=_("Null indica agente global."),
    )
    slug = models.SlugField(max_length=120, verbose_name=_("Slug"))
    name = models.CharField(max_length=150, verbose_name=_("Nombre"))
    description = models.TextField(blank=True, verbose_name=_("Descripción"))
    domain = models.CharField(max_length=80, default="general", verbose_name=_("Dominio"))
    system_prompt = models.TextField(blank=True, verbose_name=_("Prompt del sistema"))
    soul_summary = models.TextField(blank=True, verbose_name=_("Resumen del alma"))
    required_permission = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name=_("Permiso requerido"),
        help_text=_("Si está vacío, basta con autenticación."),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Activo"))
    is_system = models.BooleanField(default=True, verbose_name=_("Agente del sistema"))
    default_provider = models.ForeignKey(
        LlmProviderConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents_default",
        verbose_name=_("Proveedor por defecto"),
    )
    fallback_provider = models.ForeignKey(
        LlmProviderConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agents_fallback",
        verbose_name=_("Proveedor fallback"),
    )
    default_model_name = models.CharField(max_length=120, blank=True, verbose_name=_("Modelo principal"))
    tool_use_model_name = models.CharField(max_length=120, blank=True, verbose_name=_("Modelo tool use"))
    memory_write_model_name = models.CharField(max_length=120, blank=True, verbose_name=_("Modelo memoria"))
    fast_model_name = models.CharField(max_length=120, blank=True, verbose_name=_("Modelo rápido"))
    fallback_model_name = models.CharField(max_length=120, blank=True, verbose_name=_("Modelo fallback"))
    reasoning_profile = models.CharField(max_length=40, blank=True, default="balanced")
    max_input_tokens = models.PositiveIntegerField(default=16000)
    max_output_tokens = models.PositiveIntegerField(default=4000)
    supports_structured_output = models.BooleanField(default=True)
    supports_parallel_tool_calls = models.BooleanField(default=False)
    supports_streaming = models.BooleanField(default=True)
    supports_vision = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True, verbose_name=_("Configuración"))
    memory_policy = models.JSONField(default=dict, blank=True, verbose_name=_("Política de memoria"))
    ui_config = models.JSONField(default=dict, blank=True, verbose_name=_("Configuración UI"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Actualizado"))

    class Meta:
        verbose_name = _("Definición de agente")
        verbose_name_plural = _("Definiciones de agentes")
        unique_together = (("empresa", "slug"),)
        ordering = ("name",)
        indexes = [
            models.Index(fields=["empresa", "slug"], name="ia_agent_empresa_slug_idx"),
            models.Index(fields=["is_active"], name="ia_agent_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class AgentConversation(models.Model):
    """Conversación persistente del usuario con un agente."""

    conversation_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    agent = models.ForeignKey(
        AgentDefinition,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name=_("Agente"),
    )
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ia_conversations",
        verbose_name=_("Empresa"),
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ia_conversations",
        verbose_name=_("Usuario Synap"),
    )
    owner_legacy_user_id = models.IntegerField(null=True, blank=True, verbose_name=_("ID usuario legacy"))
    owner_legacy_user_code = models.CharField(max_length=80, blank=True, verbose_name=_("Código usuario legacy"))
    title = models.CharField(max_length=200, blank=True, verbose_name=_("Título"))
    status = models.CharField(
        max_length=20,
        choices=ConversationStatus.choices,
        default=ConversationStatus.ACTIVE,
        verbose_name=_("Estado"),
    )
    channel = models.CharField(
        max_length=20,
        choices=ConversationChannel.choices,
        default=ConversationChannel.WEB,
        verbose_name=_("Canal"),
    )
    pwa_context = models.JSONField(default=dict, blank=True, verbose_name=_("Contexto PWA"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    last_message_at = models.DateTimeField(default=timezone.now, verbose_name=_("Último mensaje"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Actualizado"))

    class Meta:
        verbose_name = _("Conversación de agente")
        verbose_name_plural = _("Conversaciones de agentes")
        ordering = ("-last_message_at", "-created_at")
        indexes = [
            models.Index(fields=["agent", "status"], name="ia_conv_agent_status_idx"),
            models.Index(fields=["empresa", "-last_message_at"], name="ia_conv_empresa_last_idx"),
            models.Index(fields=["owner_legacy_user_id"], name="ia_conv_legacy_user_id_idx"),
        ]

    def __str__(self) -> str:
        label = self.title or self.agent.name
        return f"{label} [{self.conversation_uuid}]"


class AgentMessage(models.Model):
    """Mensajes persistidos dentro de una conversación."""

    conversation = models.ForeignKey(
        AgentConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Conversación"),
    )
    role = models.CharField(max_length=20, choices=MessageRole.choices, verbose_name=_("Rol"))
    content = models.TextField(verbose_name=_("Contenido"))
    structured_content = models.JSONField(default=dict, blank=True, verbose_name=_("Contenido estructurado"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))

    class Meta:
        verbose_name = _("Mensaje de agente")
        verbose_name_plural = _("Mensajes de agentes")
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="ia_msg_conv_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.role} - {self.created_at:%Y-%m-%d %H:%M:%S}"


class AgentExecution(models.Model):
    """Registro de una ejecución del orquestador."""

    conversation = models.ForeignKey(
        AgentConversation,
        on_delete=models.CASCADE,
        related_name="executions",
        verbose_name=_("Conversación"),
    )
    agent = models.ForeignKey(
        AgentDefinition,
        on_delete=models.CASCADE,
        related_name="executions",
        verbose_name=_("Agente"),
    )
    request_message = models.ForeignKey(
        AgentMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="request_executions",
        verbose_name=_("Mensaje de solicitud"),
    )
    response_message = models.ForeignKey(
        AgentMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="response_executions",
        verbose_name=_("Mensaje de respuesta"),
    )
    provider_config = models.ForeignKey(
        LlmProviderConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions",
        verbose_name=_("Proveedor"),
    )
    model_name = models.CharField(max_length=120, blank=True, verbose_name=_("Modelo"))
    task_type = models.CharField(max_length=40, default="conversation", verbose_name=_("Tipo de tarea"))
    status = models.CharField(
        max_length=20,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.SUCCESS,
        verbose_name=_("Estado"),
    )
    request_payload = models.JSONField(default=dict, blank=True, verbose_name=_("Payload request"))
    response_payload = models.JSONField(default=dict, blank=True, verbose_name=_("Payload response"))
    memory_items_read = models.PositiveIntegerField(default=0)
    memory_items_written = models.PositiveIntegerField(default=0)
    tool_calls_count = models.PositiveIntegerField(default=0)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, verbose_name=_("Error"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))

    class Meta:
        verbose_name = _("Ejecución de agente")
        verbose_name_plural = _("Ejecuciones de agentes")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["agent", "-created_at"], name="ia_exec_agent_created_idx"),
            models.Index(fields=["status"], name="ia_exec_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.agent.slug} - {self.status} - {self.created_at:%Y-%m-%d %H:%M:%S}"


class AgentToolExecution(models.Model):
    """Trazabilidad de herramientas ejecutadas durante una ejecución."""

    execution = models.ForeignKey(
        AgentExecution,
        on_delete=models.CASCADE,
        related_name="tool_executions",
        verbose_name=_("Ejecución"),
    )
    tool_name = models.CharField(max_length=120, verbose_name=_("Herramienta"))
    status = models.CharField(
        max_length=20,
        choices=ToolExecutionStatus.choices,
        default=ToolExecutionStatus.SUCCESS,
        verbose_name=_("Estado"),
    )
    input_payload = models.JSONField(default=dict, blank=True, verbose_name=_("Input"))
    output_payload = models.JSONField(default=dict, blank=True, verbose_name=_("Output"))
    duration_ms = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True, verbose_name=_("Error"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))

    class Meta:
        verbose_name = _("Ejecución de herramienta")
        verbose_name_plural = _("Ejecuciones de herramientas")
        ordering = ("created_at", "id")
        indexes = [
            models.Index(fields=["execution", "tool_name"], name="ia_tool_exec_tool_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.tool_name} - {self.status}"


class AgentMemoryItem(models.Model):
    """Memoria persistente gobernada por agente, tenant y usuario."""

    agent = models.ForeignKey(
        AgentDefinition,
        on_delete=models.CASCADE,
        related_name="memory_items",
        verbose_name=_("Agente"),
    )
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ia_memory_items",
        verbose_name=_("Empresa"),
    )
    conversation = models.ForeignKey(
        AgentConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memory_items",
        verbose_name=_("Conversación origen"),
    )
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ia_memory_items",
        verbose_name=_("Usuario Synap"),
    )
    owner_legacy_user_id = models.IntegerField(null=True, blank=True, verbose_name=_("ID usuario legacy"))
    owner_legacy_user_code = models.CharField(max_length=80, blank=True, verbose_name=_("Código usuario legacy"))
    scope = models.CharField(max_length=20, choices=MemoryScope.choices, default=MemoryScope.USER)
    memory_type = models.CharField(max_length=20, choices=MemoryType.choices, default=MemoryType.EPISODIC)
    sensitivity = models.CharField(
        max_length=20,
        choices=MemorySensitivity.choices,
        default=MemorySensitivity.INTERNAL,
    )
    key = models.CharField(max_length=120, blank=True, verbose_name=_("Clave"))
    content = models.TextField(verbose_name=_("Contenido"))
    source_summary = models.TextField(blank=True, verbose_name=_("Resumen de origen"))
    confidence = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("0.50"))
    is_confirmed = models.BooleanField(default=False, verbose_name=_("Confirmada"))
    is_active = models.BooleanField(default=True, verbose_name=_("Activa"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Expira"))
    last_accessed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Último acceso"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Actualizado"))

    class Meta:
        verbose_name = _("Ítem de memoria")
        verbose_name_plural = _("Ítems de memoria")
        ordering = ("-updated_at", "-created_at")
        indexes = [
            models.Index(fields=["agent", "scope"], name="ia_mem_agent_scope_idx"),
            models.Index(fields=["empresa", "memory_type"], name="ia_mem_empresa_type_idx"),
            models.Index(fields=["owner_legacy_user_id"], name="ia_mem_legacy_user_id_idx"),
            models.Index(fields=["is_active", "expires_at"], name="ia_mem_active_exp_idx"),
        ]

    def __str__(self) -> str:
        key = self.key or self.memory_type
        return f"{self.agent.slug} - {key}"

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())


class AgentMemoryFeedback(models.Model):
    """Feedback para validar o corregir memorias del agente."""

    class FeedbackValue(models.TextChoices):
        ACCEPT = "accept", _("Aceptar")
        REJECT = "reject", _("Rechazar")
        CORRECT = "correct", _("Corregir")

    memory_item = models.ForeignKey(
        AgentMemoryItem,
        on_delete=models.CASCADE,
        related_name="feedback_entries",
        verbose_name=_("Memoria"),
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ia_memory_feedback",
        verbose_name=_("Usuario Synap"),
    )
    actor_legacy_user_id = models.IntegerField(null=True, blank=True, verbose_name=_("ID usuario legacy"))
    actor_legacy_user_code = models.CharField(max_length=80, blank=True, verbose_name=_("Código usuario legacy"))
    feedback_value = models.CharField(max_length=20, choices=FeedbackValue.choices)
    notes = models.TextField(blank=True, verbose_name=_("Notas"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))

    class Meta:
        verbose_name = _("Feedback de memoria")
        verbose_name_plural = _("Feedback de memoria")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.memory_item_id} - {self.feedback_value}"


class LearningExampleSource(models.TextChoices):
    """Origen del ejemplo para dataset de afinado / fine-tuning."""

    AUTO_SUCCESS = "auto_success", _("Turno exitoso (automático)")
    USER_POSITIVE = "user_positive", _("Valoración positiva del usuario")
    USER_CORRECTION = "user_correction", _("Corrección del usuario")
    ADMIN = "admin", _("Curado por administrador")


class LearningExampleStatus(models.TextChoices):
    """Estado en el flujo de revisión antes de exportar o entrenar."""

    PENDING = "pending", _("Pendiente de revisión")
    APPROVED = "approved", _("Aprobado para entrenamiento")
    REJECTED = "rejected", _("Rechazado")
    EXPORTED = "exported", _("Ya exportado a dataset externo")


class AgentLearningExample(models.Model):
    """
    Ejemplo de conversación candidato para afinado del modelo (fine-tuning) o RAG.

    No sustituye la memoria episódica: sirve para acumular pares supervisados
    con revisión humana y exportación JSONL compatible con APIs de fine-tuning.
    """

    agent = models.ForeignKey(
        AgentDefinition,
        on_delete=models.CASCADE,
        related_name="learning_examples",
        verbose_name=_("Agente"),
    )
    conversation = models.ForeignKey(
        AgentConversation,
        on_delete=models.CASCADE,
        related_name="learning_examples",
        verbose_name=_("Conversación"),
    )
    execution = models.OneToOneField(
        AgentExecution,
        on_delete=models.CASCADE,
        related_name="learning_example",
        verbose_name=_("Ejecución origen"),
    )
    user_message = models.ForeignKey(
        AgentMessage,
        on_delete=models.CASCADE,
        related_name="learning_examples_as_user",
        verbose_name=_("Mensaje usuario"),
    )
    assistant_message = models.ForeignKey(
        AgentMessage,
        on_delete=models.CASCADE,
        related_name="learning_examples_as_assistant",
        verbose_name=_("Mensaje asistente"),
    )
    source = models.CharField(
        max_length=32,
        choices=LearningExampleSource.choices,
        default=LearningExampleSource.AUTO_SUCCESS,
        verbose_name=_("Origen"),
    )
    status = models.CharField(
        max_length=20,
        choices=LearningExampleStatus.choices,
        default=LearningExampleStatus.PENDING,
        verbose_name=_("Estado"),
    )
    messages_payload = models.JSONField(
        default=list,
        verbose_name=_("Mensajes (formato chat)"),
        help_text=_("Lista de {role, content} para export JSONL / fine-tuning."),
    )
    system_prompt_snapshot = models.TextField(blank=True, verbose_name=_("System prompt al capturar"))
    review_notes = models.TextField(blank=True, verbose_name=_("Notas de revisión"))
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Revisado el"))
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ia_learning_reviews",
        verbose_name=_("Revisado por"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Creado"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Actualizado"))

    class Meta:
        verbose_name = _("Ejemplo de aprendizaje (IA)")
        verbose_name_plural = _("Ejemplos de aprendizaje (IA)")
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["agent", "status"], name="ia_learn_agent_status_idx"),
            models.Index(fields=["agent", "-created_at"], name="ia_learn_agent_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.agent.slug} — {self.get_status_display()} ({self.created_at:%Y-%m-%d})"
