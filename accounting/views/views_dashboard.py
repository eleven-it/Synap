from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from ..models import Tax, TaxGroup, TaxLine, FiscalPosition, JournalEntry
from core.decorators import tiene_permiso


@login_required
@tiene_permiso('accounting.view_tax')
def accounting_dashboard(request):
    """Dashboard principal de contabilidad e impuestos"""
    
    empresa = request.user.empresa_activa
    
    # Estadísticas generales
    total_taxes = Tax.objects.filter(empresa=empresa).count()
    active_taxes = Tax.objects.filter(empresa=empresa, is_active=True).count()
    total_tax_groups = TaxGroup.objects.filter(empresa=empresa).count()
    active_tax_groups = TaxGroup.objects.filter(empresa=empresa, is_active=True).count()
    total_fiscal_positions = FiscalPosition.objects.filter(empresa=empresa).count()
    active_fiscal_positions = FiscalPosition.objects.filter(empresa=empresa, is_active=True).count()
    
    # Estadísticas de uso (últimos 30 días)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_tax_lines = TaxLine.objects.filter(
        empresa=empresa,
        created_at__gte=thirty_days_ago
    )
    
    total_tax_amount_month = recent_tax_lines.aggregate(Sum('amount'))['amount__sum'] or 0
    total_base_amount_month = recent_tax_lines.aggregate(Sum('base'))['base__sum'] or 0
    total_tax_lines_month = recent_tax_lines.count()
    
    # Top grupos de impuestos por monto
    top_tax_groups = recent_tax_lines.values(
        'tax_id__tax_group__name'
    ).annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')[:5]
    
    # Top impuestos individuales
    top_taxes = recent_tax_lines.values(
        'tax_id__name', 'tax_id__tax_group__name'
    ).annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')[:5]
    
    # Últimas líneas de impuesto
    recent_tax_lines_list = recent_tax_lines.select_related(
        'tax_id', 'tax_id__tax_group'
    ).order_by('-created_at')[:10]
    
    # Estadísticas por tipo de impuesto
    tax_types_stats = recent_tax_lines.values(
        'tax_id__amount_type'
    ).annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')
    
    context = {
        'total_taxes': total_taxes,
        'active_taxes': active_taxes,
        'total_tax_groups': total_tax_groups,
        'active_tax_groups': active_tax_groups,
        'total_fiscal_positions': total_fiscal_positions,
        'active_fiscal_positions': active_fiscal_positions,
        'total_tax_amount_month': total_tax_amount_month,
        'total_base_amount_month': total_base_amount_month,
        'total_tax_lines_month': total_tax_lines_month,
        'top_tax_groups': top_tax_groups,
        'top_taxes': top_taxes,
        'recent_tax_lines': recent_tax_lines_list,
        'tax_types_stats': tax_types_stats,
        'period_days': 30,
    }
    
    return render(request, 'accounting/dashboard.html', context) 