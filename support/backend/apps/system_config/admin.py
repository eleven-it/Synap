import json

from django import forms
from django.contrib import admin

from .crypto_utils import decrypt_json, encrypt_json, mask_secret
from .models import (
    BrandingConfig,
    ChannelConfig,
    IAConfig,
    NotificationsConfig,
    RAGConfig,
    SecurityConfig,
    StorageConfig,
)


class ChannelConfigAdminForm(forms.ModelForm):
    """
    Permite editar la config como token en claro o JSON; al guardar se cifra.
    Si se deja vacío, no se reemplaza la config existente.
    """
    config_plain = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        label="Token o config JSON (se guarda cifrado)",
        help_text="Telegram: pegar solo el token del bot. O JSON: {\"token\": \"...\"}. Vacío = no cambiar.",
    )

    class Meta:
        model = ChannelConfig
        exclude = ("config_encrypted_json",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.config_encrypted_json:
            data = decrypt_json(self.instance.config_encrypted_json)
            if data and isinstance(data, dict):
                tok = data.get("token") or data.get("bot_token")
                if tok:
                    self.fields["config_plain"].help_text = (
                        "Actual: " + mask_secret(tok) + " (dejar vacío para no cambiar). "
                        "Pegar nuevo token o JSON para reemplazar."
                    )

    def save(self, commit=True):
        plain = (self.cleaned_data.get("config_plain") or "").strip()
        if plain:
            if plain.startswith("{"):
                try:
                    data = json.loads(plain)
                except json.JSONDecodeError:
                    data = {"token": plain}
            else:
                data = {"token": plain}
            self.instance.config_encrypted_json = encrypt_json(data)
        return super().save(commit)


@admin.register(ChannelConfig)
class ChannelConfigAdmin(admin.ModelAdmin):
    form = ChannelConfigAdminForm
    list_display = ("channel_type", "company", "status", "last_check_at")
    list_filter = ("channel_type", "status")
    search_fields = ("display_name",)


@admin.register(IAConfig)
class IAConfigAdmin(admin.ModelAdmin):
    list_display = ("provider", "model", "company", "status", "last_check_at")


@admin.register(RAGConfig)
class RAGConfigAdmin(admin.ModelAdmin):
    list_display = ("company", "top_k", "status", "last_ingest_at")


@admin.register(StorageConfig)
class StorageConfigAdmin(admin.ModelAdmin):
    list_display = ("bucket", "endpoint", "status", "last_check_at")


@admin.register(SecurityConfig)
class SecurityConfigAdmin(admin.ModelAdmin):
    list_display = ("anti_spam_enabled", "pii_warning_enabled")


@admin.register(NotificationsConfig)
class NotificationsConfigAdmin(admin.ModelAdmin):
    list_display = ("internal_alert_channel",)


@admin.register(BrandingConfig)
class BrandingConfigAdmin(admin.ModelAdmin):
    list_display = ("company", "assistant_name", "default_language")
