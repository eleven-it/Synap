from django.contrib import admin

from .models import ReportDefinition, ReportWidget, ReportDashboard, ReportExecutionLog, ReportWorkspace, ReportTemplate, LearnedRelationship


@admin.register(ReportDefinition)
class ReportDefinitionAdmin(admin.ModelAdmin):
    """Admin de definiciones de reportes."""

    list_display = ("name", "slug", "category", "empresa", "is_active", "refresh_interval")
    list_filter = ("category", "is_active", "refresh_interval")
    search_fields = ("name", "slug", "description")
    ordering = ("name",)


@admin.register(ReportWidget)
class ReportWidgetAdmin(admin.ModelAdmin):
    """Admin de widgets."""

    list_display = ("name", "report", "widget_type", "order")
    list_filter = ("widget_type",)
    search_fields = ("name", "report__name", "report__slug")
    ordering = ("report", "order")


@admin.register(ReportDashboard)
class ReportDashboardAdmin(admin.ModelAdmin):
    """Admin de dashboards guardados."""

    list_display = ("name", "empresa", "owner", "category", "is_shared")
    list_filter = ("category", "is_shared")
    search_fields = ("name", "slug", "owner__email")
    ordering = ("name",)


@admin.register(ReportExecutionLog)
class ReportExecutionLogAdmin(admin.ModelAdmin):
    """Admin de logs de ejecución."""

    list_display = ("report", "executed_by", "executed_at", "status", "duration_ms")
    list_filter = ("status", "executed_at")
    search_fields = ("report__name", "report__slug", "executed_by__email")
    ordering = ("-executed_at",)


@admin.register(ReportWorkspace)
class ReportWorkspaceAdmin(admin.ModelAdmin):
    """Admin para workspaces persistentes."""

    list_display = ("owner", "empresa", "name", "updated_at")
    list_filter = ("empresa",)
    search_fields = ("owner__email", "owner__username")
    ordering = ("owner", "empresa")


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    """Admin para plantillas de reportes."""

    list_display = ("name", "category", "is_system", "created_by", "created_at")
    list_filter = ("category", "is_system", "created_at")
    search_fields = ("name", "description")
    ordering = ("is_system", "-created_at", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LearnedRelationship)
class LearnedRelationshipAdmin(admin.ModelAdmin):
    """Admin para relaciones aprendidas por uso."""

    list_display = ("empresa", "from_table", "from_column", "to_table", "to_column", "confidence", "usage_count", "success_count", "is_blocked", "last_used_at")
    list_filter = ("empresa", "source", "is_blocked", "last_used_at")
    search_fields = ("from_table", "from_column", "to_table", "to_column")
    ordering = ("-confidence", "-last_used_at")
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ("Relación", {
            "fields": ("empresa", "from_table", "from_column", "to_table", "to_column")
        }),
        ("Estadísticas", {
            "fields": ("usage_count", "success_count", "last_used_at", "confidence")
        }),
        ("Control", {
            "fields": ("source", "is_blocked")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )


