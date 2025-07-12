from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Report, ReportTemplate, ReportComponent, ReportSchedule


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'empresa', 'branch', 'template', 'created_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'is_public', 'template__category', 'empresa', 'branch', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'template')
        }),
        (_('Company & Branch'), {
            'fields': ('empresa', 'branch', 'created_by')
        }),
        (_('Configuration'), {
            'fields': ('layout_config', 'data_sources', 'filters', 'branding'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_public')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_system', 'version', 'created_at']
    list_filter = ['category', 'is_system', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'description', 'category')
        }),
        (_('Configuration'), {
            'fields': ('layout_schema', 'default_data', 'styling'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('is_system', 'version', 'created_at')
        }),
    )


@admin.register(ReportComponent)
class ReportComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'report', 'component_type', 'z_index']
    list_filter = ['component_type', 'report__empresa', 'report__branch']
    search_fields = ['name', 'report__name']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'report', 'component_type', 'parent')
        }),
        (_('Configuration'), {
            'fields': ('configuration', 'data_source', 'styling'),
            'classes': ('collapse',)
        }),
        (_('Position'), {
            'fields': ('position', 'z_index')
        }),
    )


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'report', 'frequency', 'is_active', 'last_run', 'next_run']
    list_filter = ['frequency', 'is_active', 'export_format', 'created_at']
    search_fields = ['name', 'report__name']
    readonly_fields = ['last_run', 'next_run', 'created_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'report', 'frequency', 'cron_expression')
        }),
        (_('Export Configuration'), {
            'fields': ('export_format', 'recipients', 'subject_template', 'message_template')
        }),
        (_('Status'), {
            'fields': ('is_active', 'last_run', 'next_run', 'created_at')
        }),
    ) 