from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Sum, Count, F, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
from django.core.paginator import Paginator

from ..models import (
    JournalEntry, JournalEntryLine, Journal, ChartOfAccounts, 
    Tax, TaxGroup, TaxLine, FiscalPosition, EntryStates, AccountTypes
)
from core.decorators import tiene_permiso
from core.utils import get_user_empresa


@login_required
@tiene_permiso('accounting.view_journalentry')
def reports_dashboard(request):
    """Dashboard principal de reportes contables"""
    empresa = request.user.empresa_activa
    
    # Filtros de fecha
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    
    # Convertir a objetos date
    try:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
    
    # Estadísticas generales
    total_entries = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[start_date, end_date]
    ).count()
    
    posted_entries = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[start_date, end_date],
        state=EntryStates.POSTED
    ).count()
    
    # Totales de débito y crédito
    entry_lines = JournalEntryLine.objects.filter(
        entry__empresa=empresa,
        entry__date__range=[start_date, end_date],
        entry__state=EntryStates.POSTED
    )
    
    total_debit = entry_lines.aggregate(total=Sum('debit'))['total'] or 0
    total_credit = entry_lines.aggregate(total=Sum('credit'))['total'] or 0
    
    # Asientos por diario
    entries_by_journal = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[start_date, end_date],
        state=EntryStates.POSTED
    ).values('journal__name').annotate(
        count=Count('id'),
        total_debit=Sum('lines__debit'),
        total_credit=Sum('lines__credit')
    ).order_by('-count')
    
    # Top cuentas más utilizadas
    top_accounts = entry_lines.values(
        'account__code', 'account__name', 'account__account_type'
    ).annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
        movement_count=Count('id')
    ).order_by('-movement_count')[:10]
    
    # Balance por tipo de cuenta
    balance_by_type = entry_lines.values('account__account_type').annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit')
    ).order_by('account__account_type')
    
    # Calcular balance neto por tipo
    for balance in balance_by_type:
        account_type = balance['account__account_type']
        if account_type in [AccountTypes.ASSETS, AccountTypes.EXPENSES]:
            balance['net_balance'] = balance['total_debit'] - balance['total_credit']
        else:
            balance['net_balance'] = balance['total_credit'] - balance['total_debit']
    
    # Estadísticas de impuestos (si existen)
    tax_stats = {}
    try:
        total_taxes = Tax.objects.filter(empresa=empresa, is_active=True).count()
        total_tax_groups = TaxGroup.objects.filter(empresa=empresa, is_active=True).count()
        total_fiscal_positions = FiscalPosition.objects.filter(empresa=empresa, is_active=True).count()
        
        # Líneas de impuesto en el período
        tax_lines = TaxLine.objects.filter(
            tax__empresa=empresa,
            created_at__date__range=[start_date, end_date]
        )
        
        total_tax_amount = tax_lines.aggregate(total=Sum('tax_amount'))['total'] or 0
        total_base_amount = tax_lines.aggregate(total=Sum('base_amount'))['total'] or 0
        
        tax_stats = {
            'total_taxes': total_taxes,
            'total_tax_groups': total_tax_groups,
            'total_fiscal_positions': total_fiscal_positions,
            'total_tax_amount': total_tax_amount,
            'total_base_amount': total_base_amount,
        }
    except:
        pass
    
    # --- KPIs AVANZADOS ---
    # Período anterior para comparativas
    period_days = (end_date - start_date).days
    previous_start = start_date - timedelta(days=period_days)
    previous_end = start_date - timedelta(days=1)
    
    # Comparativas con período anterior
    previous_entries = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[previous_start, previous_end]
    ).count()
    
    previous_posted = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[previous_start, previous_end],
        state=EntryStates.POSTED
    ).count()
    
    previous_debit = JournalEntryLine.objects.filter(
        entry__empresa=empresa,
        entry__date__range=[previous_start, previous_end],
        entry__state=EntryStates.POSTED
    ).aggregate(total=Sum('debit'))['total'] or 0
    
    previous_credit = JournalEntryLine.objects.filter(
        entry__empresa=empresa,
        entry__date__range=[previous_start, previous_end],
        entry__state=EntryStates.POSTED
    ).aggregate(total=Sum('credit'))['total'] or 0
    
    # Cálculo de cambios porcentuales
    entries_change = ((total_entries - previous_entries) / previous_entries * 100) if previous_entries > 0 else 0
    posted_change = ((posted_entries - previous_posted) / previous_posted * 100) if previous_posted > 0 else 0
    debit_change = ((total_debit - previous_debit) / previous_debit * 100) if previous_debit > 0 else 0
    credit_change = ((total_credit - previous_credit) / previous_credit * 100) if previous_credit > 0 else 0
    
    # Ratios financieros
    balance_ratio = (total_credit / total_debit * 100) if total_debit > 0 else 0
    posting_efficiency = (posted_entries / total_entries * 100) if total_entries > 0 else 0
    
    # Alertas y métricas de rendimiento
    alerts = []
    if posting_efficiency < 80:
        alerts.append({
            'type': 'warning',
            'message': f'Baja eficiencia de publicación: {posting_efficiency:.1f}%',
            'icon': 'exclamation-triangle'
        })
    
    if abs(total_debit - total_credit) > 1000:
        alerts.append({
            'type': 'error',
            'message': f'Desbalance significativo: ${abs(total_debit - total_credit):.2f}',
            'icon': 'x-circle'
        })
    
    if entries_change < -20:
        alerts.append({
            'type': 'info',
            'message': f'Reducción de asientos: {entries_change:.1f}% vs período anterior',
            'icon': 'information-circle'
        })
    
    # Métricas de rendimiento
    performance_metrics = {
        'avg_entries_per_day': total_entries / period_days if period_days > 0 else 0,
        'avg_amount_per_entry': (total_debit + total_credit) / total_entries if total_entries > 0 else 0,
        'balance_accuracy': 100 - (abs(total_debit - total_credit) / max(total_debit, total_credit) * 100) if max(total_debit, total_credit) > 0 else 100,
    }
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'start_date': start_date,
        'end_date': end_date,
        'total_entries': total_entries,
        'posted_entries': posted_entries,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'entries_by_journal': entries_by_journal,
        'top_accounts': top_accounts,
        'balance_by_type': balance_by_type,
        'tax_stats': tax_stats,
        # KPIs avanzados
        'entries_change': entries_change,
        'posted_change': posted_change,
        'debit_change': debit_change,
        'credit_change': credit_change,
        'balance_ratio': balance_ratio,
        'posting_efficiency': posting_efficiency,
        'alerts': alerts,
        'performance_metrics': performance_metrics,
        'period_days': period_days,
    }
    
    # Al final de reports_dashboard
    # --- Datos para gráficos ---
    # 1. Balance por tipo de cuenta
    chart_balance_labels = [b['account__account_type'].title() for b in balance_by_type]
    chart_balance_data = [float(b['net_balance']) for b in balance_by_type]

    # 2. Tendencia de asientos por mes
    from django.db.models.functions import TruncMonth
    entries_by_month = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[start_date, end_date],
        state=EntryStates.POSTED
    ).annotate(month=TruncMonth('date')).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    chart_month_labels = [e['month'].strftime('%b %Y') for e in entries_by_month]
    chart_month_data = [e['count'] for e in entries_by_month]

    # 3. Distribución de impuestos por grupo
    tax_group_summary = []
    if tax_stats and tax_stats.get('total_taxes', 0) > 0:
        tax_lines = TaxLine.objects.filter(
            tax__empresa=empresa,
            created_at__date__range=[start_date, end_date]
        )
        summary = tax_lines.values('tax__tax_group__name').annotate(
            total=Sum('tax_amount')
        ).order_by('-total')
        tax_group_summary = list(summary)
    chart_tax_labels = [g['tax__tax_group__name'] for g in tax_group_summary]
    chart_tax_data = [float(g['total']) for g in tax_group_summary]

    context.update({
        'chart_balance_labels': json.dumps(chart_balance_labels),
        'chart_balance_data': json.dumps(chart_balance_data),
        'chart_month_labels': json.dumps(chart_month_labels),
        'chart_month_data': json.dumps(chart_month_data),
        'chart_tax_labels': json.dumps(chart_tax_labels),
        'chart_tax_data': json.dumps(chart_tax_data),
    })
    
    return render(request, 'accounting/reports/reports_dashboard.html', context)


@login_required
@tiene_permiso('accounting.view_chartofaccounts')
def account_balance_report(request):
    """Reporte de balance de cuentas"""
    empresa = request.user.empresa_activa
    
    # Filtros
    account_type = request.GET.get('account_type', '')
    search = request.GET.get('search', '')
    date_as_of = request.GET.get('date_as_of', timezone.now().date().strftime('%Y-%m-%d'))
    
    try:
        as_of_date = datetime.strptime(date_as_of, '%Y-%m-%d').date()
    except ValueError:
        as_of_date = timezone.now().date()
    
    # Obtener cuentas
    accounts = ChartOfAccounts.objects.filter(empresa=empresa, is_active=True)
    
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    
    if search:
        accounts = accounts.filter(
            Q(code__icontains=search) | Q(name__icontains=search)
        )
    
    # Calcular balances
    account_balances = []
    for account in accounts:
        # Obtener movimientos hasta la fecha especificada
        debit_movements = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED,
            entry__date__lte=as_of_date,
            account=account
        ).aggregate(total=Sum('debit'))['total'] or 0
        
        credit_movements = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED,
            entry__date__lte=as_of_date,
            account=account
        ).aggregate(total=Sum('credit'))['total'] or 0
        
        # Calcular balance según tipo de cuenta
        if account.account_type in [AccountTypes.ASSETS, AccountTypes.EXPENSES]:
            balance = debit_movements - credit_movements
        else:
            balance = credit_movements - debit_movements
        
        # Movimientos del período (últimos 30 días)
        period_start = as_of_date - timedelta(days=30)
        period_debit = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED,
            entry__date__range=[period_start, as_of_date],
            account=account
        ).aggregate(total=Sum('debit'))['total'] or 0
        
        period_credit = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED,
            entry__date__range=[period_start, as_of_date],
            account=account
        ).aggregate(total=Sum('credit'))['total'] or 0
        
        account_balances.append({
            'account': account,
            'balance': balance,
            'debit_movements': debit_movements,
            'credit_movements': credit_movements,
            'period_debit': period_debit,
            'period_credit': period_credit,
            'period_net': period_debit - period_credit if account.account_type in [AccountTypes.ASSETS, AccountTypes.EXPENSES] else period_credit - period_debit,
        })
    
    # Ordenar por balance
    account_balances.sort(key=lambda x: abs(x['balance']), reverse=True)
    
    # Totales por tipo de cuenta
    totals_by_type = {}
    for balance in account_balances:
        account_type = balance['account'].account_type
        if account_type not in totals_by_type:
            totals_by_type[account_type] = {
                'total_balance': 0,
                'total_debit': 0,
                'total_credit': 0,
                'count': 0
            }
        
        totals_by_type[account_type]['total_balance'] += balance['balance']
        totals_by_type[account_type]['total_debit'] += balance['debit_movements']
        totals_by_type[account_type]['total_credit'] += balance['credit_movements']
        totals_by_type[account_type]['count'] += 1
    
    context = {
        'account_balances': account_balances,
        'totals_by_type': totals_by_type,
        'account_type_filter': account_type,
        'search_filter': search,
        'date_as_of': date_as_of,
        'as_of_date': as_of_date,
        'account_types': AccountTypes.CHOICES,
    }
    
    # --- Datos para gráficos ---
    # 1. Distribución de balances por tipo de cuenta
    chart_type_labels = [t.title() for t in totals_by_type.keys()]
    chart_type_balances = [float(t['total_balance']) for t in totals_by_type.values()]
    chart_type_counts = [t['count'] for t in totals_by_type.values()]
    
    # 2. Top 10 cuentas con mayor balance
    top_accounts = sorted(account_balances, key=lambda x: abs(x['balance']), reverse=True)[:10]
    chart_account_labels = [f"{acc['account'].code} - {acc['account'].name[:20]}..." for acc in top_accounts]
    chart_account_balances = [float(acc['balance']) for acc in top_accounts]
    
    context.update({
        'chart_type_labels': json.dumps(chart_type_labels),
        'chart_type_balances': json.dumps(chart_type_balances),
        'chart_type_counts': json.dumps(chart_type_counts),
        'chart_account_labels': json.dumps(chart_account_labels),
        'chart_account_balances': json.dumps(chart_account_balances),
    })
    
    return render(request, 'accounting/reports/account_balance_report.html', context)


@login_required
@tiene_permiso('accounting.view_tax')
def tax_summary_report(request):
    """Reporte de resumen de impuestos"""
    empresa = request.user.empresa_activa
    
    # Filtros
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    tax_group_id = request.GET.get('tax_group', '')
    
    try:
        start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
        end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
    
    # Obtener líneas de impuesto
    tax_lines = TaxLine.objects.filter(
        tax__empresa=empresa,
        created_at__date__range=[start_date, end_date]
    )
    
    if tax_group_id:
        tax_lines = tax_lines.filter(tax__tax_group_id=tax_group_id)
    
    # Resumen por grupo de impuestos
    summary_by_group = tax_lines.values(
        'tax__tax_group__name', 'tax__tax_group__code'
    ).annotate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        total_amount=Sum('total_amount'),
        line_count=Count('id')
    ).order_by('-total_tax')
    
    # Resumen por impuesto individual
    summary_by_tax = tax_lines.values(
        'tax__name', 'tax__code', 'tax__tax_group__name', 'tax__amount', 'tax__amount_type'
    ).annotate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        total_amount=Sum('total_amount'),
        line_count=Count('id')
    ).order_by('-total_tax')
    
    # Resumen por tipo de impuesto
    summary_by_type = tax_lines.values('tax__amount_type').annotate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        total_amount=Sum('total_amount'),
        line_count=Count('id')
    ).order_by('-total_tax')
    
    # Totales generales
    total_base = tax_lines.aggregate(total=Sum('base_amount'))['total'] or 0
    total_tax = tax_lines.aggregate(total=Sum('tax_amount'))['total'] or 0
    total_amount = tax_lines.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Grupos de impuestos disponibles para filtro
    tax_groups = TaxGroup.objects.filter(empresa=empresa, is_active=True).order_by('name')
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'start_date': start_date,
        'end_date': end_date,
        'tax_group_filter': tax_group_id,
        'summary_by_group': summary_by_group,
        'summary_by_tax': summary_by_tax,
        'summary_by_type': summary_by_type,
        'total_base': total_base,
        'total_tax': total_tax,
        'total_amount': total_amount,
        'tax_groups': tax_groups,
    }
    
    # --- Datos para gráficos ---
    # 1. Distribución de impuestos por grupo
    chart_group_labels = [g['tax__tax_group__name'] for g in summary_by_group]
    chart_group_tax = [float(g['total_tax']) for g in summary_by_group]
    chart_group_base = [float(g['total_base']) for g in summary_by_group]
    
    # 2. Top impuestos individuales
    chart_tax_labels = [t['tax__name'] for t in summary_by_tax[:8]]
    chart_tax_amounts = [float(t['total_tax']) for t in summary_by_tax[:8]]
    
    # 3. Comparación base vs impuesto
    chart_comparison_labels = ['Base Amount', 'Tax Amount']
    chart_comparison_data = [float(total_base), float(total_tax)]
    
    context.update({
        'chart_group_labels': json.dumps(chart_group_labels),
        'chart_group_tax': json.dumps(chart_group_tax),
        'chart_group_base': json.dumps(chart_group_base),
        'chart_tax_labels': json.dumps(chart_tax_labels),
        'chart_tax_amounts': json.dumps(chart_tax_amounts),
        'chart_comparison_labels': json.dumps(chart_comparison_labels),
        'chart_comparison_data': json.dumps(chart_comparison_data),
    })
    
    return render(request, 'accounting/reports/tax_summary_report.html', context)


@login_required
@tiene_permiso('accounting.view_journalentry')
def financial_statements(request):
    """Estados financieros básicos"""
    empresa = request.user.empresa_activa
    
    # Fecha de corte
    date_as_of = request.GET.get('date_as_of', timezone.now().date().strftime('%Y-%m-%d'))
    
    try:
        as_of_date = datetime.strptime(date_as_of, '%Y-%m-%d').date()
    except ValueError:
        as_of_date = timezone.now().date()
    
    # Función para calcular balance de cuenta
    def get_account_balance(account, date):
        debit = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED,
            entry__date__lte=date,
            account=account
        ).aggregate(total=Sum('debit'))['total'] or 0
        
        credit = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED,
            entry__date__lte=date,
            account=account
        ).aggregate(total=Sum('credit'))['total'] or 0
        
        if account.account_type in [AccountTypes.ASSETS, AccountTypes.EXPENSES]:
            return debit - credit
        else:
            return credit - debit
    
    # BALANCE GENERAL
    # Activos
    assets_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.ASSETS,
        is_active=True
    ).order_by('code')
    
    assets_total = 0
    assets_details = []
    for account in assets_accounts:
        balance = get_account_balance(account, as_of_date)
        if balance != 0:
            assets_details.append({
                'account': account,
                'balance': balance
            })
            assets_total += balance
    
    # Pasivos
    liabilities_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.LIABILITIES,
        is_active=True
    ).order_by('code')
    
    liabilities_total = 0
    liabilities_details = []
    for account in liabilities_accounts:
        balance = get_account_balance(account, as_of_date)
        if balance != 0:
            liabilities_details.append({
                'account': account,
                'balance': balance
            })
            liabilities_total += balance
    
    # Patrimonio Neto
    equity_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.EQUITY,
        is_active=True
    ).order_by('code')
    
    equity_total = 0
    equity_details = []
    for account in equity_accounts:
        balance = get_account_balance(account, as_of_date)
        if balance != 0:
            equity_details.append({
                'account': account,
                'balance': balance
            })
            equity_total += balance
    
    # ESTADO DE RESULTADOS (último período)
    period_start = as_of_date - timedelta(days=30)  # Último mes
    
    # Ingresos
    income_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.INCOME,
        is_active=True
    ).order_by('code')
    
    income_total = 0
    income_details = []
    for account in income_accounts:
        balance = get_account_balance(account, as_of_date) - get_account_balance(account, period_start)
        if balance != 0:
            income_details.append({
                'account': account,
                'balance': balance
            })
            income_total += balance
    
    # Gastos
    expenses_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.EXPENSES,
        is_active=True
    ).order_by('code')
    
    expenses_total = 0
    expenses_details = []
    for account in expenses_accounts:
        balance = get_account_balance(account, as_of_date) - get_account_balance(account, period_start)
        if balance != 0:
            expenses_details.append({
                'account': account,
                'balance': balance
            })
            expenses_total += balance
    
    # Resultado del período
    net_income = income_total - expenses_total
    
    context = {
        'date_as_of': date_as_of,
        'as_of_date': as_of_date,
        'period_start': period_start,
        # Balance General
        'assets_total': assets_total,
        'assets_details': assets_details,
        'liabilities_total': liabilities_total,
        'liabilities_details': liabilities_details,
        'equity_total': equity_total,
        'equity_details': equity_details,
        # Estado de Resultados
        'income_total': income_total,
        'income_details': income_details,
        'expenses_total': expenses_total,
        'expenses_details': expenses_details,
        'net_income': net_income,
    }
    
    # --- Datos para gráficos ---
    # 1. Balance General (dona)
    chart_balance_labels = ['Assets', 'Liabilities', 'Equity']
    chart_balance_data = [float(assets_total), float(liabilities_total), float(equity_total)]
    
    # 2. Estado de Resultados (barras)
    chart_income_labels = ['Income', 'Expenses', 'Net Income']
    chart_income_data = [float(income_total), float(expenses_total), float(net_income)]
    
    # 3. Top cuentas de activos y pasivos
    top_assets = sorted(assets_details, key=lambda x: abs(x['balance']), reverse=True)[:5]
    top_liabilities = sorted(liabilities_details, key=lambda x: abs(x['balance']), reverse=True)[:5]
    
    chart_assets_labels = [f"{acc['account'].code} - {acc['account'].name[:15]}..." for acc in top_assets]
    chart_assets_data = [float(acc['balance']) for acc in top_assets]
    
    chart_liabilities_labels = [f"{acc['account'].code} - {acc['account'].name[:15]}..." for acc in top_liabilities]
    chart_liabilities_data = [float(acc['balance']) for acc in top_liabilities]
    
    context.update({
        'chart_balance_labels': json.dumps(chart_balance_labels),
        'chart_balance_data': json.dumps(chart_balance_data),
        'chart_income_labels': json.dumps(chart_income_labels),
        'chart_income_data': json.dumps(chart_income_data),
        'chart_assets_labels': json.dumps(chart_assets_labels),
        'chart_assets_data': json.dumps(chart_assets_data),
        'chart_liabilities_labels': json.dumps(chart_liabilities_labels),
        'chart_liabilities_data': json.dumps(chart_liabilities_data),
    })
    
    return render(request, 'accounting/reports/financial_statements.html', context) 

@login_required
def bank_reconciliation(request):
    """Vista para conciliación bancaria"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener parámetros de filtro
    account_id = request.GET.get('account')
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    
    # Obtener cuentas bancarias
    bank_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type='assets',
        name__icontains='bank'
    ).order_by('name')
    
    # Obtener asientos de la cuenta seleccionada
    entries = []
    if account_id:
        account = ChartOfAccounts.objects.get(id=account_id, empresa=empresa)
        
        # Obtener líneas de asiento para esta cuenta
        entry_lines = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__range=[date_from, date_to],
            entry__state=EntryStates.POSTED
        ).select_related('entry', 'account').order_by('entry__date')
        
        # Agrupar por asiento
        for line in entry_lines:
            entries.append({
                'entry': line.entry,
                'line': line,
                'date': line.entry.date,
                'reference': line.entry.reference,
                'description': line.name,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.credit - line.debit,
                'reconciled': False,  # Por defecto no conciliado
            })
    
    # Simular movimientos bancarios (en un sistema real vendrían de una API bancaria)
    bank_movements = []
    if account_id:
        # Generar movimientos simulados basados en los asientos
        for i, entry in enumerate(entries):
            bank_movements.append({
                'id': f'BM-{i+1:03d}',
                'date': entry['date'],
                'description': f"Bank movement for {entry['reference']}",
                'amount': entry['balance'],
                'type': 'credit' if entry['balance'] > 0 else 'debit',
                'reconciled': False,
            })
    
    # Calcular saldos
    total_entries = sum(entry['balance'] for entry in entries)
    total_bank = sum(movement['amount'] for movement in bank_movements)
    difference = total_entries - total_bank
    
    context = {
        'empresa': empresa,
        'bank_accounts': bank_accounts,
        'selected_account': account_id,
        'date_from': date_from,
        'date_to': date_to,
        'entries': entries,
        'bank_movements': bank_movements,
        'total_entries': total_entries,
        'total_bank': total_bank,
        'difference': difference,
        'reconciliation_rate': (len([e for e in entries if e['reconciled']]) / len(entries) * 100) if entries else 0,
    }
    
    return render(request, 'accounting/reports/bank_reconciliation.html', context)

@login_required
def trend_analysis(request):
    """Vista para análisis de tendencias"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener parámetros
    period = request.GET.get('period', '30')  # días
    account_type = request.GET.get('account_type', '')
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=int(period))
    
    # Obtener datos de tendencias
    trends_data = []
    
    # Agrupar por día
    current_date = start_date
    while current_date <= end_date:
        day_entries = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__date=current_date,
            entry__state=EntryStates.POSTED
        )
        
        if account_type:
            day_entries = day_entries.filter(account__account_type=account_type)
        
        total_debit = day_entries.aggregate(total=Sum('debit'))['total'] or 0
        total_credit = day_entries.aggregate(total=Sum('credit'))['total'] or 0
        count_entries = day_entries.values('entry').distinct().count()
        
        trends_data.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'debit': float(total_debit),
            'credit': float(total_credit),
            'net': float(total_credit - total_debit),
            'entries_count': count_entries,
        })
        
        current_date += timedelta(days=1)
    
    # Calcular métricas de tendencia
    if trends_data:
        net_values = [d['net'] for d in trends_data]
        trend_direction = 'up' if net_values[-1] > net_values[0] else 'down'
        trend_percentage = ((net_values[-1] - net_values[0]) / abs(net_values[0]) * 100) if net_values[0] != 0 else 0
    else:
        trend_direction = 'stable'
        trend_percentage = 0
    
    context = {
        'empresa': empresa,
        'period': period,
        'account_type': account_type,
        'trends_data': trends_data,
        'trend_direction': trend_direction,
        'trend_percentage': trend_percentage,
        'account_types': AccountTypes.CHOICES,
    }
    
    return render(request, 'accounting/reports/trend_analysis.html', context)

@login_required
def custom_reports(request):
    """Vista para reportes personalizados"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener parámetros
    report_type = request.GET.get('type', 'entries')
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    account_type = request.GET.get('account_type', '')
    journal_id = request.GET.get('journal', '')
    state = request.GET.get('state', '')
    
    # Construir consulta base
    if report_type == 'entries':
        queryset = JournalEntry.objects.filter(
            empresa=empresa,
            date__range=[date_from, date_to]
        )
        
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if state:
            queryset = queryset.filter(state=state)
            
        entries = queryset.select_related('journal', 'created_by').order_by('-date')
        
        # Paginación
        paginator = Paginator(entries, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'empresa': empresa,
            'report_type': report_type,
            'date_from': date_from,
            'date_to': date_to,
            'account_type': account_type,
            'journal_id': journal_id,
            'state': state,
            'page_obj': page_obj,
            'journals': Journal.objects.filter(empresa=empresa, is_active=True),
            'states': EntryStates.CHOICES,
        }
    
    elif report_type == 'lines':
        queryset = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__date__range=[date_from, date_to],
            entry__state=EntryStates.POSTED
        )
        
        if account_type:
            queryset = queryset.filter(account__account_type=account_type)
        if journal_id:
            queryset = queryset.filter(entry__journal_id=journal_id)
            
        lines = queryset.select_related('entry', 'account', 'entry__journal').order_by('-entry__date')
        
        # Paginación
        paginator = Paginator(lines, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'empresa': empresa,
            'report_type': report_type,
            'date_from': date_from,
            'date_to': date_to,
            'account_type': account_type,
            'journal_id': journal_id,
            'page_obj': page_obj,
            'journals': Journal.objects.filter(empresa=empresa, is_active=True),
            'account_types': AccountTypes.CHOICES,
        }
    
    return render(request, 'accounting/reports/custom_reports.html', context)

@login_required
def financial_ratios(request):
    """Vista para análisis de ratios financieros"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener fecha de análisis
    analysis_date = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    
    # Calcular saldos de cuentas por tipo
    account_balances = {}
    for account_type, _ in AccountTypes.CHOICES:
        accounts = ChartOfAccounts.objects.filter(
            empresa=empresa,
            account_type=account_type,
            is_active=True
        )
        
        total_balance = 0
        for account in accounts:
            # Obtener saldo de la cuenta hasta la fecha
            debit_total = JournalEntryLine.objects.filter(
                entry__empresa=empresa,
                account=account,
                entry__date__lte=analysis_date,
                entry__state=EntryStates.POSTED
            ).aggregate(total=Sum('debit'))['total'] or 0
            
            credit_total = JournalEntryLine.objects.filter(
                entry__empresa=empresa,
                account=account,
                entry__date__lte=analysis_date,
                entry__state=EntryStates.POSTED
            ).aggregate(total=Sum('credit'))['total'] or 0
            
            # Calcular saldo según tipo de cuenta
            if account_type in ['assets', 'expenses']:
                balance = debit_total - credit_total
            else:
                balance = credit_total - debit_total
            
            total_balance += balance
        
        account_balances[account_type] = total_balance
    
    # Calcular ratios financieros
    assets = account_balances.get('assets', 0)
    liabilities = account_balances.get('liabilities', 0)
    equity = account_balances.get('equity', 0)
    income = account_balances.get('income', 0)
    expenses = account_balances.get('expenses', 0)
    
    ratios = {
        'current_ratio': assets / liabilities if liabilities > 0 else 0,
        'debt_to_equity': liabilities / equity if equity > 0 else 0,
        'return_on_equity': (income - expenses) / equity if equity > 0 else 0,
        'profit_margin': (income - expenses) / income if income > 0 else 0,
        'asset_turnover': income / assets if assets > 0 else 0,
    }
    
    context = {
        'empresa': empresa,
        'analysis_date': analysis_date,
        'account_balances': account_balances,
        'ratios': ratios,
        'net_income': income - expenses,
    }
    
    return render(request, 'accounting/reports/financial_ratios.html', context) 

@login_required
@tiene_permiso('accounting.view_report')
def balance_sheet_report(request):
    """Reporte de Balance General"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener fecha de balance
    balance_date = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    
    def get_account_balance(account, date):
        """Calcular saldo de una cuenta hasta una fecha específica"""
        debit_total = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__lte=date,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('debit'))['total'] or 0
        
        credit_total = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__lte=date,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('credit'))['total'] or 0
        
        if account.account_type in [AccountTypes.ASSETS, AccountTypes.EXPENSES]:
            return debit_total - credit_total
        else:
            return credit_total - debit_total
    
    # Obtener cuentas por tipo
    assets = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.ASSETS,
        is_active=True
    ).order_by('code')
    
    liabilities = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.LIABILITIES,
        is_active=True
    ).order_by('code')
    
    equity = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.EQUITY,
        is_active=True
    ).order_by('code')
    
    # Calcular saldos
    assets_data = []
    total_assets = 0
    for account in assets:
        balance = get_account_balance(account, balance_date)
        assets_data.append({
            'account': account,
            'balance': balance
        })
        total_assets += balance
    
    liabilities_data = []
    total_liabilities = 0
    for account in liabilities:
        balance = get_account_balance(account, balance_date)
        liabilities_data.append({
            'account': account,
            'balance': balance
        })
        total_liabilities += balance
    
    equity_data = []
    total_equity = 0
    for account in equity:
        balance = get_account_balance(account, balance_date)
        equity_data.append({
            'account': account,
            'balance': balance
        })
        total_equity += balance
    
    # Verificar balance
    total_liabilities_equity = total_liabilities + total_equity
    balance_check = abs(total_assets - total_liabilities_equity)
    
    context = {
        'empresa': empresa,
        'balance_date': balance_date,
        'assets_data': assets_data,
        'liabilities_data': liabilities_data,
        'equity_data': equity_data,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'total_liabilities_equity': total_liabilities_equity,
        'balance_check': balance_check,
    }
    
    return render(request, 'accounting/reports/balance_sheet.html', context)

@login_required
@tiene_permiso('accounting.view_report')
def income_statement_report(request):
    """Reporte de Estado de Resultados"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener período
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    
    def get_account_balance(account, start_date, end_date):
        """Calcular saldo de una cuenta en un período específico"""
        debit_total = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__range=[start_date, end_date],
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('debit'))['total'] or 0
        
        credit_total = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__range=[start_date, end_date],
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('credit'))['total'] or 0
        
        if account.account_type == AccountTypes.EXPENSES:
            return debit_total - credit_total
        elif account.account_type == AccountTypes.INCOME:
            return credit_total - debit_total
        else:
            return 0
    
    # Obtener cuentas de ingresos y gastos
    income_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.INCOME,
        is_active=True
    ).order_by('code')
    
    expense_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        account_type=AccountTypes.EXPENSES,
        is_active=True
    ).order_by('code')
    
    # Calcular saldos
    income_data = []
    total_income = 0
    for account in income_accounts:
        balance = get_account_balance(account, date_from, date_to)
        if balance > 0:
            income_data.append({
                'account': account,
                'balance': balance
            })
            total_income += balance
    
    expense_data = []
    total_expenses = 0
    for account in expense_accounts:
        balance = get_account_balance(account, date_from, date_to)
        if balance > 0:
            expense_data.append({
                'account': account,
                'balance': balance
            })
            total_expenses += balance
    
    # Calcular resultado neto
    net_income = total_income - total_expenses
    
    context = {
        'empresa': empresa,
        'date_from': date_from,
        'date_to': date_to,
        'income_data': income_data,
        'expense_data': expense_data,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_income': net_income,
    }
    
    return render(request, 'accounting/reports/income_statement.html', context)

@login_required
@tiene_permiso('accounting.view_report')
def trial_balance_report(request):
    """Reporte de Balance de Comprobación"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener fecha de balance
    balance_date = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    account_type = request.GET.get('account_type', '')
    
    def get_account_balance(account, date):
        """Calcular saldo de una cuenta hasta una fecha específica"""
        debit_total = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__lte=date,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('debit'))['total'] or 0
        
        credit_total = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__lte=date,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('credit'))['total'] or 0
        
        return debit_total, credit_total
    
    # Obtener cuentas
    accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        is_active=True
    )
    
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    
    accounts = accounts.order_by('account_type', 'code')
    
    # Calcular saldos
    trial_balance_data = []
    total_debit = 0
    total_credit = 0
    
    for account in accounts:
        debit, credit = get_account_balance(account, balance_date)
        if debit > 0 or credit > 0:
            trial_balance_data.append({
                'account': account,
                'debit': debit,
                'credit': credit,
                'balance': debit - credit
            })
            total_debit += debit
            total_credit += credit
    
    context = {
        'empresa': empresa,
        'balance_date': balance_date,
        'account_type': account_type,
        'trial_balance_data': trial_balance_data,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'account_types': AccountTypes.CHOICES,
    }
    
    return render(request, 'accounting/reports/trial_balance.html', context)

@login_required
@tiene_permiso('accounting.view_report')
def general_ledger_report(request):
    """Reporte de Mayor General"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener parámetros
    account_id = request.GET.get('account', '')
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    
    if account_id:
        account = get_object_or_404(ChartOfAccounts, id=account_id, empresa=empresa)
        
        # Obtener movimientos de la cuenta
        movements = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__range=[date_from, date_to],
            entry__state=EntryStates.POSTED
        ).select_related('entry', 'entry__journal').order_by('entry__date', 'id')
        
        # Calcular saldo inicial
        initial_balance = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            account=account,
            entry__date__lt=date_from,
            entry__state=EntryStates.POSTED
        ).aggregate(
            total_debit=Sum('debit'),
            total_credit=Sum('credit')
        )
        
        initial_debit = initial_balance['total_debit'] or 0
        initial_credit = initial_balance['total_credit'] or 0
        
        if account.account_type in [AccountTypes.ASSETS, AccountTypes.EXPENSES]:
            initial_balance_amount = initial_debit - initial_credit
        else:
            initial_balance_amount = initial_credit - initial_debit
        
        # Calcular saldos corrientes
        running_balance = initial_balance_amount
        for movement in movements:
            if account.account_type in [AccountTypes.ASSETS, AccountTypes.EXPENSES]:
                running_balance += movement.debit - movement.credit
            else:
                running_balance += movement.credit - movement.debit
            movement.running_balance = running_balance
        
        # Paginación
        paginator = Paginator(movements, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'empresa': empresa,
            'account': account,
            'date_from': date_from,
            'date_to': date_to,
            'initial_balance': initial_balance_amount,
            'page_obj': page_obj,
        }
        
        return render(request, 'accounting/reports/general_ledger_detail.html', context)
    
    else:
        # Lista de cuentas
        accounts = ChartOfAccounts.objects.filter(
            empresa=empresa,
            is_active=True
        ).order_by('account_type', 'code')
        
        context = {
            'empresa': empresa,
            'accounts': accounts,
        }
        
        return render(request, 'accounting/reports/general_ledger.html', context)

@login_required
@tiene_permiso('accounting.view_report')
def tax_report(request):
    """Reporte de Impuestos"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener período
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    tax_id = request.GET.get('tax', '')
    
    # Obtener líneas de impuesto
    tax_lines = TaxLine.objects.filter(
        tax__empresa=empresa,
        created_at__date__range=[date_from, date_to]
    ).select_related('tax', 'tax__tax_group')
    
    if tax_id:
        tax_lines = tax_lines.filter(tax_id=tax_id)
    
    # Agrupar por impuesto
    tax_summary = tax_lines.values(
        'tax__name', 'tax__code', 'tax__amount', 'tax__tax_group__name'
    ).annotate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        count_transactions=Count('id')
    ).order_by('tax__name')
    
    # Totales generales
    total_base_amount = tax_lines.aggregate(total=Sum('base_amount'))['total'] or 0
    total_tax_amount = tax_lines.aggregate(total=Sum('tax_amount'))['total'] or 0
    
    # Agrupar por grupo de impuestos
    tax_group_summary = tax_lines.values(
        'tax__tax_group__name'
    ).annotate(
        total_base=Sum('base_amount'),
        total_tax=Sum('tax_amount'),
        count_transactions=Count('id')
    ).order_by('tax__tax_group__name')
    
    context = {
        'empresa': empresa,
        'date_from': date_from,
        'date_to': date_to,
        'tax_id': tax_id,
        'tax_summary': tax_summary,
        'tax_group_summary': tax_group_summary,
        'total_base_amount': total_base_amount,
        'total_tax_amount': total_tax_amount,
        'taxes': Tax.objects.filter(empresa=empresa, is_active=True),
    }
    
    return render(request, 'accounting/reports/tax_report.html', context)

@login_required
@tiene_permiso('accounting.view_report')
def advanced_dashboard(request):
    """Dashboard avanzado de reportes"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Obtener período
    date_from = request.GET.get('date_from', (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().date().strftime('%Y-%m-%d'))
    
    # KPIs avanzados
    total_entries = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[date_from, date_to]
    ).count()
    
    posted_entries = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[date_from, date_to],
        state=EntryStates.POSTED
    ).count()
    
    # Análisis por diario
    journal_analysis = JournalEntry.objects.filter(
        empresa=empresa,
        date__range=[date_from, date_to],
        state=EntryStates.POSTED
    ).values('journal__name').annotate(
        count=Count('id'),
        total_amount=Sum('lines__debit') + Sum('lines__credit')
    ).order_by('-count')
    
    # Análisis por tipo de cuenta
    account_type_analysis = JournalEntryLine.objects.filter(
        entry__empresa=empresa,
        entry__date__range=[date_from, date_to],
        entry__state=EntryStates.POSTED
    ).values('account__account_type').annotate(
        total_debit=Sum('debit'),
        total_credit=Sum('credit'),
        count_movements=Count('id')
    ).order_by('account__account_type')
    
    # Métricas de rendimiento
    posting_efficiency = (posted_entries / total_entries * 100) if total_entries > 0 else 0
    avg_entries_per_day = total_entries / ((datetime.strptime(date_to, '%Y-%m-%d').date() - datetime.strptime(date_from, '%Y-%m-%d').date()).days + 1)
    
    context = {
        'empresa': empresa,
        'date_from': date_from,
        'date_to': date_to,
        'total_entries': total_entries,
        'posted_entries': posted_entries,
        'journal_analysis': journal_analysis,
        'account_type_analysis': account_type_analysis,
        'posting_efficiency': posting_efficiency,
        'avg_entries_per_day': avg_entries_per_day,
    }
    
    return render(request, 'accounting/reports/advanced_dashboard.html', context)

@login_required
@tiene_permiso('accounting.view_report')
def bank_reconciliation_advanced(request):
    """Conciliación bancaria avanzada"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Esta vista sería para una implementación más avanzada de conciliación bancaria
    # Por ahora redirigimos a la vista básica
    return redirect('accounting:bank_reconciliation')

@login_required
@tiene_permiso('accounting.view_report')
def trend_analysis_advanced(request):
    """Análisis de tendencias avanzado"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Esta vista sería para una implementación más avanzada de análisis de tendencias
    # Por ahora redirigimos a la vista básica
    return redirect('accounting:trend_analysis')

@login_required
@tiene_permiso('accounting.view_report')
def custom_reports_advanced(request):
    """Reportes personalizados avanzados"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Esta vista sería para una implementación más avanzada de reportes personalizados
    # Por ahora redirigimos a la vista básica
    return redirect('accounting:custom_reports')

@login_required
@tiene_permiso('accounting.view_report')
def financial_ratios_advanced(request):
    """Ratios financieros avanzados"""
    empresa = get_user_empresa(request)
    if not empresa:
        return redirect('core:select_company')
    
    # Esta vista sería para una implementación más avanzada de ratios financieros
    # Por ahora redirigimos a la vista básica
    return redirect('accounting:financial_ratios') 