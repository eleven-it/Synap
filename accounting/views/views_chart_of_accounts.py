from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.db.models import Count, Sum
from django.core.paginator import Paginator

from ..models import ChartOfAccounts, AccountTypes
from ..forms import ChartOfAccountsForm
from core.decorators import tiene_permiso


class ChartOfAccountsListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista del plan de cuentas con filtros y búsqueda"""
    model = ChartOfAccounts
    template_name = 'accounting/chart_of_accounts/account_list.html'
    context_object_name = 'accounts'
    permission_required = 'accounting.view_chartofaccounts'
    paginate_by = 50

    def get_queryset(self):
        """Filtrar por empresa del usuario y aplicar búsqueda"""
        queryset = ChartOfAccounts.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('parent')
        
        # Búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Filtro por tipo de cuenta
        account_type = self.request.GET.get('account_type', '')
        if account_type:
            queryset = queryset.filter(account_type=account_type)
        
        # Filtro por estado
        is_active = self.request.GET.get('is_active', '')
        if is_active != '':
            queryset = queryset.filter(is_active=is_active == 'true')
        
        # Filtro por cuenta padre
        parent = self.request.GET.get('parent', '')
        if parent == 'null':
            queryset = queryset.filter(parent__isnull=True)
        elif parent:
            queryset = queryset.filter(parent_id=parent)
        
        return queryset.order_by('code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.empresa_activa
        
        # Estadísticas
        total_accounts = ChartOfAccounts.objects.filter(empresa=empresa).count()
        active_accounts = ChartOfAccounts.objects.filter(empresa=empresa, is_active=True).count()
        inactive_accounts = ChartOfAccounts.objects.filter(empresa=empresa, is_active=False).count()
        
        # Cuentas por tipo
        accounts_by_type = ChartOfAccounts.objects.filter(empresa=empresa).values(
            'account_type'
        ).annotate(
            count=Count('id')
        ).order_by('account_type')
        
        # Cuentas padre disponibles para filtro
        parent_accounts = ChartOfAccounts.objects.filter(
            empresa=empresa,
            is_active=True
        ).order_by('code', 'name')
        
        context.update({
            'search': self.request.GET.get('search', ''),
            'account_type_filter': self.request.GET.get('account_type', ''),
            'is_active_filter': self.request.GET.get('is_active', ''),
            'parent_filter': self.request.GET.get('parent', ''),
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'inactive_accounts': inactive_accounts,
            'accounts_by_type': accounts_by_type,
            'parent_accounts': parent_accounts,
            'account_types': AccountTypes.CHOICES,
        })
        return context


class ChartOfAccountsCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear nueva cuenta contable"""
    model = ChartOfAccounts
    form_class = ChartOfAccountsForm
    template_name = 'accounting/chart_of_accounts/account_form.html'
    permission_required = 'accounting.add_chartofaccounts'
    success_url = reverse_lazy('accounting:chart_of_accounts_list')

    def form_valid(self, form):
        """Asignar empresa automáticamente"""
        form.instance.empresa = self.request.user.empresa_activa
        response = super().form_valid(form)
        messages.success(self.request, _('Account created successfully.'))
        return response

    def get_form_kwargs(self):
        """Pasar empresa al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa_activa
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Create Account')
        context['submit_text'] = _('Create Account')
        return context


class ChartOfAccountsUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar cuenta contable"""
    model = ChartOfAccounts
    form_class = ChartOfAccountsForm
    template_name = 'accounting/chart_of_accounts/account_form.html'
    permission_required = 'accounting.change_chartofaccounts'
    success_url = reverse_lazy('accounting:chart_of_accounts_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return ChartOfAccounts.objects.filter(empresa=self.request.user.empresa_activa)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Account updated successfully.'))
        return response

    def get_form_kwargs(self):
        """Pasar empresa al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa_activa
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Edit Account')
        context['submit_text'] = _('Update Account')
        return context


class ChartOfAccountsDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar cuenta contable"""
    model = ChartOfAccounts
    template_name = 'accounting/chart_of_accounts/account_confirm_delete.html'
    permission_required = 'accounting.delete_chartofaccounts'
    success_url = reverse_lazy('accounting:chart_of_accounts_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return ChartOfAccounts.objects.filter(empresa=self.request.user.empresa_activa)

    def delete(self, request, *args, **kwargs):
        """Verificar que no tenga cuentas hijas o líneas de asiento"""
        account = self.get_object()
        
        # Verificar cuentas hijas
        if account.children.exists():
            messages.error(
                request, 
                _('Cannot delete account. It has child accounts.')
            )
            return redirect('accounting:chart_of_accounts_list')
        
        # Verificar líneas de asiento
        if account.entry_lines.exists():
            messages.error(
                request, 
                _('Cannot delete account. It has journal entry lines.')
            )
            return redirect('accounting:chart_of_accounts_list')
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Account deleted successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Confirm Account Deletion')
        return context


class ChartOfAccountsDetailView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Detalle de cuenta contable con movimientos"""
    model = ChartOfAccounts
    template_name = 'accounting/chart_of_accounts/account_detail.html'
    context_object_name = 'account'
    permission_required = 'accounting.view_chartofaccounts'
    paginate_by = 20

    def get_queryset(self):
        """Obtener la cuenta específica"""
        return ChartOfAccounts.objects.filter(
            pk=self.kwargs['pk'],
            empresa=self.request.user.empresa_activa
        ).select_related('parent')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.get_queryset().first()
        
        if not account:
            messages.error(self.request, _('Account not found.'))
            return context
        
        # Obtener movimientos de la cuenta
        entry_lines = account.entry_lines.select_related(
            'entry', 'partner', 'currency'
        ).order_by('-entry__date', '-entry__created_at')
        
        # Paginar movimientos
        paginator = Paginator(entry_lines, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Calcular saldos
        total_debit = entry_lines.aggregate(Sum('debit'))['debit__sum'] or 0
        total_credit = entry_lines.aggregate(Sum('credit'))['credit__sum'] or 0
        balance = total_debit - total_credit
        
        # Cuentas hijas
        child_accounts = account.children.filter(is_active=True).order_by('code')
        
        context.update({
            'account': account,
            'entry_lines': page_obj,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'balance': balance,
            'child_accounts': child_accounts,
            'child_accounts_count': child_accounts.count(),
            'entry_lines_count': entry_lines.count(),
        })
        return context


@tiene_permiso('accounting.change_chartofaccounts')
def toggle_account_status(request, pk):
    """Activar/desactivar cuenta contable"""
    try:
        account = ChartOfAccounts.objects.get(
            pk=pk, 
            empresa=request.user.empresa_activa
        )
        account.is_active = not account.is_active
        account.save()
        
        status = 'activated' if account.is_active else 'deactivated'
        messages.success(
            request, 
            _('Account {} successfully.').format(status)
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': account.is_active,
                'message': _('Account {} successfully.').format(status)
            })
        
    except ChartOfAccounts.DoesNotExist:
        messages.error(request, _('Account not found.'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('Account not found.')
            })
    
    return redirect('accounting:chart_of_accounts_list')


@tiene_permiso('accounting.view_chartofaccounts')
def account_tree_view(request):
    """Vista de árbol del plan de cuentas"""
    empresa = request.user.empresa_activa
    
    # Obtener cuentas padre (nivel raíz)
    root_accounts = ChartOfAccounts.objects.filter(
        empresa=empresa,
        parent__isnull=True,
        is_active=True
    ).order_by('code')
    
    context = {
        'root_accounts': root_accounts,
        'account_types': AccountTypes.CHOICES,
    }
    
    return render(request, 'accounting/chart_of_accounts/account_tree.html', context)


@tiene_permiso('accounting.view_chartofaccounts')
def account_balance_sheet(request):
    """Balance de cuentas"""
    empresa = request.user.empresa_activa
    
    # Obtener cuentas por tipo
    accounts_by_type = {}
    for account_type, label in AccountTypes.CHOICES:
        accounts = ChartOfAccounts.objects.filter(
            empresa=empresa,
            account_type=account_type,
            is_active=True
        ).order_by('code')
        
        # Calcular saldos para cada cuenta
        for account in accounts:
            total_debit = account.entry_lines.aggregate(Sum('debit'))['debit__sum'] or 0
            total_credit = account.entry_lines.aggregate(Sum('credit'))['credit__sum'] or 0
            account.balance = total_debit - total_credit
        
        accounts_by_type[account_type] = {
            'label': label,
            'accounts': accounts,
            'total_debit': sum(acc.entry_lines.aggregate(Sum('debit'))['debit__sum'] or 0 for acc in accounts),
            'total_credit': sum(acc.entry_lines.aggregate(Sum('credit'))['credit__sum'] or 0 for acc in accounts),
        }
    
    context = {
        'accounts_by_type': accounts_by_type,
        'account_types': AccountTypes.CHOICES,
    }
    
    return render(request, 'accounting/chart_of_accounts/account_balance_sheet.html', context) 