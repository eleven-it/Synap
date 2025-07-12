from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.views.generic.edit import FormView
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.messages.views import SuccessMessageMixin

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Button, HTML

from ..models import FiscalYear, AccountingPeriod, JournalEntry, JournalEntryLine
from ..forms import FiscalYearForm, AccountingPeriodForm
from core.utils import get_empresa_actual


# --- VISTAS DE AÑOS FISCALES ---

class FiscalYearListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de años fiscales"""
    model = FiscalYear
    template_name = 'accounting/fiscal_years/fiscal_year_list.html'
    context_object_name = 'fiscal_years'
    permission_required = 'accounting.view_fiscal_year'
    paginate_by = 20

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        queryset = FiscalYear.objects.filter(empresa=empresa)
        
        # Filtros
        search = self.request.GET.get('search', '')
        status = self.request.GET.get('status', '')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'closed':
                queryset = queryset.filter(is_closed=True)
            elif status == 'current':
                today = timezone.now().date()
                queryset = queryset.filter(date_from__lte=today, date_to__gte=today)
        
        return queryset.order_by('-date_from')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = get_empresa_actual(self.request)
        
        # Estadísticas
        context['stats'] = {
            'total_fiscal_years': FiscalYear.objects.filter(empresa=empresa).count(),
            'active_fiscal_years': FiscalYear.objects.filter(empresa=empresa, is_active=True).count(),
            'closed_fiscal_years': FiscalYear.objects.filter(empresa=empresa, is_closed=True).count(),
            'current_fiscal_year': FiscalYear.objects.filter(
                empresa=empresa,
                date_from__lte=timezone.now().date(),
                date_to__gte=timezone.now().date()
            ).first()
        }
        
        return context


class FiscalYearCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear año fiscal"""
    model = FiscalYear
    form_class = FiscalYearForm
    template_name = 'accounting/fiscal_years/fiscal_year_form.html'
    permission_required = 'accounting.add_fiscal_year'
    success_url = reverse_lazy('accounting:fiscal_year_list')
    success_message = _('Fiscal year created successfully.')

    def form_valid(self, form):
        form.instance.empresa = get_empresa_actual(self.request)
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Create Fiscal Year')
        context['submit_text'] = _('Create Fiscal Year')
        return context


class FiscalYearUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar año fiscal"""
    model = FiscalYear
    form_class = FiscalYearForm
    template_name = 'accounting/fiscal_years/fiscal_year_form.html'
    permission_required = 'accounting.change_fiscal_year'
    success_url = reverse_lazy('accounting:fiscal_year_list')
    success_message = _('Fiscal year updated successfully.')

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        return FiscalYear.objects.filter(empresa=empresa)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Fiscal Year')
        context['submit_text'] = _('Update Fiscal Year')
        return context


class FiscalYearDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle del año fiscal"""
    model = FiscalYear
    template_name = 'accounting/fiscal_years/fiscal_year_detail.html'
    permission_required = 'accounting.view_fiscal_year'
    context_object_name = 'fiscal_year'

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        return FiscalYear.objects.filter(empresa=empresa)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fiscal_year = self.get_object()
        
        # Estadísticas del año fiscal
        context['stats'] = {
            'total_periods': fiscal_year.periods.count(),
            'closed_periods': fiscal_year.periods.filter(is_closed=True).count(),
            'open_periods': fiscal_year.periods.filter(is_closed=False).count(),
            'total_entries': JournalEntry.objects.filter(
                empresa=fiscal_year.empresa,
                date__gte=fiscal_year.date_from,
                date__lte=fiscal_year.date_to
            ).count(),
            'total_debits': JournalEntryLine.objects.filter(
                entry__empresa=fiscal_year.empresa,
                entry__date__gte=fiscal_year.date_from,
                entry__date__lte=fiscal_year.date_to,
                entry__state='posted'
            ).aggregate(total=Sum('debit'))['total'] or 0,
            'total_credits': JournalEntryLine.objects.filter(
                entry__empresa=fiscal_year.empresa,
                entry__date__gte=fiscal_year.date_from,
                entry__date__lte=fiscal_year.date_to,
                entry__state='posted'
            ).aggregate(total=Sum('credit'))['total'] or 0,
        }
        
        # Períodos del año fiscal
        context['periods'] = fiscal_year.periods.all().order_by('sequence')
        
        return context


class FiscalYearDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar año fiscal"""
    model = FiscalYear
    template_name = 'accounting/fiscal_years/fiscal_year_confirm_delete.html'
    permission_required = 'accounting.delete_fiscal_year'
    success_url = reverse_lazy('accounting:fiscal_year_list')
    success_message = _('Fiscal year deleted successfully.')

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        return FiscalYear.objects.filter(empresa=empresa)

    def delete(self, request, *args, **kwargs):
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)


@login_required
@permission_required('accounting.change_fiscal_year')
def close_fiscal_year(request, pk):
    """Cerrar año fiscal"""
    empresa = get_empresa_actual(request)
    fiscal_year = get_object_or_404(FiscalYear, pk=pk, empresa=empresa)
    
    try:
        with transaction.atomic():
            fiscal_year.close(request.user)
            messages.success(request, _('Fiscal year closed successfully.'))
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('accounting:fiscal_year_detail', pk=pk)


@login_required
@permission_required('accounting.change_fiscal_year')
def reopen_fiscal_year(request, pk):
    """Reabrir año fiscal"""
    empresa = get_empresa_actual(request)
    fiscal_year = get_object_or_404(FiscalYear, pk=pk, empresa=empresa)
    
    try:
        with transaction.atomic():
            fiscal_year.reopen(request.user)
            messages.success(request, _('Fiscal year reopened successfully.'))
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('accounting:fiscal_year_detail', pk=pk)


# --- VISTAS DE PERÍODOS CONTABLES ---

class AccountingPeriodListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de períodos contables"""
    model = AccountingPeriod
    template_name = 'accounting/periods/accounting_period_list.html'
    context_object_name = 'periods'
    permission_required = 'accounting.view_accounting_period'
    paginate_by = 20

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        queryset = AccountingPeriod.objects.filter(fiscal_year__empresa=empresa).select_related('fiscal_year')
        
        # Filtros
        search = self.request.GET.get('search', '')
        fiscal_year = self.request.GET.get('fiscal_year', '')
        status = self.request.GET.get('status', '')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        if fiscal_year:
            queryset = queryset.filter(fiscal_year_id=fiscal_year)
        
        if status:
            if status == 'active':
                queryset = queryset.filter(is_active=True)
            elif status == 'closed':
                queryset = queryset.filter(is_closed=True)
            elif status == 'current':
                today = timezone.now().date()
                queryset = queryset.filter(date_from__lte=today, date_to__gte=today)
        
        return queryset.order_by('fiscal_year', 'sequence')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = get_empresa_actual(self.request)
        
        # Estadísticas
        context['stats'] = {
            'total_periods': AccountingPeriod.objects.filter(fiscal_year__empresa=empresa).count(),
            'active_periods': AccountingPeriod.objects.filter(fiscal_year__empresa=empresa, is_active=True).count(),
            'closed_periods': AccountingPeriod.objects.filter(fiscal_year__empresa=empresa, is_closed=True).count(),
            'current_period': AccountingPeriod.objects.filter(
                fiscal_year__empresa=empresa,
                date_from__lte=timezone.now().date(),
                date_to__gte=timezone.now().date()
            ).first()
        }
        
        # Años fiscales para filtro
        context['fiscal_years'] = FiscalYear.objects.filter(empresa=empresa).order_by('-date_from')
        
        return context


class AccountingPeriodCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear período contable"""
    model = AccountingPeriod
    form_class = AccountingPeriodForm
    template_name = 'accounting/periods/accounting_period_form.html'
    permission_required = 'accounting.add_accounting_period'
    success_url = reverse_lazy('accounting:accounting_period_list')
    success_message = _('Accounting period created successfully.')

    def form_valid(self, form):
        # La empresa se asigna a través del fiscal_year
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Create Accounting Period')
        context['submit_text'] = _('Create Period')
        return context


class AccountingPeriodUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar período contable"""
    model = AccountingPeriod
    form_class = AccountingPeriodForm
    template_name = 'accounting/periods/accounting_period_form.html'
    permission_required = 'accounting.change_accounting_period'
    success_url = reverse_lazy('accounting:accounting_period_list')
    success_message = _('Accounting period updated successfully.')

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        return AccountingPeriod.objects.filter(fiscal_year__empresa=empresa)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Edit Accounting Period')
        context['submit_text'] = _('Update Period')
        return context


class AccountingPeriodDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle del período contable"""
    model = AccountingPeriod
    template_name = 'accounting/periods/accounting_period_detail.html'
    permission_required = 'accounting.view_accounting_period'
    context_object_name = 'period'

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        return AccountingPeriod.objects.filter(fiscal_year__empresa=empresa).select_related('fiscal_year')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.get_object()
        
        # Estadísticas del período
        context['stats'] = {
            'total_entries': period.entries_count,
            'total_debits': period.total_debits,
            'total_credits': period.total_credits,
            'balance': period.balance,
            'duration_days': period.duration_days,
        }
        
        # Últimos asientos del período
        context['recent_entries'] = JournalEntry.objects.filter(
            empresa=period.fiscal_year.empresa,
            date__gte=period.date_from,
            date__lte=period.date_to
        ).order_by('-date', '-created_at')[:10]
        
        return context


class AccountingPeriodDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar período contable"""
    model = AccountingPeriod
    form_class = AccountingPeriodForm
    template_name = 'accounting/periods/accounting_period_confirm_delete.html'
    permission_required = 'accounting.delete_accounting_period'
    success_url = reverse_lazy('accounting:accounting_period_list')
    success_message = _('Accounting period deleted successfully.')

    def get_queryset(self):
        empresa = get_empresa_actual(self.request)
        return AccountingPeriod.objects.filter(fiscal_year__empresa=empresa)

    def delete(self, request, *args, **kwargs):
        messages.success(request, self.success_message)
        return super().delete(request, *args, **kwargs)


@login_required
@permission_required('accounting.change_accounting_period')
def close_accounting_period(request, pk):
    """Cerrar período contable"""
    empresa = get_empresa_actual(request)
    period = get_object_or_404(AccountingPeriod, pk=pk, fiscal_year__empresa=empresa)
    
    try:
        with transaction.atomic():
            period.close(request.user)
            messages.success(request, _('Accounting period closed successfully.'))
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('accounting:accounting_period_detail', pk=pk)


@login_required
@permission_required('accounting.change_accounting_period')
def reopen_accounting_period(request, pk):
    """Reabrir período contable"""
    empresa = get_empresa_actual(request)
    period = get_object_or_404(AccountingPeriod, pk=pk, fiscal_year__empresa=empresa)
    
    try:
        with transaction.atomic():
            period.reopen(request.user)
            messages.success(request, _('Accounting period reopened successfully.'))
    except Exception as e:
        messages.error(request, str(e))
    
    return redirect('accounting:accounting_period_detail', pk=pk)


# --- VISTAS DE DASHBOARD ---

@login_required
@permission_required('accounting.view_fiscal_year')
def periods_dashboard(request):
    """Dashboard de períodos contables"""
    empresa = get_empresa_actual(request)
    
    # Año fiscal actual
    current_fiscal_year = FiscalYear.objects.filter(
        empresa=empresa,
        date_from__lte=timezone.now().date(),
        date_to__gte=timezone.now().date()
    ).first()
    
    # Período actual
    current_period = AccountingPeriod.objects.filter(
        fiscal_year__empresa=empresa,
        date_from__lte=timezone.now().date(),
        date_to__gte=timezone.now().date()
    ).first()
    
    # Estadísticas generales
    stats = {
        'total_fiscal_years': FiscalYear.objects.filter(empresa=empresa).count(),
        'active_fiscal_years': FiscalYear.objects.filter(empresa=empresa, is_active=True).count(),
        'total_periods': AccountingPeriod.objects.filter(fiscal_year__empresa=empresa).count(),
        'closed_periods': AccountingPeriod.objects.filter(fiscal_year__empresa=empresa, is_closed=True).count(),
        'open_periods': AccountingPeriod.objects.filter(fiscal_year__empresa=empresa, is_closed=False).count(),
    }
    
    # Últimos años fiscales
    recent_fiscal_years = FiscalYear.objects.filter(empresa=empresa).order_by('-date_from')[:5]
    
    # Períodos que necesitan atención
    periods_needing_attention = AccountingPeriod.objects.filter(
        fiscal_year__empresa=empresa,
        is_active=True,
        is_closed=False
    ).order_by('date_to')[:5]
    
    context = {
        'current_fiscal_year': current_fiscal_year,
        'current_period': current_period,
        'stats': stats,
        'recent_fiscal_years': recent_fiscal_years,
        'periods_needing_attention': periods_needing_attention,
    }
    
    return render(request, 'accounting/periods/periods_dashboard.html', context) 