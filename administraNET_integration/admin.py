from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import AdministraNETConfig, TableMapping, SyncLog


@admin.register(AdministraNETConfig)
class AdministraNETConfigAdmin(admin.ModelAdmin):
    """
    Admin para configuración de administraNET
    """
    list_display = [
        'database_name', 'host', 'port', 'is_active', 
        'sync_interval', 'last_sync', 'created_at'
    ]
    list_filter = ['is_active', 'enable_logging', 'log_level', 'created_at']
    search_fields = ['host', 'database_name', 'username']
    readonly_fields = ['created_at', 'updated_at', 'last_sync']
    
    fieldsets = (
        (_('Conexión'), {
            'fields': ('host', 'port', 'database_name', 'username', 'password')
        }),
        (_('Configuración'), {
            'fields': ('is_active', 'sync_interval')
        }),
        (_('Logs'), {
            'fields': ('enable_logging', 'log_level')
        }),
        (_('Información'), {
            'fields': ('created_at', 'updated_at', 'last_sync'),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Hacer algunos campos de solo lectura si es una instancia existente"""
        if obj:  # Editando una instancia existente
            return self.readonly_fields + ('host', 'port', 'database_name', 'username')
        return self.readonly_fields
    
    def save_model(self, request, obj, form, change):
        """Guardar modelo con validación adicional"""
        if not change:  # Nueva instancia
            # Desactivar otras configuraciones
            AdministraNETConfig.objects.update(is_active=False)
        
        super().save_model(request, obj, form, change)


@admin.register(TableMapping)
class TableMappingAdmin(admin.ModelAdmin):
    """
    Admin para mapeos de tablas
    """
    list_display = [
        'mapping_type', 'administraNET_table', 'synap_model', 
        'is_active', 'sync_direction', 'sync_frequency', 'use_preset_mapping'
    ]
    list_filter = [
        'mapping_type', 'is_active', 'sync_direction', 'use_preset_mapping', 'created_at'
    ]
    search_fields = ['administraNET_table', 'synap_model']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Mapeo'), {
            'fields': ('mapping_type', 'administraNET_table', 'synap_model', 'use_preset_mapping')
        }),
        (_('Configuración'), {
            'fields': ('is_active', 'sync_direction', 'sync_frequency')
        }),
        (_('Campos'), {
            'fields': ('field_mappings',),
            'description': _('Mapeo de campos en formato JSON')
        }),
        (_('Información'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_form(self, request, obj=None, **kwargs):
        """Personalizar formulario"""
        form = super().get_form(request, obj, **kwargs)
        if 'field_mappings' in form.base_fields:
            form.base_fields['field_mappings'].help_text = _(
                'Formato JSON: {"campo_admin": "campo_synap"}'
            )
        return form


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    """
    Admin para logs de sincronización
    """
    list_display = [
        'sync_type', 'status', 'started_at', 'duration_display', 
        'records_processed', 'records_created', 'records_updated', 'records_failed'
    ]
    list_filter = [
        'sync_type', 'status', 'started_at', 'completed_at'
    ]
    search_fields = ['error_message']
    readonly_fields = [
        'sync_type', 'status', 'started_at', 'completed_at',
        'records_processed', 'records_created', 'records_updated', 
        'records_failed', 'error_message', 'error_details', 'initiated_by'
    ]
    date_hierarchy = 'started_at'
    
    fieldsets = (
        (_('Información General'), {
            'fields': ('sync_type', 'status', 'started_at', 'completed_at', 'initiated_by')
        }),
        (_('Estadísticas'), {
            'fields': (
                'records_processed', 'records_created', 'records_updated',
                'records_failed'
            )
        }),
        (_('Detalles'), {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """No permitir crear logs manualmente"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir editar logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permitir eliminar logs"""
        return True
    
    def get_queryset(self, request):
        """Optimizar consulta"""
        return super().get_queryset(request).select_related('initiated_by')
    
    def duration_display(self, obj):
        """Mostrar duración de forma legible"""
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        return "-"
    duration_display.short_description = _('Duración')
    
    def records_summary(self, obj):
        """Mostrar resumen de registros"""
        return f"P:{obj.records_processed} C:{obj.records_created} U:{obj.records_updated} F:{obj.records_failed}"
    records_summary.short_description = _('Resumen')
    
    def get_list_display(self, request):
        """Personalizar list_display según permisos"""
        list_display = list(super().get_list_display(request))
        if not request.user.is_superuser:
            # Remover campos sensibles para usuarios no superuser
            sensitive_fields = ['records_created', 'records_updated', 'records_failed']
            list_display = [f for f in list_display if f not in sensitive_fields]
            list_display.append('records_summary')
        return list_display


# Personalizar el admin site
admin.site.site_header = _('Administración Synap')
admin.site.site_title = _('Synap Admin')
admin.site.index_title = _('Panel de Control')

# Agregar acciones personalizadas
@admin.action(description=_('Activar integración'))
def activate_integration(modeladmin, request, queryset):
    """Activar integración seleccionada"""
    queryset.update(is_active=True)
    modeladmin.message_user(request, _('Integración activada exitosamente.'))

@admin.action(description=_('Desactivar integración'))
def deactivate_integration(modeladmin, request, queryset):
    """Desactivar integración seleccionada"""
    queryset.update(is_active=False)
    modeladmin.message_user(request, _('Integración desactivada exitosamente.'))

# Agregar acciones al admin
AdministraNETConfigAdmin.actions = [activate_integration, deactivate_integration]
