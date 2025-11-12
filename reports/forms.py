from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ReportDashboard, ReportCategory


class DashboardFilterForm(forms.Form):
    """Formulario de filtros globales para dashboards."""

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "synap-input"}),
        label=_("Date from"),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "synap-input"}),
        label=_("Date to"),
    )
    business_unit = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "synap-input", "placeholder": _("Business unit")}),
        label=_("Business unit"),
    )
    channel = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "synap-input", "placeholder": _("Channel")}),
        label=_("Channel"),
    )


class DashboardSaveForm(forms.ModelForm):
    """Formulario para guardar dashboards personalizados."""

    class Meta:
        model = ReportDashboard
        fields = ("name", "slug", "category", "is_shared")
        widgets = {
            "name": forms.TextInput(attrs={"class": "synap-input", "placeholder": _("Dashboard name")}),
            "slug": forms.TextInput(attrs={"class": "synap-input", "placeholder": _("Slug")}),
            "category": forms.Select(attrs={"class": "synap-select"}, choices=ReportCategory.choices),
            "is_shared": forms.CheckboxInput(attrs={"class": "synap-checkbox"}),
        }
        labels = {
            "name": _("Name"),
            "slug": _("Slug"),
            "category": _("Category"),
            "is_shared": _("Shared with the organization"),
        }


