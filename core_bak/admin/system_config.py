from django.contrib import admin
from core.models import SystemConfiguration

@admin.register(SystemConfiguration)
class SystemConfigurationAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('key', 'value', 'description')
    ordering = ('key',)