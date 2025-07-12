from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from ..models import Tax, TaxGroup, TaxLine, FiscalPosition, JournalEntry, Journal, ChartOfAccounts, EntryStates
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
        tax__empresa=empresa,
        created_at__gte=thirty_days_ago
    )
    
    total_tax_amount_month = recent_tax_lines.aggregate(Sum('tax_amount'))['tax_amount__sum'] or 0
    total_base_amount_month = recent_tax_lines.aggregate(Sum('base_amount'))['base_amount__sum'] or 0
    total_tax_lines_month = recent_tax_lines.count()
    
    # Top grupos de impuestos por monto
    top_tax_groups = recent_tax_lines.values(
        'tax__tax_group__name'
    ).annotate(
        total_amount=Sum('tax_amount'),
        count=Count('id')
    ).order_by('-total_amount')[:5]
    
    # Top impuestos individuales
    top_taxes = recent_tax_lines.values(
        'tax__name', 'tax__tax_group__name'
    ).annotate(
        total_amount=Sum('tax_amount'),
        count=Count('id')
    ).order_by('-total_amount')[:5]
    
    # Últimas líneas de impuesto
    recent_tax_lines_list = recent_tax_lines.select_related(
        'tax', 'tax__tax_group'
    ).order_by('-created_at')[:10]
    
    # Estadísticas por tipo de impuesto
    tax_types_stats = recent_tax_lines.values(
        'tax__amount_type'
    ).annotate(
        total_amount=Sum('tax_amount'),
        count=Count('id')
    ).order_by('-total_amount')
    
    # Estadísticas de asientos contables
    total_entries = JournalEntry.objects.filter(empresa=empresa).count()
    draft_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.DRAFT).count()
    posted_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.POSTED).count()
    total_journals = Journal.objects.filter(empresa=empresa, is_active=True).count()
    total_accounts = ChartOfAccounts.objects.filter(empresa=empresa, is_active=True).count()
    
    # Asientos recientes
    recent_entries = JournalEntry.objects.filter(
        empresa=empresa
    ).select_related('journal', 'created_by').order_by('-created_at')[:5]
    
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
        # Estadísticas de asientos contables
        'total_entries': total_entries,
        'draft_entries': draft_entries,
        'posted_entries': posted_entries,
        'total_journals': total_journals,
        'total_accounts': total_accounts,
        'recent_entries': recent_entries,
    }
    
    return render(request, 'accounting/dashboard.html', context) 