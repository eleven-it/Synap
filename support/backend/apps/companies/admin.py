from django.contrib import admin
from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("synap_id", "prefix", "language", "is_active")
    list_filter = ("is_active",)
