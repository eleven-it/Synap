from rest_framework import serializers
# Función dummy para mantener compatibilidad - no se usa internacionalización
def _(s): return s

from .models import ReportDefinition, ReportWidget, ReportDashboard, ReportCategory
from .services.catalog_service import CatalogEntry


class ReportWidgetSerializer(serializers.ModelSerializer):
    """Serializer para widgets de reportes."""

    class Meta:
        model = ReportWidget
        fields = ("id", "name", "widget_type", "order", "layout", "configuration")


class ReportDefinitionSerializer(serializers.ModelSerializer):
    """Serializer para definiciones de reportes."""

    widgets = ReportWidgetSerializer(many=True, read_only=True)

    class Meta:
        model = ReportDefinition
        fields = (
            "id",
            "slug",
            "name",
            "description",
            "category",
            "version",
            "config",
            "metadata",
            "refresh_interval",
            "widgets",
        )


class CatalogEntrySerializer(serializers.Serializer):
    """Serializer para entradas del catálogo agrupadas por categoría."""

    slug = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    category = serializers.ChoiceField(choices=ReportCategory.choices)
    refresh_interval = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField(), default=list())
    metrics = serializers.ListField(child=serializers.CharField(), default=list())
    dimensions = serializers.ListField(child=serializers.CharField(), default=list())
    version = serializers.CharField()
    is_visible = serializers.BooleanField(default=True)

    @classmethod
    def from_catalog_entry(cls, entry: CatalogEntry) -> dict:
        """Construye un diccionario serializable desde la entrada de dominio."""
        return {
            "slug": entry.slug,
            "name": entry.name,
            "description": entry.description,
            "category": entry.category,
            "refresh_interval": entry.refresh_interval,
            "tags": entry.tags,
            "metrics": entry.metrics,
            "dimensions": entry.dimensions,
            "version": entry.version,
            "is_visible": getattr(entry, "is_visible", True),
        }


class ReportQueryRequestSerializer(serializers.Serializer):
    """Entrada para consultas parametrizadas."""

    slug = serializers.SlugField()
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    metrics = serializers.ListField(child=serializers.CharField(), required=False)
    dimensions = serializers.ListField(child=serializers.CharField(), required=False)
    # filters puede contener cualquier tipo de valor: strings, números, booleanos, listas, etc.
    filters = serializers.DictField(required=False, allow_empty=True)
    group_by = serializers.ListField(child=serializers.CharField(), required=False)
    limit = serializers.IntegerField(default=5000, min_value=1, max_value=20000)


class ReportQueryResponseSerializer(serializers.Serializer):
    """Salida estándar de consultas de reportes."""

    meta = serializers.DictField()
    data = serializers.ListField(child=serializers.DictField(), default=list)
    totals = serializers.DictField(child=serializers.FloatField(), default=dict)
    notes = serializers.ListField(child=serializers.CharField(), default=list)


class KPIResponseSerializer(serializers.Serializer):
    """Respuesta simplificada para KPIs puntuales."""

    kpi = serializers.CharField()
    value = serializers.FloatField()
    unit = serializers.CharField()
    breakdown = serializers.DictField(child=serializers.FloatField())


class ReportDashboardSerializer(serializers.ModelSerializer):
    """Serializer para dashboards guardados."""

    class Meta:
        model = ReportDashboard
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "layout",
            "filters",
            "is_shared",
            "created_at",
            "updated_at",
        )


