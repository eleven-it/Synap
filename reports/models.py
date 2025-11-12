from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ReportCategory(models.TextChoices):
    """Categorías estándar de reportes."""

    OPERATIONAL = "operational", _("Operational")
    MANAGERIAL = "managerial", _("Managerial")


class RefreshInterval(models.TextChoices):
    """Frecuencias soportadas para precálculos."""

    REALTIME = "realtime", "Casi en tiempo real"
    HOURLY = "hourly", "Horario"
    DAILY = "daily", "Diario"
    WEEKLY = "weekly", "Semanal"
    MONTHLY = "monthly", "Mensual"


class ReportDefinition(models.Model):
    """Definición declarativa de un reporte o conjunto de métricas."""

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="report_definitions",
        verbose_name=_("Company"),
        help_text=_("Company that owns this report definition. Null means global."),
    )
    slug = models.SlugField(
        max_length=128,
        verbose_name=_("Slug"),
        help_text=_("Unique identifier used to query the report via API."),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        help_text=_("Friendly name displayed in the catalog."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Short description, supports markdown for highlights."),
    )
    category = models.CharField(
        max_length=24,
        choices=ReportCategory.choices,
        default=ReportCategory.OPERATIONAL,
        verbose_name=_("Category"),
    )
    version = models.CharField(
        max_length=16,
        default="1.0.0",
        verbose_name=_("Version"),
        help_text=_("Semantic version of the definition for cache invalidation."),
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Configuration"),
        help_text=_("Declarative configuration (metrics, dimensions, datasource)."),
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Metadata"),
        help_text=_("Additional metadata such as owners, tags or compliance info."),
    )
    refresh_interval = models.CharField(
        max_length=16,
        choices=RefreshInterval.choices,
        default=RefreshInterval.DAILY,
        verbose_name=_("Refresh interval"),
        help_text=_("Recommended refresh cadence for aggregates."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is active"),
        help_text=_("Inactive definitions are hidden from catalogs and APIs."),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_created",
        verbose_name=_("Created by"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_updated",
        verbose_name=_("Updated by"),
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Report definition")
        verbose_name_plural = _("Report definitions")
        ordering = ("name",)
        unique_together = (("empresa", "slug"),)
        indexes = [
            models.Index(fields=["empresa", "category"], name="reports_by_company_cat"),
            models.Index(fields=["slug"], name="reports_slug_idx"),
            models.Index(fields=["is_active"], name="reports_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"

    def is_operational(self) -> bool:
        """Indica si el reporte es operativo."""
        return self.category == ReportCategory.OPERATIONAL

    def is_managerial(self) -> bool:
        """Indica si el reporte es gerencial."""
        return self.category == ReportCategory.MANAGERIAL


class ReportWidget(models.Model):
    """Definición de widget reusable para dashboards."""

    report = models.ForeignKey(
        ReportDefinition,
        on_delete=models.CASCADE,
        related_name="widgets",
        verbose_name=_("Report"),
    )
    name = models.CharField(max_length=128, verbose_name=_("Widget name"))
    widget_type = models.CharField(
        max_length=64,
        verbose_name=_("Type"),
        help_text=_("Type identifier, e.g. d3-line, d3-waterfall, pivot-table."),
    )
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))
    layout = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Layout"),
        help_text=_("Grid layout definition (cols, rows, responsive breakpoints)."),
    )
    configuration = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Configuration"),
        help_text=_("Visualization settings and bindings for the widget."),
    )

    class Meta:
        verbose_name = _("Report widget")
        verbose_name_plural = _("Report widgets")
        ordering = ("report", "order", "name")

    def __str__(self) -> str:
        return f"{self.report.slug}:{self.name}"


class ReportDashboard(models.Model):
    """Dashboard personalizado guardado por usuario o compartido."""

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="report_dashboards",
        verbose_name=_("Company"),
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_dashboards",
        verbose_name=_("Owner"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    slug = models.SlugField(
        max_length=128,
        verbose_name=_("Slug"),
        help_text=_("Identifier to expose saved dashboards in URLs."),
    )
    category = models.CharField(
        max_length=24,
        choices=ReportCategory.choices,
        default=ReportCategory.OPERATIONAL,
        verbose_name=_("Category"),
    )
    layout = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Layout"),
        help_text=_("Serialized layout with widget ordering and sizing."),
    )
    filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Default filters"),
    )
    is_shared = models.BooleanField(
        default=False,
        verbose_name=_("Shared"),
        help_text=_("Shared dashboards are visible to roles with matching permissions."),
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Report dashboard")
        verbose_name_plural = _("Report dashboards")
        ordering = ("name",)
        unique_together = (("empresa", "slug"),)

    def __str__(self) -> str:
        return f"{self.name} ({self.empresa})"


class ReportExecutionLog(models.Model):
    """Historial de ejecuciones de reportes para auditoría."""

    report = models.ForeignKey(
        ReportDefinition,
        on_delete=models.CASCADE,
        related_name="execution_logs",
        verbose_name=_("Report"),
    )
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_execution_logs",
        verbose_name=_("Executed by"),
    )
    executed_at = models.DateTimeField(default=timezone.now, verbose_name=_("Executed at"))
    status = models.CharField(
        max_length=32,
        default="success",
        verbose_name=_("Status"),
        help_text=_("Execution result status."),
    )
    filters_snapshot = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Filters snapshot"),
        help_text=_("Filters applied when the report was executed."),
    )
    duration_ms = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Execution time (ms)"),
        help_text=_("Total execution duration in milliseconds."),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Optional information about the execution."),
    )

    class Meta:
        verbose_name = _("Report execution log")
        verbose_name_plural = _("Report execution logs")
        ordering = ("-executed_at",)
        indexes = [
            models.Index(fields=["executed_at"], name="reports_execution_date_idx"),
            models.Index(fields=["status"], name="reports_execution_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.report.slug} - {self.executed_at:%Y-%m-%d %H:%M:%S}"


class ReportWorkspace(models.Model):
    """Seleccion de reportes favoritos para el modo workspace."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_workspaces",
        verbose_name=_("Owner"),
    )
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="report_workspaces",
        verbose_name=_("Company"),
    )
    name = models.CharField(
        max_length=128,
        default="Workspace",
        verbose_name=_("Name"),
    )
    items = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Reports"),
        help_text=_("List of report slugs included in the workspace."),
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Report workspace")
        verbose_name_plural = _("Report workspaces")
        unique_together = ("owner", "empresa")

    def __str__(self) -> str:
        empresa = getattr(self.empresa, "nombre", None) or "Global"
        return f"Workspace {self.owner} ({empresa})"


