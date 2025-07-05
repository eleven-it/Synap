from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

from ..models import Tax, TaxGroup, TaxLine, FiscalPosition, JournalEntry, JournalEntryLine
from core.decorators import tiene_permiso


class TaxReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Reporte de impuestos con filtros y gráficos"""
    template_name = 'accounting/reports/tax_report.html'
    permission_required = 'accounting.view_tax'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtros de fecha
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        tax_group = self.request.GET.get('tax_group', '')
        
        # Filtrar líneas de impuesto por empresa
        queryset = TaxLine.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('tax_id', 'tax_id__tax_group')
        
        # Aplicar filtros
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        if tax_group:
            queryset = queryset.filter(tax_id__tax_group_id=tax_group)
        
        # Estadísticas generales
        total_tax_amount = queryset.aggregate(Sum('amount'))['amount__sum'] or 0
        total_base_amount = queryset.aggregate(Sum('base'))['base__sum'] or 0
        total_tax_lines = queryset.count()
        
        # Agrupación por grupo de impuestos
        tax_groups_summary = queryset.values(
            'tax_id__tax_group__name'
        ).annotate(
            total_amount=Sum('amount'),
            total_base=Sum('base'),
            count=Count('id')
        ).order_by('-total_amount')
        
        # Agrupación por impuesto individual
        taxes_summary = queryset.values(
            'tax_id__name', 'tax_id__tax_group__name'
        ).annotate(
            total_amount=Sum('amount'),
            total_base=Sum('base'),
            count=Count('id')
        ).order_by('-total_amount')
        
        # Datos para gráficos
        chart_data = {
            'labels': [item['tax_id__tax_group__name'] for item in tax_groups_summary],
            'data': [float(item['total_amount']) for item in tax_groups_summary],
        }
        
        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'tax_group_filter': tax_group,
            'total_tax_amount': total_tax_amount,
            'total_base_amount': total_base_amount,
            'total_tax_lines': total_tax_lines,
            'tax_groups_summary': tax_groups_summary,
            'taxes_summary': taxes_summary,
            'chart_data': json.dumps(chart_data),
            'tax_groups': TaxGroup.objects.filter(
                empresa=self.request.user.empresa_activa,
                is_active=True
            ).order_by('name'),
        })
        return context


class FiscalPositionReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Reporte de posiciones fiscales"""
    template_name = 'accounting/reports/fiscal_position_report.html'
    permission_required = 'accounting.view_fiscalposition'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener posiciones fiscales de la empresa
        fiscal_positions = FiscalPosition.objects.filter(
            empresa=self.request.user.empresa_activa
        ).prefetch_related('tax_mappings')
        
        # Estadísticas de uso (simulado - en producción se conectaría con ventas)
        fiscal_position_stats = []
        for fp in fiscal_positions:
            # Aquí se conectaría con el modelo de ventas para obtener estadísticas reales
            fiscal_position_stats.append({
                'fiscal_position': fp,
                'usage_count': 0,  # Placeholder
                'total_amount': 0,  # Placeholder
            })
        
        context.update({
            'fiscal_positions': fiscal_positions,
            'fiscal_position_stats': fiscal_position_stats,
        })
        return context


class TaxCalculationReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Reporte de cálculo de impuestos"""
    template_name = 'accounting/reports/tax_calculation_report.html'
    permission_required = 'accounting.view_tax'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtros
        tax_id = self.request.GET.get('tax_id', '')
        start_date = self.request.GET.get('start_date', '')
        end_date = self.request.GET.get('end_date', '')
        
        # Filtrar líneas de impuesto
        queryset = TaxLine.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('tax_id', 'tax_id__tax_group')
        
        if tax_id:
            queryset = queryset.filter(tax_id_id=tax_id)
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Análisis de cálculo
        calculation_analysis = queryset.values(
            'tax_id__name', 'tax_id__amount_type'
        ).annotate(
            total_amount=Sum('amount'),
            total_base=Sum('base'),
            avg_rate=Sum('amount') / Sum('base') * 100 if Sum('base') else 0,
            count=Count('id')
        ).order_by('-total_amount')
        
        # Detalles de líneas
        tax_lines = queryset.order_by('-created_at')[:100]  # Últimas 100 líneas
        
        context.update({
            'tax_id_filter': tax_id,
            'start_date': start_date,
            'end_date': end_date,
            'calculation_analysis': calculation_analysis,
            'tax_lines': tax_lines,
            'taxes': Tax.objects.filter(
                empresa=self.request.user.empresa_activa,
                is_active=True
            ).order_by('tax_group__name', 'name'),
        })
        return context


@tiene_permiso('accounting.view_tax')
def export_tax_report(request):
    """Exportar reporte de impuestos a CSV/Excel"""
    from django.http import HttpResponse
    import csv
    
    # Filtros
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    tax_group = request.GET.get('tax_group', '')
    
    # Filtrar datos
    queryset = TaxLine.objects.filter(
        empresa=request.user.empresa_activa
    ).select_related('tax_id', 'tax_id__tax_group')
    
    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)
    if tax_group:
        queryset = queryset.filter(tax_id__tax_group_id=tax_group)
    
    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tax_report_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        _('Date'), _('Tax Group'), _('Tax'), _('Base Amount'), 
        _('Tax Amount'), _('Rate'), _('Description')
    ])
    
    for tax_line in queryset:
        writer.writerow([
            tax_line.created_at.strftime('%Y-%m-%d'),
            tax_line.tax_id.tax_group.name if tax_line.tax_id.tax_group else '',
            tax_line.tax_id.name,
            tax_line.base,
            tax_line.amount,
            tax_line.tax_id.amount,
            tax_line.description or ''
        ])
    
    return response


@tiene_permiso('accounting.view_tax')
def tax_report_data_api(request):
    """API para datos del reporte de impuestos (AJAX)"""
    # Filtros
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    tax_group = request.GET.get('tax_group', '')
    
    # Filtrar datos
    queryset = TaxLine.objects.filter(
        empresa=request.user.empresa_activa
    ).select_related('tax_id', 'tax_id__tax_group')
    
    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)
    if tax_group:
        queryset = queryset.filter(tax_id__tax_group_id=tax_group)
    
    # Agrupación por mes
    monthly_data = queryset.extra(
        select={'month': "DATE_TRUNC('month', created_at)"}
    ).values('month').annotate(
        total_amount=Sum('amount'),
        total_base=Sum('base'),
        count=Count('id')
    ).order_by('month')
    
    # Datos para gráficos
    chart_data = {
        'labels': [item['month'].strftime('%B %Y') for item in monthly_data],
        'amounts': [float(item['total_amount']) for item in monthly_data],
        'bases': [float(item['total_base']) for item in monthly_data],
    }
    
    return JsonResponse({
        'success': True,
        'data': chart_data,
        'summary': {
            'total_amount': float(queryset.aggregate(Sum('amount'))['amount__sum'] or 0),
            'total_base': float(queryset.aggregate(Sum('base'))['base__sum'] or 0),
            'total_count': queryset.count(),
        }
    }) 