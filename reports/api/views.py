from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from ..models import Report, ReportTemplate, ReportComponent, ReportSchedule
from ..services.report_service import ReportService
from ..services.export_service import ExportService
from .serializers import (
    ReportSerializer, ReportCreateSerializer, ReportUpdateSerializer, ReportListSerializer,
    ReportTemplateSerializer, ReportComponentSerializer, ReportScheduleSerializer,
    ReportPreviewSerializer, ReportExportSerializer, ReportsDashboardSerializer
)
from core.pagination import StandardResultsSetPagination


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de reportes"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_public', 'template__category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        """Filtrar por empresa y sucursal del usuario"""
        user = self.request.user
        return Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa
        )
    
    def get_serializer_class(self):
        """Retornar serializador apropiado según la acción"""
        if self.action == 'create':
            return ReportCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ReportUpdateSerializer
        elif self.action == 'list':
            return ReportListSerializer
        return ReportSerializer
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicar un reporte"""
        report = self.get_object()
        try:
            new_report = ReportService.duplicate_report(request.user, report.id)
            serializer = self.get_serializer(new_report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Vista previa del reporte"""
        report = self.get_object()
        format_type = request.query_params.get('format', 'html')
        
        try:
            preview_data = ExportService.generate_preview(report, format_type)
            return Response(preview_data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """Exportar reporte a PDF"""
        report = self.get_object()
        try:
            pdf_data = ExportService.export_to_pdf(report)
            response = Response(pdf_data, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{report.name}.pdf"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def export_pptx(self, request, pk=None):
        """Exportar reporte a PPTX"""
        report = self.get_object()
        try:
            pptx_data = ExportService.export_to_pptx(report)
            response = Response(pptx_data, content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation')
            response['Content-Disposition'] = f'attachment; filename="{report.name}.pptx"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ReportTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de templates de reportes"""
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_system']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def get_queryset(self):
        """Filtrar templates por categoría si se especifica"""
        queryset = ReportTemplate.objects.all()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class ReportComponentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para componentes de reportes (solo lectura)"""
    serializer_class = ReportComponentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar por reporte específico"""
        report_id = self.request.query_params.get('report_id')
        if report_id:
            return ReportComponent.objects.filter(report_id=report_id)
        return ReportComponent.objects.none()


class ReportScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de programación de reportes"""
    serializer_class = ReportScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['frequency', 'is_active', 'export_format']
    search_fields = ['name', 'report__name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrar por empresa y sucursal del usuario"""
        user = self.request.user
        return ReportSchedule.objects.filter(
            report__empresa=user.empresa_activa,
            report__branch=user.branch_activa
        )


class ReportsDashboardView(viewsets.ViewSet):
    """Vista para dashboard de reportes"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Obtener datos del dashboard"""
        user = request.user
        
        # Estadísticas básicas
        total_reports = Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa
        ).count()
        
        active_reports = Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa,
            is_active=True
        ).count()
        
        # Reportes recientes
        recent_reports = Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa
        ).order_by('-created_at')[:5]
        
        # Templates populares
        popular_templates = ReportTemplate.objects.filter(
            report__empresa=user.empresa_activa,
            report__branch=user.branch_activa
        ).annotate(
            usage_count=Count('report')
        ).order_by('-usage_count')[:5]
        
        # Reportes programados
        scheduled_reports = ReportSchedule.objects.filter(
            report__empresa=user.empresa_activa,
            report__branch=user.branch_activa,
            is_active=True
        ).count()
        
        data = {
            'total_reports': total_reports,
            'active_reports': active_reports,
            'recent_reports': ReportListSerializer(recent_reports, many=True).data,
            'popular_templates': ReportTemplateSerializer(popular_templates, many=True).data,
            'scheduled_reports': scheduled_reports,
        }
        
        serializer = ReportsDashboardSerializer(data)
        return Response(serializer.data) 