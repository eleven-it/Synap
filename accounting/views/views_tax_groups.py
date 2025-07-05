from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.http import JsonResponse

from ..models import TaxGroup, ChartOfAccounts
from ..forms import TaxGroupForm
from core.decorators import tiene_permiso


class TaxGroupListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de grupos de impuestos con filtros y búsqueda"""
    model = TaxGroup
    template_name = 'accounting/tax_groups/tax_group_list.html'
    context_object_name = 'tax_groups'
    permission_required = 'accounting.view_taxgroup'
    paginate_by = 20

    def get_queryset(self):
        """Filtrar por empresa del usuario y aplicar búsqueda"""
        queryset = TaxGroup.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('account_id', 'refund_account_id')
        
        # Búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Filtro por estado
        is_active = self.request.GET.get('is_active', '')
        if is_active != '':
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'is_active_filter': self.request.GET.get('is_active', ''),
            'total_count': self.get_queryset().count(),
            'active_count': self.get_queryset().filter(is_active=True).count(),
            'inactive_count': self.get_queryset().filter(is_active=False).count(),
        })
        return context


class TaxGroupCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear nuevo grupo de impuestos"""
    model = TaxGroup
    form_class = TaxGroupForm
    template_name = 'accounting/tax_groups/tax_group_form.html'
    permission_required = 'accounting.add_taxgroup'
    success_url = reverse_lazy('accounting:tax_group_list')

    def form_valid(self, form):
        """Asignar empresa automáticamente"""
        form.instance.empresa = self.request.user.empresa_activa
        response = super().form_valid(form)
        messages.success(self.request, _('Tax group created successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Create Tax Group')
        context['submit_text'] = _('Create Tax Group')
        return context


class TaxGroupUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar grupo de impuestos"""
    model = TaxGroup
    form_class = TaxGroupForm
    template_name = 'accounting/tax_groups/tax_group_form.html'
    permission_required = 'accounting.change_taxgroup'
    success_url = reverse_lazy('accounting:tax_group_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return TaxGroup.objects.filter(empresa=self.request.user.empresa_activa)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Tax group updated successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Edit Tax Group')
        context['submit_text'] = _('Update Tax Group')
        return context


class TaxGroupDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar grupo de impuestos"""
    model = TaxGroup
    template_name = 'accounting/tax_groups/tax_group_confirm_delete.html'
    permission_required = 'accounting.delete_taxgroup'
    success_url = reverse_lazy('accounting:tax_group_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return TaxGroup.objects.filter(empresa=self.request.user.empresa_activa)

    def delete(self, request, *args, **kwargs):
        """Verificar que no tenga impuestos asociados"""
        tax_group = self.get_object()
        if tax_group.taxes.exists():
            messages.error(
                request, 
                _('Cannot delete tax group. It has associated taxes.')
            )
            return redirect('accounting:tax_group_list')
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Tax group deleted successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Confirm Tax Group Deletion')
        return context


@tiene_permiso('accounting.change_taxgroup')
def toggle_tax_group_status(request, pk):
    """Activar/desactivar grupo de impuestos"""
    try:
        tax_group = TaxGroup.objects.get(
            pk=pk, 
            empresa=request.user.empresa_activa
        )
        tax_group.is_active = not tax_group.is_active
        tax_group.save()
        
        status = 'activated' if tax_group.is_active else 'deactivated'
        messages.success(
            request, 
            _('Tax group {} successfully.').format(status)
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': tax_group.is_active,
                'message': _('Tax group {} successfully.').format(status)
            })
        
    except TaxGroup.DoesNotExist:
        messages.error(request, _('Tax group not found.'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('Tax group not found.')
            })
    
    return redirect('accounting:tax_group_list') 