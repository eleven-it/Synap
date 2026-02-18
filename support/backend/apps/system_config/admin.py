from django.contrib import admin
from .models import (
    BrandingConfig,
    ChannelConfig,
    IAConfig,
    NotificationsConfig,
    RAGConfig,
    SecurityConfig,
    StorageConfig,
)


@admin.register(ChannelConfig)
class ChannelConfigAdmin(admin.ModelAdmin):
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
