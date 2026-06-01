from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.urls import reverse
from django.shortcuts import redirect
# Función dummy para mantener compatibilidad - no se usa internacionalización
def _(s): return s
from django.views.generic import TemplateView

from core.utils.permissions import user_has_full_access
from .domain import build_catalog_for_user
from .models import ReportDefinition, ReportWorkspace
from .permissions import OperationalReportsPermission, ManagerialReportsPermission, BuilderReportsPermission

# Reportes con UI/dashboard propio (runner legacy por slug) que deben listarse también bajo «Declarativos»
# en el Builder, sin marcar config como declarative-v1 (evita que QueryRunner delegue al motor declarativo).
BUILDER_HYBRID_SLUGS = frozenset(
    {
        "ventas-objetivos-vs-bo",
        "ventas-por-vendedor",
        "ventas-por-articulo",
        "bo-stock-facturacion",
        "stock-existencias",
    }
)
class ReportsLoginRequiredMixin(LoginRequiredMixin):
    """
    Mixin personalizado para Reports que funciona con AdministraNETUser.
    Verifica sesión de administraNET en lugar de solo is_authenticated.
    """
    def dispatch(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 ReportsLoginRequiredMixin: Path={request.path}, User={getattr(request.user, 'cod_usuario', 'unknown')}")
        
        # Verificar sesión de administraNET primero
        if "user" not in request.session:
            logger.warning(f"❌ ReportsLoginRequiredMixin: No hay sesión de usuario, redirigiendo a login")
            return redirect("login:login")
        
        # Verificar is_authenticated (para compatibilidad con LoginRequiredMixin)
        is_authenticated = getattr(request.user, 'is_authenticated', False)
        logger.info(f"🔍 ReportsLoginRequiredMixin: is_authenticated={is_authenticated}, user_type={type(request.user).__name__}")
        
        if not is_authenticated:
            logger.warning(f"❌ ReportsLoginRequiredMixin: Usuario no autenticado, redirigiendo a login")
            return redirect("login:login")
        
        logger.info(f"✅ ReportsLoginRequiredMixin: Usuario autenticado, continuando...")
        return super().dispatch(request, *args, **kwargs)


def get_user_for_foreignkey(user):
    """
    Helper para obtener un usuario válido para ForeignKeys.
    Si es AdministraNETUser, retorna None (no se puede usar en ForeignKeys).
    Si es UsuarioExtendido, retorna el usuario directamente.
    """
    from core.models import UsuarioExtendido
    if isinstance(user, UsuarioExtendido):
        return user
    # Para AdministraNETUser, retornar None ya que no es un modelo de Django
    return None


def get_workspace_for_user(user, empresa):
    """
    Helper para obtener el workspace de un usuario.
    Maneja tanto UsuarioExtendido como AdministraNETUser.
    """
    from core.models import UsuarioExtendido
    
    # Para AdministraNETUser, no podemos usar ForeignKey directamente
    # Retornar None ya que no podemos guardar AdministraNETUser en ForeignKey
    # En el futuro se podría implementar almacenamiento en sesión o cache
    if not isinstance(user, UsuarioExtendido):
        return None
    
    # Para UsuarioExtendido, usar el ForeignKey normalmente
    workspace = ReportWorkspace.objects.filter(owner=user, empresa=empresa).first()
    return workspace


class ReportsCatalogView(ReportsLoginRequiredMixin, TemplateView):
    """Vista principal del catálogo de reportes."""

    template_name = "reports/catalog.html"

    def get_workspace_items(self):
        user = self.request.user
        empresa = getattr(user, "empresa_activa", None)
        workspace = get_workspace_for_user(user, empresa)
        if not workspace:
            return []
        return list(workspace.items or [])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = getattr(self.request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        catalog = build_catalog_for_user(self.request.user, empresa_id)

        is_supervisor_user = user_has_full_access(self.request.user)

        context.update(
            {
                "page_title": _("Reports catalog"),
                "catalog": catalog,
                "can_operational": OperationalReportsPermission().has_permission(self.request, self),
                "can_managerial": ManagerialReportsPermission().has_permission(self.request, self),
                "can_builder": BuilderReportsPermission().has_permission(self.request, self),
                "workspace_api_url": reverse("reports-api:reports-workspace"),
                "workspace_view_url": reverse("reports:workspace"),
                "workspace_count": len(self.get_workspace_items()),
                "is_supervisor_user": is_supervisor_user,
            }
        )
        return context


class DashboardDetailView(ReportsLoginRequiredMixin, TemplateView):
    """Detalle de un dashboard específico."""

    template_name = "reports/dashboard_detail.html"
    EXECUTIVE_SLUG = "resumen-ejecutivo-ventas"
    COMMAND_CENTER_SLUG = "command-center-gerencial"

    def get_template_names(self):
        slug = self.kwargs.get("slug")
        if slug == self.EXECUTIVE_SLUG:
            return ["reports/executive_summary.html"]
        if slug == self.COMMAND_CENTER_SLUG:
            return ["reports/command_center.html"]
        return [self.template_name]

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
        from reports.services.report_visibility import report_visible_for_user

        if not report_visible_for_user(report, self.request.user):
            raise Http404("Report not visible")
        return report

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_report()
        config = report.config or {}
        is_declarative = config.get("version") == "declarative-v1"
        context.update(
            {
                "page_title": report.name,
                "report": report,
                "widgets": report.widgets.all(),
                "dashboard_api_url": reverse("reports-api:reports-query"),
                "workspace_api_url": reverse("reports-api:reports-workspace"),
                "schema_api_url": reverse("reports-api:reports-schema", kwargs={"slug": report.slug}),
                "is_declarative": is_declarative,
                "can_builder": BuilderReportsPermission().has_permission(self.request, self),
                "report_config_for_script": config if isinstance(config, dict) else {},
            }
        )
        if report.slug == self.EXECUTIVE_SLUG:
            context["executive_summary_api_url"] = reverse("reports-api:reports-executive-summary")
            context["pv_canal_api_url"] = reverse("reports-api:reports-pv-canal-ejecutivo")
        if report.slug == self.COMMAND_CENTER_SLUG:
            from reports.services.executive_dashboard.base import mpr_modulo_activo

            mpr_active = mpr_modulo_activo()
            context["command_center_api_url"] = reverse("reports-api:reports-executive-dashboard")
            context["executive_summary_api_url"] = reverse("reports-api:reports-executive-summary")
            context["executive_sales_page_url"] = reverse(
                "reports:dashboard_detail", kwargs={"slug": self.EXECUTIVE_SLUG}
            )
            context["cash_flow_waterfall_url"] = reverse(
                "reports:dashboard_detail", kwargs={"slug": "cash_flow_waterfall"}
            )
            context["mpr_module_active"] = mpr_active
            context["mpr_tablero_url"] = reverse("mpr:tablero") if mpr_active else ""
            area_urls = {
                "ventas": reverse("reports-api:reports-executive-dashboard-ventas-resumen"),
                "inventario": reverse(
                    "reports-api:reports-executive-dashboard-inventario-resumen"
                ),
                "compras": reverse("reports-api:reports-executive-dashboard-compras-resumen"),
                "cruzados": reverse(
                    "reports-api:reports-executive-dashboard-cruzados-resumen"
                ),
                "tesoreria": reverse(
                    "reports-api:reports-executive-dashboard-tesoreria-resumen"
                ),
                "ventas_cobros": reverse(
                    "reports-api:reports-executive-dashboard-ventas-cobros-resumen"
                ),
            }
            if mpr_active:
                area_urls["manufactura"] = reverse(
                    "reports-api:reports-executive-dashboard-manufactura-resumen"
                )
            context["area_urls"] = area_urls
            context["detail_urls"] = {
                "pedidos_pendientes": reverse(
                    "reports-api:reports-executive-dashboard-ventas-pedidos-pendientes"
                ),
                "remitos_nf": reverse(
                    "reports-api:reports-executive-dashboard-ventas-remitos-nf"
                ),
                "backorder": reverse(
                    "reports-api:reports-executive-dashboard-cruzados-backorder"
                ),
                "existencias": reverse(
                    "reports-api:reports-executive-dashboard-inventario-existencias"
                ),
            }
        return context


class ReportsWorkspaceView(ReportsLoginRequiredMixin, TemplateView):
    """Dashboard en formato workspace con múltiples reportes guardados."""

    template_name = "reports/workspace.html"

    def get_workspace_items(self):
        user = self.request.user
        empresa = getattr(user, "empresa_activa", None)
        workspace = get_workspace_for_user(user, empresa)
        if not workspace:
            return []
        return list(workspace.items or [])

    def _is_mobile(self) -> bool:
        user_agent = (self.request.META.get("HTTP_USER_AGENT") or "").lower()
        mobile_tokens = ("iphone", "android", "ipad", "mobile", "opera mini", "mobile safari")
        return any(token in user_agent for token in mobile_tokens)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Workspace de reportes"),
                "dashboard_api_url": reverse("reports-api:reports-query"),
                "workspace_api_url": reverse("reports-api:reports-workspace"),
                "workspace_count": len(self.get_workspace_items()),
                "workspace_is_mobile": self._is_mobile(),
            }
        )
        return context


class ReportBuilderListView(ReportsLoginRequiredMixin, TemplateView):
    """Lista de reportes editables en el Builder."""

    template_name = "reports/builder_list.html"

    def dispatch(self, request, *args, **kwargs):
        # Verificar permiso de builder
        if not BuilderReportsPermission().has_permission(request, self):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("No tiene permiso para acceder al Report Builder.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = getattr(self.request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        
        # Obtener todos los reportes (declarativos y legacy)
        from django.db.models import Q
        filters = Q(is_active=True)
        if empresa_id:
            filters &= Q(empresa__isnull=True) | Q(empresa_id=empresa_id)
        else:
            filters &= Q(empresa__isnull=True)
        
        all_reports = ReportDefinition.objects.filter(filters).order_by("name")
        
        # Separar declarativos y legacy
        declarative_reports = [r for r in all_reports if r.config and r.config.get("version") == "declarative-v1"]
        legacy_reports = [r for r in all_reports if not (r.config and r.config.get("version") == "declarative-v1")]
        builder_hybrid_count = sum(1 for r in all_reports if r.slug in BUILDER_HYBRID_SLUGS)
        declarative_tab_count = len(declarative_reports) + builder_hybrid_count

        context.update(
            {
                "page_title": _("Report Builder"),
                "reports": all_reports,  # Todos los reportes para mostrar en la tabla
                "declarative_reports": declarative_reports,
                "legacy_reports": legacy_reports,
                "builder_hybrid_slugs": BUILDER_HYBRID_SLUGS,
                "declarative_tab_count": declarative_tab_count,
                "builder_api_url": reverse("reports-api:reports-builder-config", kwargs={"slug": "placeholder"}).replace("placeholder", ""),
                "builder_templates_api_url": reverse("reports-api:reports-builder-templates"),
            }
        )
        return context


class DataMapView(ReportsLoginRequiredMixin, TemplateView):
    """Vista del mapa visual de datos de la base de datos."""

    template_name = "reports/data_map.html"

    def dispatch(self, request, *args, **kwargs):
        # Verificar permiso de builder
        if not BuilderReportsPermission().has_permission(request, self):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("No tiene permiso para acceder al Mapa de Datos.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": _("Mapa de Datos"),
                "data_map_api_url": reverse("reports-api:reports-data-map"),
            }
        )
        return context


class ReportBuilderDetailView(ReportsLoginRequiredMixin, TemplateView):
    """Vista de edición de un reporte en el Builder."""

    template_name = "reports/builder_detail.html"

    def dispatch(self, request, *args, **kwargs):
        # Verificar permiso de builder
        if not BuilderReportsPermission().has_permission(request, self):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("No tiene permiso para acceder al Report Builder.")
        return super().dispatch(request, *args, **kwargs)

    def get_report(self) -> ReportDefinition:
        slug = self.kwargs.get("slug")
        
        # IMPORTANTE: Solo crear nuevo reporte si el slug es exactamente "new"
        # No confundir con slugs como "nuevo_reporte" que son reportes existentes
        if slug == "new":
            empresa = getattr(self.request.user, "empresa_activa", None)
            # Crear un nuevo reporte con valores por defecto
            report = ReportDefinition(
                name="Nuevo Reporte",
                slug="nuevo-reporte",  # Slug temporal, se actualizará cuando se guarde
                category="operational",
                config={
                    "version": "declarative-v1",
                    "metrics": [],
                    "dimensions": [],
                    "datasource": "",
                },
                refresh_interval="daily",
                is_active=True,
                empresa=empresa,
            )
            # No guardar aún, se guardará cuando el usuario guarde en el builder
            return report
        
        # Buscar reporte existente
        empresa = getattr(self.request.user, "empresa_activa", None)
        filters = Q(slug=slug, is_active=True)
        if empresa:
            filters &= Q(empresa__isnull=True) | Q(empresa=empresa)
        else:
            filters &= Q(empresa__isnull=True)
        
        report = ReportDefinition.objects.filter(filters).first()
        if not report:
            # Log para depuración
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Reporte no encontrado: slug='{slug}', empresa={empresa.id if empresa else None}")
            # Intentar búsqueda sin filtro de empresa para debug
            report_fallback = ReportDefinition.objects.filter(slug=slug, is_active=True).first()
            if report_fallback:
                logger.warning(f"Reporte encontrado sin filtro de empresa: slug='{slug}', empresa_db={report_fallback.empresa.id if report_fallback.empresa else None}")
            # Intentar buscar por slug alternativo (con guiones en lugar de guiones bajos o viceversa)
            # Esto ayuda cuando el slug cambió pero la URL sigue usando el antiguo
            slug_alt = slug.replace('_', '-') if '_' in slug else slug.replace('-', '_')
            if slug_alt != slug:
                report_alt = ReportDefinition.objects.filter(filters & Q(slug=slug_alt)).first()
                if report_alt:
                    logger.info(f"Reporte encontrado con slug alternativo: '{slug}' -> '{slug_alt}'")
                    # Redirigir al slug correcto sería ideal, pero por ahora retornamos el reporte
                    # para que la página funcione
                    return report_alt
            raise Http404(f"Report not found with slug: {slug}")
        return report

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get("slug")
        
        # IMPORTANTE: Determinar si es nuevo ANTES de llamar a get_report()
        # para evitar confusión con slugs como "nuevo_reporte"
        is_new = slug == "new"
        
        report = self.get_report()
        config = report.config or {}
        is_declarative = config.get("version") == "declarative-v1"
        
        # Para reportes nuevos, usar "new" como slug en las URLs de la API
        api_slug = "new" if is_new else report.slug
        
        context.update(
            {
                "page_title": f"Builder: {report.name}" if not is_new else "Builder: Nuevo Reporte",
                "report": report,
                "is_declarative": is_declarative,
                "is_new": is_new,
                "builder_config_api_url": reverse("reports-api:reports-builder-config", kwargs={"slug": api_slug}),
                "builder_preview_api_url": reverse("reports-api:reports-builder-preview", kwargs={"slug": api_slug}),
                "builder_widgets_api_url": reverse("reports-api:reports-builder-widgets", kwargs={"slug": api_slug}),
                "schema_api_url": reverse("reports-api:reports-schema", kwargs={"slug": api_slug}) if not is_new else None,
                "builder_datasources_api_url": reverse("reports-api:reports-builder-datasources"),
            }
        )
        return context


