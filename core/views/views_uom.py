from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import UnitOfMeasure
from ..forms import UoMForm
from django.utils.translation import gettext_lazy as _

class UoMListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = UnitOfMeasure
    template_name = 'core/uom/uom_list.html'
    context_object_name = 'uoms'
    permission_required = 'configuracion.uom'
    paginate_by = 20

class UoMCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = UnitOfMeasure
    form_class = UoMForm
    template_name = 'core/uom/uom_form.html'
    permission_required = 'configuracion.uom'
    success_url = reverse_lazy('core:uom_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Create Unit of Measure")
        return context

class UoMUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = UnitOfMeasure
    form_class = UoMForm
    template_name = 'core/uom/uom_form.html'
    permission_required = 'configuracion.uom'
    success_url = reverse_lazy('core:uom_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Edit Unit of Measure")
        return context

class UoMDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = UnitOfMeasure
    template_name = 'core/uom/uom_confirm_delete.html'
    success_url = reverse_lazy('core:uom_list')
    permission_required = 'configuracion.uom'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Confirm Deletion")
        return context 