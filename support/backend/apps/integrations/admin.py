from django.contrib import admin
from .models import CopilotMessage


@admin.register(CopilotMessage)
class CopilotMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "case", "created_at")
