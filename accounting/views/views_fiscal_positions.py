from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse

from ..models import FiscalPosition, FiscalPositionTax, Tax
from ..forms import FiscalPositionForm, FiscalPositionTaxForm
from core.decorators import tiene_permiso


class FiscalPositionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de posiciones fiscales con filtros y búsqueda"""
    model = FiscalPosition
    template_name = 'accounting/fiscal_positions/fiscal_position_list.html'
    context_object_name = 'fiscal_positions'
    permission_required = 'accounting.view_fiscalposition'
    paginate_by = 20

    def get_queryset(self):
        """Filtrar por empresa del usuario y aplicar búsqueda"""
        queryset = FiscalPosition.objects.filter(
            empresa=self.request.user.empresa_activa
        )
        
        # Búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search) |
                Q(country_id__icontains=search) |
                Q(state_id__icontains=search)
            )
        
        # Filtro por estado
        is_active = self.request.GET.get('is_active', '')
        if is_active != '':
            queryset = queryset.filter(is_active=is_active == 'true')
        
        # Filtro por país
        country = self.request.GET.get('country', '')
        if country:
            queryset = queryset.filter(country_id=country)
        
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'search': self.request.GET.get('search', ''),
            'is_active_filter': self.request.GET.get('is_active', ''),
            'country_filter': self.request.GET.get('country', ''),
            'total_count': self.get_queryset().count(),
            'active_count': self.get_queryset().filter(is_active=True).count(),
            'inactive_count': self.get_queryset().filter(is_active=False).count(),
        })
        return context


class FiscalPositionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear nueva posición fiscal"""
    model = FiscalPosition
    form_class = FiscalPositionForm
    template_name = 'accounting/fiscal_positions/fiscal_position_form.html'
    permission_required = 'accounting.add_fiscalposition'
    success_url = reverse_lazy('accounting:fiscal_position_list')

    def form_valid(self, form):
        """Asignar empresa automáticamente"""
        form.instance.empresa = self.request.user.empresa_activa
        response = super().form_valid(form)
        messages.success(self.request, _('Fiscal position created successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Create Fiscal Position')
        context['submit_text'] = _('Create Fiscal Position')
        return context


class FiscalPositionUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar posición fiscal"""
    model = FiscalPosition
    form_class = FiscalPositionForm
    template_name = 'accounting/fiscal_positions/fiscal_position_form.html'
    permission_required = 'accounting.change_fiscalposition'
    success_url = reverse_lazy('accounting:fiscal_position_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return FiscalPosition.objects.filter(empresa=self.request.user.empresa_activa)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Fiscal position updated successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Edit Fiscal Position')
        context['submit_text'] = _('Update Fiscal Position')
        return context


class FiscalPositionDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar posición fiscal"""
    model = FiscalPosition
    template_name = 'accounting/fiscal_positions/fiscal_position_confirm_delete.html'
    permission_required = 'accounting.delete_fiscalposition'
    success_url = reverse_lazy('accounting:fiscal_position_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return FiscalPosition.objects.filter(empresa=self.request.user.empresa_activa)

    def delete(self, request, *args, **kwargs):
        """Verificar que no tenga mapeos asociados"""
        fiscal_position = self.get_object()
        if fiscal_position.tax_mappings.exists():
            messages.error(
                request, 
                _('Cannot delete fiscal position. It has associated tax mappings.')
            )
            return redirect('accounting:fiscal_position_list')
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Fiscal position deleted successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Confirm Fiscal Position Deletion')
        return context


@tiene_permiso('accounting.change_fiscalposition')
def toggle_fiscal_position_status(request, pk):
    """Activar/desactivar posición fiscal"""
    try:
        fiscal_position = FiscalPosition.objects.get(
            pk=pk, 
            empresa=request.user.empresa_activa
        )
        fiscal_position.is_active = not fiscal_position.is_active
        fiscal_position.save()
        
        status = 'activated' if fiscal_position.is_active else 'deactivated'
        messages.success(
            request, 
            _('Fiscal position {} successfully.').format(status)
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': fiscal_position.is_active,
                'message': _('Fiscal position {} successfully.').format(status)
            })
        
    except FiscalPosition.DoesNotExist:
        messages.error(request, _('Fiscal position not found.'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('Fiscal position not found.')
            })
    
    return redirect('accounting:fiscal_position_list')


@tiene_permiso('accounting.view_fiscalposition')
def fiscal_position_detail(request, pk):
    """Detalle de la posición fiscal"""
    try:
        fiscal_position = FiscalPosition.objects.get(
            pk=pk, 
            empresa=request.user.empresa_activa
        )
        
        # Obtener mapeos de impuestos
        tax_mappings = fiscal_position.tax_mappings.select_related(
            'tax_src_id', 'tax_dest_id'
        ).all()
        
        context = {
            'fiscal_position': fiscal_position,
            'tax_mappings': tax_mappings,
            'tax_mappings_count': tax_mappings.count(),
        }
        
        return render(request, 'accounting/fiscal_positions/fiscal_position_detail.html', context)
        
    except FiscalPosition.DoesNotExist:
        messages.error(request, _('Fiscal position not found.'))
        return redirect('accounting:fiscal_position_list')


# Vistas para mapeos de posición fiscal
class FiscalPositionTaxCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear nuevo mapeo de posición fiscal"""
    model = FiscalPositionTax
    form_class = FiscalPositionTaxForm
    template_name = 'accounting/fiscal_positions/fiscal_position_tax_form.html'
    permission_required = 'accounting.add_fiscalpositiontax'

    def dispatch(self, request, *args, **kwargs):
        """Obtener la posición fiscal"""
        try:
            self.fiscal_position = FiscalPosition.objects.get(
                pk=self.kwargs['fiscal_position_pk'],
                empresa=request.user.empresa_activa
            )
        except FiscalPosition.DoesNotExist:
            messages.error(request, _('Fiscal position not found.'))
            return redirect('accounting:fiscal_position_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Asignar posición fiscal automáticamente"""
        form.instance.fiscal_position = self.fiscal_position
        response = super().form_valid(form)
        messages.success(self.request, _('Tax mapping created successfully.'))
        return response

    def get_success_url(self):
        return reverse_lazy('accounting:fiscal_position_detail', kwargs={'pk': self.fiscal_position.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'fiscal_position': self.fiscal_position,
            'titulo': _('Create Tax Mapping'),
            'submit_text': _('Create Tax Mapping'),
        })
        return context


class FiscalPositionTaxUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar mapeo de posición fiscal"""
    model = FiscalPositionTax
    form_class = FiscalPositionTaxForm
    template_name = 'accounting/fiscal_positions/fiscal_position_tax_form.html'
    permission_required = 'accounting.change_fiscalpositiontax'

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return FiscalPositionTax.objects.filter(
            fiscal_position__empresa=self.request.user.empresa_activa
        )

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Tax mapping updated successfully.'))
        return response

    def get_success_url(self):
        return reverse_lazy('accounting:fiscal_position_detail', kwargs={'pk': self.object.fiscal_position.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'fiscal_position': self.object.fiscal_position,
            'titulo': _('Edit Tax Mapping'),
            'submit_text': _('Update Tax Mapping'),
        })
        return context


class FiscalPositionTaxDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar mapeo de posición fiscal"""
    model = FiscalPositionTax
    template_name = 'accounting/fiscal_positions/fiscal_position_tax_confirm_delete.html'
    permission_required = 'accounting.delete_fiscalpositiontax'

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return FiscalPositionTax.objects.filter(
            fiscal_position__empresa=self.request.user.empresa_activa
        )

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Tax mapping deleted successfully.'))
        return response

    def get_success_url(self):
        return reverse_lazy('accounting:fiscal_position_detail', kwargs={'pk': self.object.fiscal_position.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'fiscal_position': self.object.fiscal_position,
            'titulo': _('Confirm Tax Mapping Deletion'),
        })
        return context 