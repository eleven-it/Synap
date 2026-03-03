from django.contrib import admin
from .models import Case, Message, CaseSummary, CaseCounter


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ("number_display", "company", "status", "assigned_to", "created_at")
    list_filter = ("status", "company")
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("case", "sender_type", "direction", "created_at")


@admin.register(CaseSummary)
class CaseSummaryAdmin(admin.ModelAdmin):
    list_display = ("case", "model_version", "created_at")


@admin.register(CaseCounter)
class CaseCounterAdmin(admin.ModelAdmin):
    list_display = ("company", "last_number")
