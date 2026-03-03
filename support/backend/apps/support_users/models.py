"""Usuario de soporte (final) e identidades de canal."""
from django.db import models
from apps.companies.models import Company


class SupportUser(models.Model):
    """
    Usuario final que recibe soporte. Asociado a una empresa.
    Alta y autorización solo desde backoffice.
    """
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="support_users",
    )
    name = models.CharField("Nombre", max_length=255)
    language = models.CharField("Idioma", max_length=10, default="es")
    is_authorized = models.BooleanField("Autorizado", default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "support_support_user"
        verbose_name = "Usuario de soporte"
        verbose_name_plural = "Usuarios de soporte"

    def __str__(self) -> str:
        return f"{self.name} ({self.company.prefix})"


class ChannelType(models.TextChoices):
    TELEGRAM = "telegram", "Telegram"
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"


class ChannelIdentity(models.Model):
    """
    Identidad de canal: telegram_user_id, E.164 o email.
    Un usuario puede tener varias identidades. Único (tipo_canal, external_id).
    """
    support_user = models.ForeignKey(
        SupportUser,
        on_delete=models.CASCADE,
        related_name="channel_identities",
    )
    channel_type = models.CharField(
        "Tipo canal",
        max_length=20,
        choices=ChannelType.choices,
    )
    external_id = models.CharField("ID externo (telegram_id, E.164, email)", max_length=255)
    metadata = models.JSONField("Metadata", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "support_channel_identity"
        verbose_name = "Identidad de canal"
        verbose_name_plural = "Identidades de canal"
        constraints = [
            models.UniqueConstraint(
                fields=["channel_type", "external_id"],
                name="support_channel_identity_unique",
            )
        ]
        indexes = [
            models.Index(fields=["support_user"]),
        ]

    def __str__(self) -> str:
        return f"{self.channel_type}:{self.external_id}"
