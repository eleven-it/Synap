from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin

from ..models import Tax, TaxGroup, ChartOfAccounts
from ..forms import TaxForm
from ..services.tax_service import TaxService
from core.models import Empresa
from core.utils import get_empresa_actual


# ... existing code ...

class TaxListView(LoginRequiredMixin, ListView):
    """Vista para listar impuestos individuales con filtros y paginación"""
    model = Tax
    template_name = 'accounting/taxes/tax_list.html'
    context_object_name = 'taxes'
    paginate_by = 10
    
    def get_queryset(self):
        """Filtrar impuestos según parámetros de búsqueda"""
        empresa = get_empresa_actual(self.request)
        queryset = Tax.objects.filter(empresa=empresa).select_related('tax_group', 'account_id', 'refund_account_id')
        
        # Filtro de búsqueda
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Filtro de estado
        is_active_filter = self.request.GET.get('is_active', '')
        if is_active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active_filter == 'false':
            queryset = queryset.filter(is_active=False)
        
        # Filtro de grupo de impuestos
        tax_group_filter = self.request.GET.get('tax_group', '')
        if tax_group_filter:
            queryset = queryset.filter(tax_group_id=tax_group_filter)
        
        # Filtro de tipo de cantidad
        amount_type_filter = self.request.GET.get('amount_type', '')
        if amount_type_filter:
            queryset = queryset.filter(amount_type=amount_type_filter)
        
        return queryset.order_by('sequence', 'name')
    
    def get_context_data(self, **kwargs):
        """Agregar contexto adicional para filtros y estadísticas"""
        context = super().get_context_data(**kwargs)
        empresa = get_empresa_actual(self.request)
        
        # Estadísticas
        all_taxes = Tax.objects.filter(empresa=empresa)
        context['total_count'] = all_taxes.count()
        context['active_count'] = all_taxes.filter(is_active=True).count()
        context['inactive_count'] = all_taxes.filter(is_active=False).count()
        
        # Opciones de filtro
        context['tax_groups'] = TaxGroup.objects.filter(empresa=empresa).order_by('name')
        context['search'] = self.request.GET.get('search', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '')
        context['tax_group_filter'] = self.request.GET.get('tax_group', '')
        context['amount_type_filter'] = self.request.GET.get('amount_type', '')
        
        return context


class TaxCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Vista para crear un nuevo impuesto"""
    model = Tax
    form_class = TaxForm
    template_name = 'accounting/taxes/tax_form.html'
    success_url = reverse_lazy('accounting:tax_list')
    success_message = _("Tax '%(name)s' was created successfully.")
    
    def get_form_kwargs(self):
        """Pasar la empresa actual al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = get_empresa_actual(self.request)
        return kwargs
    
    def form_valid(self, form):
        """Asignar empresa y guardar el impuesto"""
        form.instance.empresa = get_empresa_actual(self.request)
        response = super().form_valid(form)
        
        # Mostrar mensaje de éxito con animación
        messages.success(self.request, self.success_message % {'name': form.instance.name})
        return response


class TaxUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Vista para editar un impuesto existente"""
    model = Tax
    form_class = TaxForm
    template_name = 'accounting/taxes/tax_form.html'
    success_url = reverse_lazy('accounting:tax_list')
    success_message = _("Tax '%(name)s' was updated successfully.")
    
    def get_queryset(self):
        """Filtrar por empresa actual"""
        empresa = get_empresa_actual(self.request)
        return Tax.objects.filter(empresa=empresa)
    
    def get_form_kwargs(self):
        """Pasar la empresa actual al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = get_empresa_actual(self.request)
        return kwargs
    
    def form_valid(self, form):
        """Guardar cambios y mostrar mensaje"""
        response = super().form_valid(form)
        messages.success(self.request, self.success_message % {'name': form.instance.name})
        return response


class TaxDeleteView(LoginRequiredMixin, DeleteView):
    """Vista para eliminar un impuesto"""
    model = Tax
    template_name = 'accounting/taxes/tax_delete.html'
    success_url = reverse_lazy('accounting:tax_list')
    
    def get_queryset(self):
        """Filtrar por empresa actual"""
        empresa = get_empresa_actual(self.request)
        return Tax.objects.filter(empresa=empresa)
    
    def get_context_data(self, **kwargs):
        """Agregar información sobre objetos relacionados"""
        context = super().get_context_data(**kwargs)
        
        # Verificar si hay objetos relacionados
        tax = self.get_object()
        related_objects = []
        
        # Aquí puedes agregar verificaciones de objetos relacionados
        # Por ejemplo, verificar si el impuesto está siendo usado en ventas, etc.
        
        context['related_objects'] = related_objects
        return context
    
    def delete(self, request, *args, **kwargs):
        """Eliminar y mostrar mensaje de éxito"""
        tax = self.get_object()
        messages.success(request, _("Tax '%(name)s' was deleted successfully.") % {'name': tax.name})
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def tax_toggle_status(request, pk):
    """Cambiar el estado activo/inactivo de un impuesto"""
    try:
        empresa = get_empresa_actual(request)
        tax = get_object_or_404(Tax, pk=pk, empresa=empresa)
        
        # Cambiar estado
        tax.is_active = not tax.is_active
        tax.save()
        
        status_text = _("activated") if tax.is_active else _("deactivated")
        
        return JsonResponse({
            'success': True,
            'message': _("Tax '%(name)s' was %(status)s successfully.") % {
                'name': tax.name,
                'status': status_text
            },
            'is_active': tax.is_active
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': _("Error updating tax status: %(error)s") % {'error': str(e)}
        }, status=400)


@login_required
def tax_detail(request, pk):
    """Vista de detalle de un impuesto (opcional)"""
    empresa = get_empresa_actual(request)
    tax = get_object_or_404(Tax, pk=pk, empresa=empresa)
    
    context = {
        'tax': tax,
        'empresa': empresa,
    }
    
    return render(request, 'accounting/taxes/tax_detail.html', context)


@login_required
def tax_duplicate(request, pk):
    """Duplicar un impuesto existente"""
    empresa = get_empresa_actual(request)
    original_tax = get_object_or_404(Tax, pk=pk, empresa=empresa)
    
    if request.method == 'POST':
        # Crear copia del impuesto
        new_tax = Tax.objects.create(
            empresa=empresa,
            name=f"{original_tax.name} (Copy)",
            code=f"{original_tax.code}_COPY",
            description=original_tax.description,
            tax_group=original_tax.tax_group,
            amount_type=original_tax.amount_type,
            amount=original_tax.amount,
            account_id=original_tax.account_id,
            refund_account_id=original_tax.refund_account_id,
            sequence=original_tax.sequence + 1,
            is_active=False  # Por defecto inactivo
        )
        
        messages.success(request, _("Tax '%(name)s' was duplicated successfully.") % {'name': new_tax.name})
        return redirect('accounting:tax_edit', pk=new_tax.pk)
    
    context = {
        'tax': original_tax,
        'empresa': empresa,
    }
    
    return render(request, 'accounting/taxes/tax_duplicate.html', context)


@login_required
def tax_bulk_actions(request):
    """Acciones masivas en impuestos"""
    if request.method == 'POST':
        empresa = get_empresa_actual(request)
        action = request.POST.get('action')
        tax_ids = request.POST.getlist('tax_ids')
        
        if not tax_ids:
            messages.error(request, _("No taxes selected."))
            return redirect('accounting:tax_list')
        
        taxes = Tax.objects.filter(pk__in=tax_ids, empresa=empresa)
        
        if action == 'activate':
            taxes.update(is_active=True)
            messages.success(request, _("%(count)d taxes were activated.") % {'count': taxes.count()})
        elif action == 'deactivate':
            taxes.update(is_active=False)
            messages.success(request, _("%(count)d taxes were deactivated.") % {'count': taxes.count()})
        elif action == 'delete':
            count = taxes.count()
            taxes.delete()
            messages.success(request, _("%(count)d taxes were deleted.") % {'count': count})
        else:
            messages.error(request, _("Invalid action."))
    
    return redirect('accounting:tax_list')


@login_required
def tax_export(request):
    """Exportar lista de impuestos"""
    empresa = get_empresa_actual(request)
    taxes = Tax.objects.filter(empresa=empresa).select_related('tax_group', 'account_id', 'refund_account_id')
    
    # Aquí implementarías la lógica de exportación
    # Por ejemplo, generar CSV, Excel, PDF, etc.
    
    messages.info(request, _("Export functionality will be implemented in the next phase."))
    return redirect('accounting:tax_list') 