from django.contrib import admin

from .models import ReportDefinition, ReportWidget, ReportDashboard, ReportExecutionLog, ReportWorkspace


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


