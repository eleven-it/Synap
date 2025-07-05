from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse

from ..models import Tax, TaxGroup
from ..forms import TaxForm
from core.decorators import tiene_permiso


class TaxListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de impuestos con filtros y búsqueda"""
    model = Tax
    template_name = 'accounting/taxes/tax_list.html'
    context_object_name = 'taxes'
    permission_required = 'accounting.view_tax'
    paginate_by = 20

    def get_queryset(self):
        """Filtrar por empresa del usuario y aplicar búsqueda"""
        queryset = Tax.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('tax_group', 'account_id', 'refund_account_id')
        
        # Búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search) |
                Q(tax_group__name__icontains=search)
            )
        
        # Filtro por estado
        is_active = self.request.GET.get('is_active', '')
        if is_active != '':
            queryset = queryset.filter(is_active=is_active == 'true')
        
        # Filtro por grupo de impuestos
        tax_group = self.request.GET.get('tax_group', '')
        if tax_group:
            queryset = queryset.filter(tax_group_id=tax_group)
        
        # Filtro por tipo de impuesto
        amount_type = self.request.GET.get('amount_type', '')
        if amount_type:
            queryset = queryset.filter(amount_type=amount_type)
        
        return queryset.order_by('tax_group__name', 'sequence', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'is_active_filter': self.request.GET.get('is_active', ''),
            'tax_group_filter': self.request.GET.get('tax_group', ''),
            'amount_type_filter': self.request.GET.get('amount_type', ''),
            'total_count': self.get_queryset().count(),
            'active_count': self.get_queryset().filter(is_active=True).count(),
            'inactive_count': self.get_queryset().filter(is_active=False).count(),
            'tax_groups': TaxGroup.objects.filter(
                empresa=self.request.user.empresa_activa, 
                is_active=True
            ).order_by('name'),
            'amount_types': Tax._meta.get_field('amount_type').choices,
        })
        return context


class TaxCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear nuevo impuesto"""
    model = Tax
    form_class = TaxForm
    template_name = 'accounting/taxes/tax_form.html'
    permission_required = 'accounting.add_tax'
    success_url = reverse_lazy('accounting:tax_list')

    def form_valid(self, form):
        """Asignar empresa automáticamente"""
        form.instance.empresa = self.request.user.empresa_activa
        response = super().form_valid(form)
        messages.success(self.request, _('Tax created successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Create Tax')
        context['submit_text'] = _('Create Tax')
        return context


class TaxUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar impuesto"""
    model = Tax
    form_class = TaxForm
    template_name = 'accounting/taxes/tax_form.html'
    permission_required = 'accounting.change_tax'
    success_url = reverse_lazy('accounting:tax_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return Tax.objects.filter(empresa=self.request.user.empresa_activa)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Tax updated successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Edit Tax')
        context['submit_text'] = _('Update Tax')
        return context


class TaxDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar impuesto"""
    model = Tax
    template_name = 'accounting/taxes/tax_confirm_delete.html'
    permission_required = 'accounting.delete_tax'
    success_url = reverse_lazy('accounting:tax_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return Tax.objects.filter(empresa=self.request.user.empresa_activa)

    def delete(self, request, *args, **kwargs):
        """Verificar que no tenga líneas de impuesto asociadas"""
        tax = self.get_object()
        if tax.tax_lines.exists():
            messages.error(
                request, 
                _('Cannot delete tax. It has associated tax lines.')
            )
            return redirect('accounting:tax_list')
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Tax deleted successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Confirm Tax Deletion')
        return context


@tiene_permiso('accounting.change_tax')
def toggle_tax_status(request, pk):
    """Activar/desactivar impuesto"""
    try:
        tax = Tax.objects.get(
            pk=pk, 
            empresa=request.user.empresa_activa
        )
        tax.is_active = not tax.is_active
        tax.save()
        
        status = 'activated' if tax.is_active else 'deactivated'
        messages.success(
            request, 
            _('Tax {} successfully.').format(status)
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': tax.is_active,
                'message': _('Tax {} successfully.').format(status)
            })
        
    except Tax.DoesNotExist:
        messages.error(request, _('Tax not found.'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('Tax not found.')
            })
    
    return redirect('accounting:tax_list')


@tiene_permiso('accounting.view_tax')
def tax_detail(request, pk):
    """Detalle del impuesto"""
    try:
        tax = Tax.objects.select_related(
            'tax_group', 'account_id', 'refund_account_id'
        ).get(
            pk=pk, 
            empresa=request.user.empresa_activa
        )
        
        # Obtener estadísticas de uso
        tax_lines_count = tax.tax_lines.count()
        recent_tax_lines = tax.tax_lines.order_by('-created_at')[:10]
        
        context = {
            'tax': tax,
            'tax_lines_count': tax_lines_count,
            'recent_tax_lines': recent_tax_lines,
        }
        
        return render(request, 'accounting/taxes/tax_detail.html', context)
        
    except Tax.DoesNotExist:
        messages.error(request, _('Tax not found.'))
        return redirect('accounting:tax_list') 