from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .domain import build_catalog_for_user
from .models import ReportDefinition, ReportDashboard
from .permissions import OperationalReportsPermission, ManagerialReportsPermission
from .serializers import (
    CatalogEntrySerializer,
    ReportQueryRequestSerializer,
    ReportQueryResponseSerializer,
    KPIResponseSerializer,
    ReportDashboardSerializer,
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


class SavedDashboardViewSet(viewsets.ModelViewSet):
    """CRUD de dashboards guardados."""

    serializer_class = ReportDashboardSerializer

    def get_queryset(self):
        user = self.request.user
        empresa = getattr(user, "empresa_activa", None)
        qs = ReportDashboard.objects.filter(owner=user)
        if empresa:
            qs = qs.filter(empresa=empresa)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        empresa = getattr(user, "empresa_activa", None)
        serializer.save(owner=user, empresa=empresa)


