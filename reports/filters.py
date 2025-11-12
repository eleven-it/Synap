import django_filters

from .models import ReportDefinition, ReportCategory


class ReportDefinitionFilter(django_filters.FilterSet):
    """Filtros reutilizables para catálogos de reportes."""

    category = django_filters.ChoiceFilter(choices=ReportCategory.choices)
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = ReportDefinition
        fields = ("category", "is_active")


