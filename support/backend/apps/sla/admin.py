from django.contrib import admin
from .models import SLAConfig


@admin.register(SLAConfig)
class SLAConfigAdmin(admin.ModelAdmin):
    list_display = ("company", "case_type", "response_time_minutes", "warning_pct")
