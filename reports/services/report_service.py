from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from ..models import Report, ReportComponent, ReportSchedule
from core.models import Empresa, Branch


class ReportService:
    """Servicio para gestión de reportes"""
    
    @staticmethod
    def create_report(user, data):
        """Crear un nuevo reporte"""
        with transaction.atomic():
            report = Report.objects.create(
                name=data['name'],
                description=data.get('description', ''),
                empresa=user.empresa_activa,
                branch=user.branch_activa,
                created_by=user,
                template_id=data['template_id'],
                layout_config=data.get('layout_config', {}),
                data_sources=data.get('data_sources', []),
                filters=data.get('filters', {}),
                branding=data.get('branding', {})
            )
            
            # Crear componentes si se proporcionan
            if 'components' in data:
                for comp_data in data['components']:
                    ReportComponent.objects.create(
                        report=report,
                        **comp_data
                    )
            
            return report
    
    @staticmethod
    def get_user_reports(user, filters=None):
        """Obtener reportes del usuario"""
        queryset = Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa
        )
        
        if filters:
            if filters.get('is_active') is not None:
                queryset = queryset.filter(is_active=filters['is_active'])
            if filters.get('template_id'):
                queryset = queryset.filter(template_id=filters['template_id'])
            if filters.get('search'):
                queryset = queryset.filter(name__icontains=filters['search'])
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def duplicate_report(user, report_id):
        """Duplicar un reporte"""
        original = Report.objects.get(id=report_id)
        
        # Verificar permisos
        if not user.has_perm('reports.crear'):
            raise PermissionDenied("No tienes permisos para crear reportes")
        
        with transaction.atomic():
            # Crear copia del reporte
            new_report = Report.objects.create(
                name=f"{original.name} (Copy)",
                description=original.description,
                empresa=user.empresa_activa,
                branch=user.branch_activa,
                created_by=user,
                template=original.template,
                layout_config=original.layout_config,
                data_sources=original.data_sources,
                filters=original.filters,
                branding=original.branding
            )
            
            # Copiar componentes
            for component in original.components.all():
                ReportComponent.objects.create(
                    report=new_report,
                    name=component.name,
                    component_type=component.component_type,
                    configuration=component.configuration,
                    data_source=component.data_source,
                    styling=component.styling,
                    position=component.position,
                    z_index=component.z_index
                )
            
            return new_report
    
    @staticmethod
    def update_report_layout(report_id, layout_config):
        """Actualizar configuración de layout de un reporte"""
        report = Report.objects.get(id=report_id)
        report.layout_config = layout_config
        report.save()
        return report
    
    @staticmethod
    def get_report_statistics(user):
        """Obtener estadísticas de reportes del usuario"""
        total_reports = Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa
        ).count()
        
        active_reports = Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa,
            is_active=True
        ).count()
        
        recent_reports = Report.objects.filter(
            empresa=user.empresa_activa,
            branch=user.branch_activa,
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        return {
            'total_reports': total_reports,
            'active_reports': active_reports,
            'recent_reports': recent_reports,
        } 