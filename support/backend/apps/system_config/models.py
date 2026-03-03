"""
Modelos de configuración producto. Persistencia en PostgreSQL.
Multi-tenant: company NULL = global; opcional override por empresa donde aplique.
"""
from django.db import models
from apps.companies.models import Company


class ConfigStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    VALIDATING = "validating", "Validando"
    ACTIVE = "active", "Activo"
    ERROR = "error", "Error"
    DISABLED = "disabled", "Desactivado"


class ChannelType(models.TextChoices):
    TELEGRAM = "telegram", "Telegram"
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"


class ChannelConfig(models.Model):
    """
    Configuración por canal (telegram, whatsapp, email).
    Un registro por (company, channel_type). company NULL = global.
    Secretos en config_encrypted_json; nunca se devuelven completos en API.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="channel_configs",
    )
    channel_type = models.CharField(
        "Tipo de canal",
        max_length=20,
        choices=ChannelType.choices,
    )
    display_name = models.CharField("Nombre para mostrar", max_length=128, blank=True)
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=ConfigStatus.choices,
        default=ConfigStatus.DRAFT,
        db_index=True,
    )
    config_encrypted_json = models.TextField("Config cifrada (tokens, keys, etc.)", blank=True)
    last_check_at = models.DateTimeField("Última comprobación", null=True, blank=True)
    last_error = models.TextField("Último error (humano)", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_system_config_channel"
        verbose_name = "Configuración de canal"
        verbose_name_plural = "Configuraciones de canal"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "channel_type"],
                name="support_sysconfig_channel_company_type_uniq",
            )
        ]
        ordering = ["company_id", "channel_type"]

    def __str__(self):
        scope = self.company_id or "global"
        return f"{self.get_channel_type_display()} ({scope})"


class IAConfig(models.Model):
    """Configuración IA/LLM. Global o por empresa (company nullable)."""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="ia_configs",
    )
    provider = models.CharField("Proveedor", max_length=64, blank=True)
    model = models.CharField("Modelo", max_length=128, blank=True)
    api_key_encrypted = models.TextField("API key cifrada", blank=True)
    limits_json = models.JSONField("Límites (rate, tokens)", default=dict, blank=True)
    prompt_version_id = models.CharField(
        "Versión de prompt",
        max_length=64,
        blank=True,
        null=True,
    )
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=ConfigStatus.choices,
        default=ConfigStatus.DRAFT,
        db_index=True,
    )
    last_check_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_system_config_ia"
        verbose_name = "Configuración IA"
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                name="support_sysconfig_ia_company_uniq",
            )
        ]

    def __str__(self):
        return f"IA ({self.company_id or 'global'})"


class RAGConfig(models.Model):
    """Configuración RAG: top_k, fuentes, cache. Global o por empresa."""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rag_configs",
    )
    top_k = models.PositiveSmallIntegerField("Top K", default=10)
    sources_enabled_json = models.JSONField("Fuentes habilitadas", default=list, blank=True)
    cache_ttl_seconds = models.PositiveIntegerField("TTL caché (s)", default=300)
    status = models.CharField(
        max_length=20,
        choices=ConfigStatus.choices,
        default=ConfigStatus.ACTIVE,
        db_index=True,
    )
    last_ingest_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_system_config_rag"
        verbose_name = "Configuración RAG"
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                name="support_sysconfig_rag_company_uniq",
            )
        ]

    def __str__(self):
        return f"RAG ({self.company_id or 'global'})"


class StorageConfig(models.Model):
    """Configuración almacenamiento S3/compatible. Global."""
    endpoint = models.CharField("Endpoint", max_length=512, blank=True)
    bucket = models.CharField("Bucket", max_length=256, blank=True)
    region = models.CharField("Región", max_length=64, default="us-east-1")
    force_path_style = models.BooleanField("Force path style", default=False)
    access_key_masked = models.CharField(
        "Access key (enmascarado en UI)",
        max_length=64,
        blank=True,
    )
    secret_encrypted = models.TextField("Secret cifrado", blank=True)
    max_size_bytes = models.PositiveIntegerField("Tamaño máximo (bytes)", default=10 * 1024 * 1024)
    allowed_content_types_json = models.JSONField(
        "Content types permitidos",
        default=list,
        blank=True,
    )
    retention_days = models.PositiveIntegerField("Retención (días)", default=365)
    status = models.CharField(
        max_length=20,
        choices=ConfigStatus.choices,
        default=ConfigStatus.DRAFT,
        db_index=True,
    )
    last_check_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_system_config_storage"
        verbose_name = "Configuración storage"
        # Un solo registro global (sin company)
        constraints = []

    def __str__(self):
        return f"Storage {self.bucket or '(sin config)'}"


class SecurityConfig(models.Model):
    """Configuración seguridad: rate limits, anti-spam, PII. Global."""
    rate_limits_json = models.JSONField("Límites por canal/IP", default=dict, blank=True)
    anti_spam_enabled = models.BooleanField("Anti-spam activo", default=True)
    pii_warning_enabled = models.BooleanField("Aviso PII activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_system_config_security"
        verbose_name = "Configuración seguridad"

    def __str__(self):
        return "Seguridad (global)"


class NotificationsConfig(models.Model):
    """Notificaciones y escalamiento. Global."""
    escalation_emails_json = models.JSONField("Emails escalamiento", default=list, blank=True)
    sla_warning_message_template = models.TextField("Plantilla aviso SLA", blank=True)
    sla_breach_message_template = models.TextField("Plantilla SLA vencido", blank=True)
    internal_alert_channel = models.CharField(
        "Canal alertas internas",
        max_length=128,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_system_config_notifications"
        verbose_name = "Configuración notificaciones"

    def __str__(self):
        return "Notificaciones (global)"


class BrandingConfig(models.Model):
    """Branding: nombre asistente, saludo, idioma. Global o por empresa."""
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="branding_configs",
    )
    assistant_name = models.CharField("Nombre del asistente", max_length=128, blank=True)
    welcome_message = models.TextField("Mensaje de bienvenida", blank=True)
    default_language = models.CharField("Idioma por defecto", max_length=10, default="es")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_system_config_branding"
        verbose_name = "Configuración branding"
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                name="support_sysconfig_branding_company_uniq",
            )
        ]

    def __str__(self):
        return f"Branding ({self.company_id or 'global'})"
