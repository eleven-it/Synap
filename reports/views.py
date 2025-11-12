from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, ListView

from .domain import build_catalog_for_user
from .models import ReportDefinition, ReportDashboard, ReportCategory
from .permissions import OperationalReportsPermission, ManagerialReportsPermission


class ReportsCatalogView(LoginRequiredMixin, TemplateView):
    """Vista principal del catálogo de reportes."""

    template_name = "reports/catalog.html"

    def get_workspace_slugs(self):
        request = getattr(self, "request", None)
        if not request or not hasattr(request, "session") or not request.session:
            return []
        return list(request.session.get("reports_workspace", []))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = getattr(self.request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        catalog = build_catalog_for_user(self.request.user, empresa_id)

        context.update(
            {
                "page_title": _("Reports catalog"),
                "catalog": catalog,
                "can_operational": OperationalReportsPermission().has_permission(self.request, self),
                "can_managerial": ManagerialReportsPermission().has_permission(self.request, self),
                "workspace_api_url": reverse("reports-api:reports-workspace"),
                "workspace_view_url": reverse("reports:workspace"),
                "workspace_count": len(self.get_workspace_slugs()),
            }
        )
        return context


class DashboardDetailView(LoginRequiredMixin, TemplateView):
    """Detalle de un dashboard específico."""

    template_name = "reports/dashboard_detail.html"

    def get_report(self) -> ReportDefinition:
        slug = self.kwargs.get("slug")
        empresa = getattr(self.request.user, "empresa_activa", None)
        filters = Q(slug=slug, is_active=True)
        if empresa:
            filters &= Q(empresa__isnull=True) | Q(empresa=empresa)
        else:
            filters &= Q(empresa__isnull=True)
        report = ReportDefinition.objects.filter(filters).first()
        if not report:
            raise Http404("Report not found")
        if report.is_operational() and not OperationalReportsPermission().has_permission(self.request, self):
            raise Http404("Not authorized for operational reports")
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(self.request, self):
            raise Http404("Not authorized for managerial reports")
        return report

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_report()
        context.update(
            {
                "page_title": report.name,
                "report": report,
                "widgets": report.widgets.all(),
                "dashboard_api_url": reverse("reports-api:reports-query"),
                "workspace_api_url": reverse("reports-api:reports-workspace"),
            }
        )
        return context


class ReportsWorkspaceView(LoginRequiredMixin, TemplateView):
    """Dashboard en formato workspace con múltiples reportes guardados."""

    template_name = "reports/workspace.html"

    def get_workspace_slugs(self):
        request = getattr(self, "request", None)
        if not request or not hasattr(request, "session") or not request.session:
            return []
        return list(request.session.get("reports_workspace", []))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Workspace de reportes"),
                "dashboard_api_url": reverse("reports-api:reports-query"),
                "workspace_api_url": reverse("reports-api:reports-workspace"),
                "workspace_count": len(self.get_workspace_slugs()),
            }
        )
        return context


class SavedDashboardsView(LoginRequiredMixin, ListView):
    """Listado de dashboards guardados por el usuario."""

    model = ReportDashboard
    template_name = "reports/saved_dashboards.html"
    context_object_name = "dashboards"

    def get_queryset(self):
        empresa = getattr(self.request.user, "empresa_activa", None)
        qs = super().get_queryset().filter(owner=self.request.user)
        if empresa:
            qs = qs.filter(empresa=empresa)
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = _("Saved dashboards")
        context["categories"] = ReportCategory.choices
        return context


