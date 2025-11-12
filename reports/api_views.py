from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .domain import build_catalog_for_user
from .models import ReportDefinition, ReportWorkspace
from .permissions import OperationalReportsPermission, ManagerialReportsPermission
from .serializers import (
    CatalogEntrySerializer,
    ReportQueryRequestSerializer,
    ReportQueryResponseSerializer,
    KPIResponseSerializer,
)
from .services.query_runner import QueryRunnerService
from .services.export_service import ExportService


class ReportCatalogAPIView(APIView):
    """API del catálogo de reportes."""

    def get(self, request, *args, **kwargs):
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        catalog = build_catalog_for_user(request.user, empresa_id)
        serializer = CatalogEntrySerializer([CatalogEntrySerializer.from_catalog_entry(item) for item in catalog], many=True)
        return Response(serializer.data)


class ReportQueryAPIView(APIView):
    """API para ejecutar consultas de reportes."""

    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def post(self, request, *args, **kwargs):
        serializer = ReportQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        report = get_object_or_404(ReportDefinition, slug=payload["slug"], is_active=True)
        if report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)

        result = QueryRunnerService(request.user).run(report, payload)
        response_serializer = ReportQueryResponseSerializer(result.__dict__)
        return Response(response_serializer.data)


class WorkspaceSelectionAPIView(APIView):
    """Gestiona el workspace de dashboards seleccionados por el usuario."""

    permission_classes = [IsAuthenticated]

    MAX_ITEMS = 16

    def _get_workspace(self, request) -> ReportWorkspace:
        user = request.user
        empresa = getattr(user, "empresa_activa", None)
        workspace, _ = ReportWorkspace.objects.get_or_create(
            owner=user,
            empresa=empresa,
            defaults={"items": []},
        )
        return workspace

    def get(self, request, *args, **kwargs):
        workspace = self._get_workspace(request)
        slugs = list(workspace.items or [])

        if not slugs:
            return Response({"slots": [], "count": 0})

        reports = (
            ReportDefinition.objects.filter(slug__in=slugs, is_active=True)
            .prefetch_related("widgets")
        )
        report_map = {report.slug: report for report in reports}

        slots = []
        valid_slugs = []
        for slug in slugs:
            report = report_map.get(slug)
            if not report:
                continue
            widget = report.widgets.order_by("order", "id").first()
            if not widget:
                continue
            valid_slugs.append(slug)
            slots.append(
                {
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "widget": {
                        "id": widget.id,
                        "name": widget.name,
                        "widget_type": widget.widget_type,
                        "configuration": widget.configuration or {},
                    },
                }
            )

        if valid_slugs != slugs:
            workspace.items = valid_slugs
            workspace.save(update_fields=["items", "updated_at"])

        return Response({"slots": slots, "count": len(slots)})

    def post(self, request, *args, **kwargs):
        slug = request.data.get("slug")
        if not slug:
            return Response({"detail": "Slug requerido."}, status=status.HTTP_400_BAD_REQUEST)

        report = ReportDefinition.objects.filter(slug=slug, is_active=True).first()
        if not report:
            return Response({"detail": "Reporte no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        workspace = self._get_workspace(request)
        current = list(workspace.items or [])
        if slug in current:
            return Response({"status": "exists", "count": len(current)})

        if len(current) >= self.MAX_ITEMS:
            return Response(
                {
                    "detail": "Se alcanzó el máximo de elementos en el workspace.",
                    "count": len(current),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        current.append(slug)
        workspace.items = current
        workspace.save(update_fields=["items", "updated_at"])
        return Response({"status": "added", "count": len(current)})

    def delete(self, request, *args, **kwargs):
        slug = request.data.get("slug")
        if not slug:
            return Response({"detail": "Slug requerido."}, status=status.HTTP_400_BAD_REQUEST)

        workspace = self._get_workspace(request)
        current = list(workspace.items or [])
        if slug not in current:
            return Response({"status": "missing", "count": len(current)})

        current = [item for item in current if item != slug]
        workspace.items = current
        workspace.save(update_fields=["items", "updated_at"])
        return Response({"status": "removed", "count": len(current)})


class KPIAPIView(APIView):
    """API para KPIs puntuales."""

    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def get(self, request, *args, **kwargs):
        slug = request.query_params.get("slug")
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        if report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "kpi": slug,
            "value": 0,
            "unit": request.query_params.get("unit", ""),
            "breakdown": {},
        }
        serializer = KPIResponseSerializer(payload)
        return Response(serializer.data)


class ReportExportAPIView(APIView):
    """API para exportaciones PDF/XLSX."""

    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def post(self, request, *args, **kwargs):
        serializer = ReportQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        export_type = request.query_params.get("type", "xlsx")

        report = get_object_or_404(ReportDefinition, slug=payload["slug"], is_active=True)
        if report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)

        export_result = ExportService(request.user).export(report.slug, payload, export_type)
        return Response(
            {
                "path": export_result.path,
                "created_at": export_result.created_at,
                "expires_at": export_result.expires_at,
            },
            status=status.HTTP_202_ACCEPTED,
        )


