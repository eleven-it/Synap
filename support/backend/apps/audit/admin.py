from django.contrib import admin
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "company", "case", "created_at")
    list_filter = ("event_type",)
    readonly_fields = ("case", "company", "event_type", "payload", "actor", "created_at")
