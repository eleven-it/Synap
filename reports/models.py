from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
# Función dummy para mantener compatibilidad - no se usa internacionalización
def _(s): return s

User = get_user_model()


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
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_("Is visible"),
        help_text=_("Visible reports are shown to all authorized users. Only the supervisor user (cod_usuario) can see deactivated reports and toggle this flag."),
    )
    show_in_catalog = models.BooleanField(
        default=True,
        verbose_name=_("Show in catalog"),
        help_text=_("If enabled, the report will appear in the catalog. This is independent of visibility to users."),
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
            models.Index(fields=["is_visible"], name="reports_visible_idx"),
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


class ReportDefinitionVersion(models.Model):
    """Historial de versiones de configuración de reportes declarativos."""

    report = models.ForeignKey(
        ReportDefinition,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name=_("Report"),
    )
    version_number = models.IntegerField(
        verbose_name=_("Version number"),
        help_text=_("Número de versión incremental"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_versions_created",
        verbose_name=_("Created by"),
    )
    config = models.JSONField(
        verbose_name=_("Configuration"),
        help_text=_("Configuración completa del reporte en esta versión"),
    )
    change_summary = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Change summary"),
        help_text=_("Resumen de los cambios realizados en esta versión"),
    )

    class Meta:
        verbose_name = _("Report definition version")
        verbose_name_plural = _("Report definition versions")
        ordering = ["-created_at"]
        unique_together = (("report", "version_number"),)
        indexes = [
            models.Index(fields=["report", "version_number"], name="reports_version_idx"),
            models.Index(fields=["report", "-created_at"], name="reports_version_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.report.slug} v{self.version_number}"


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


class ReportTemplate(models.Model):
    """Plantilla de reporte para crear nuevos reportes desde una configuración base."""

    name = models.CharField(
        max_length=255,
        verbose_name=_("Name"),
        help_text=_("Nombre descriptivo de la plantilla"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Descripción de qué hace esta plantilla"),
    )
    category = models.CharField(
        max_length=24,
        choices=ReportCategory.choices,
        default=ReportCategory.OPERATIONAL,
        verbose_name=_("Category"),
    )
    config = models.JSONField(
        default=dict,
        verbose_name=_("Configuration"),
        help_text=_("Configuración declarativa del reporte (declarative-v1)"),
    )
    widgets = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Widgets"),
        help_text=_("Lista de widgets preconfigurados para la plantilla"),
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name=_("Is system template"),
        help_text=_("Si es True, es una plantilla del sistema que no puede ser eliminada"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="report_templates_created",
        verbose_name=_("Created by"),
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Report template")
        verbose_name_plural = _("Report templates")
        ordering = ("is_system", "-created_at", "name")

    def __str__(self) -> str:
        system_label = "[Sistema] " if self.is_system else ""
        return f"{system_label}{self.name}"


class LearnedRelationship(models.Model):
    """
    Relaciones aprendidas por uso en el Builder Visual.
    El sistema aprende qué relaciones (JOINs) se usan y funcionan correctamente,
    priorizándolas en el wizard de relaciones.
    """
    
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="learned_relationships",
        verbose_name=_("Company"),
        help_text=_("Empresa específica. NULL significa relación global (todas las empresas)."),
    )
    
    from_table = models.CharField(
        max_length=255,
        verbose_name=_("From Table"),
        help_text=_("Tabla origen de la relación"),
    )
    from_column = models.CharField(
        max_length=255,
        verbose_name=_("From Column"),
        help_text=_("Columna origen de la relación"),
    )
    to_table = models.CharField(
        max_length=255,
        verbose_name=_("To Table"),
        help_text=_("Tabla destino de la relación"),
    )
    to_column = models.CharField(
        max_length=255,
        verbose_name=_("To Column"),
        help_text=_("Columna destino de la relación"),
    )
    
    # Estadísticas de uso
    usage_count = models.IntegerField(
        default=0,
        verbose_name=_("Usage Count"),
        help_text=_("Número de veces que se ha usado esta relación"),
    )
    success_count = models.IntegerField(
        default=0,
        verbose_name=_("Success Count"),
        help_text=_("Número de veces que se ha usado exitosamente"),
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Used At"),
        help_text=_("Última vez que se usó esta relación"),
    )
    
    # Clasificación
    confidence = models.FloatField(
        default=0.5,
        verbose_name=_("Confidence"),
        help_text=_("Confianza en la relación (0.0 a 1.0). Mayor = más confiable"),
    )
    source = models.CharField(
        max_length=32,
        default="usage",
        verbose_name=_("Source"),
        help_text=_("Origen de la relación: 'usage' (aprendida por uso), 'manual' (creada manualmente)"),
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name=_("Is Blocked"),
        help_text=_("Si está bloqueada, no se sugerirá ni aprenderá"),
    )
    
    # Nuevos campos para gobernanza y validación
    class RelationshipStatus(models.TextChoices):
        PROPOSED = "proposed", _("Proposed")
        APPROVED = "approved", _("Approved")
        DEPRECATED = "deprecated", _("Deprecated")
    
    status = models.CharField(
        max_length=16,
        choices=RelationshipStatus.choices,
        default=RelationshipStatus.PROPOSED,
        verbose_name=_("Status"),
        help_text=_("Estado de la relación: proposed (pendiente), approved (aprobada), deprecated (deprecada)"),
    )
    
    match_rule_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Match Rule JSON"),
        help_text=_("Reglas de transformación para matching (TRIM, UPPER, CAST, REPLACE, CONCAT)"),
    )
    
    validation_metrics_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Validation Metrics JSON"),
        help_text=_("Métricas de validación: match_rate, null_rate, duplicates_dest, cardinality_est"),
    )
    
    confidence_calculated = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("Confidence Calculated"),
        help_text=_("Confianza calculada automáticamente por validación"),
    )
    
    confidence_override = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("Confidence Override"),
        help_text=_("Confianza manualmente sobrescrita por administrador"),
    )
    
    deprecated_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("Deprecated Reason"),
        help_text=_("Razón por la cual la relación fue deprecada"),
    )
    
    version = models.IntegerField(
        default=1,
        verbose_name=_("Version"),
        help_text=_("Versión de la relación (se incrementa al editar)"),
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Learned Relationship")
        verbose_name_plural = _("Learned Relationships")
        unique_together = ("empresa", "from_table", "from_column", "to_table", "to_column")
        indexes = [
            models.Index(fields=["empresa", "from_table"], name="learned_rel_empresa_from_idx"),
            models.Index(fields=["empresa", "to_table"], name="learned_rel_empresa_to_idx"),
            models.Index(fields=["from_table", "to_table"], name="learned_rel_tables_idx"),
            models.Index(fields=["-confidence", "-last_used_at"], name="learned_rel_ranking_idx"),
        ]
        ordering = ["-confidence", "-last_used_at"]
    
    def __str__(self) -> str:
        empresa_str = f"{self.empresa.name} - " if self.empresa else "Global - "
        status_str = f" [{self.get_status_display()}]" if self.status else ""
        return f"{empresa_str}{self.from_table}.{self.from_column} → {self.to_table}.{self.to_column} (conf: {self.confidence:.2f}){status_str}"
    
    @property
    def effective_confidence(self):
        """Retorna la confianza efectiva (override > calculated > confidence)."""
        if self.confidence_override is not None:
            return self.confidence_override
        if self.confidence_calculated is not None:
            return self.confidence_calculated
        return self.confidence
    
    @property
    def is_active(self):
        """Retorna True si la relación está activa (approved y no bloqueada)."""
        return self.status == self.RelationshipStatus.APPROVED and not self.is_blocked


class TableClusterAssignment(models.Model):
    """
    Asignación personalizada de tablas a clusters.
    Permite a los usuarios organizar manualmente las tablas en clusters
    en lugar de usar solo heurísticas automáticas.
    """
    
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="table_cluster_assignments",
        verbose_name=_("Company"),
        help_text=_("Company that owns this cluster assignment. Null means global."),
    )
    
    base_empresa = models.CharField(
        max_length=128,
        verbose_name=_("Base Empresa"),
        help_text=_("Base de datos MySQL donde se encuentra la tabla"),
    )
    
    cluster_id = models.CharField(
        max_length=128,
        verbose_name=_("Cluster ID"),
        help_text=_("Identificador único del cluster (ej: 'ventas', 'inventario')"),
    )
    
    cluster_label = models.CharField(
        max_length=255,
        verbose_name=_("Cluster Label"),
        help_text=_("Etiqueta descriptiva del cluster (ej: 'Ventas', 'Inventario')"),
    )
    
    table_name = models.CharField(
        max_length=255,
        verbose_name=_("Table Name"),
        help_text=_("Nombre de la tabla asignada a este cluster"),
    )
    
    order = models.IntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Orden de visualización dentro del cluster"),
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_cluster_assignments",
        verbose_name=_("Created By"),
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )
    
    class Meta:
        verbose_name = _("Table Cluster Assignment")
        verbose_name_plural = _("Table Cluster Assignments")
        unique_together = [
            ("base_empresa", "table_name"),  # Una tabla solo puede estar en un cluster por base_empresa
        ]
        indexes = [
            models.Index(fields=["base_empresa", "cluster_id"]),
            models.Index(fields=["empresa", "base_empresa"]),
        ]
    
    def __str__(self):
        return f"{self.cluster_label} - {self.table_name}"


class RelationshipAuditLog(models.Model):
    """
    Log de auditoría para cambios en relaciones aprendidas.
    Registra todas las acciones (crear, aprobar, deprecar, editar) con diff.
    """
    
    relationship = models.ForeignKey(
        LearnedRelationship,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        verbose_name=_("Relationship"),
    )
    
    action = models.CharField(
        max_length=32,
        verbose_name=_("Action"),
        help_text=_("Acción realizada: created, approved, deprecated, edited, deleted"),
    )
    
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relationship_audit_logs",
        verbose_name=_("Actor"),
        help_text=_("Usuario que realizó la acción"),
    )
    
    diff_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Diff JSON"),
        help_text=_("Cambios realizados (antes/después)"),
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Notas adicionales sobre la acción"),
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    
    class Meta:
        verbose_name = _("Relationship Audit Log")
        verbose_name_plural = _("Relationship Audit Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["relationship", "-created_at"], name="audit_log_rel_created_idx"),
            models.Index(fields=["actor", "-created_at"], name="audit_log_actor_created_idx"),
        ]
    
    def __str__(self) -> str:
        actor_str = self.actor.username if self.actor else "System"
        return f"{actor_str} - {self.action} - {self.relationship} ({self.created_at})"


class PuntoVentaCanalEjecutivo(models.Model):
    """
    Clasificación Mayorista / Minorista (salón) por PV para el panel ejecutivo de ventas.
    Persistido en Synap (no en MySQL legacy). PV sin fila aquí se tratan como «sin asignar».
    """

    class Canal(models.TextChoices):
        MAYORISTA = "mayorista", _("Mayorista")
        MINORISTA = "minorista", _("Minorista (Salón)")

    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="punto_venta_canales_ejecutivo",
        verbose_name=_("Empresa"),
    )
    id_pv = models.PositiveIntegerField(verbose_name=_("ID punto de venta (AdministraNET)"))
    canal = models.CharField(
        max_length=16,
        choices=Canal.choices,
        verbose_name=_("Canal"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Clasificación PV — panel ejecutivo")
        verbose_name_plural = _("Clasificaciones PV — panel ejecutivo")
        constraints = [
            models.UniqueConstraint(
                fields=("empresa", "id_pv"),
                name="reports_pv_canal_unico_por_empresa",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa", "id_pv"], name="reports_pv_canal_emp_pv_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.empresa_id} PV {self.id_pv} → {self.canal}"


