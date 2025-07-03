from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Location
from core.utils.utils import require_empresa_activa
from django.http import HttpResponseForbidden

class LocationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Location
    template_name = 'inventory/location_list.html'
    context_object_name = 'locations'
    permission_required = 'inventory.view_location'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        empresa = self.request.user.empresa_activa
        branch = self.request.user.branch_activa
        return Location.objects.select_related('warehouse').filter(empresa=empresa, branch=branch).order_by('warehouse__name', 'name')


class LocationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Location
    template_name = 'inventory/location_form.html'
    fields = ['name', 'location_type', 'warehouse', 'parent_location', 'is_active', 'allow_operations']
    permission_required = 'inventory.add_location'
    success_url = reverse_lazy('inventory:location_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Location"
        return context

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        return super().form_valid(form)

class LocationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Location
    template_name = 'inventory/location_form.html'
    fields = ['name', 'location_type', 'warehouse', 'parent_location', 'is_active', 'allow_operations']
    permission_required = 'inventory.change_location'
    success_url = reverse_lazy('inventory:location_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Location"
        return context

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        return super().form_valid(form)

class LocationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Location
    template_name = 'inventory/location_confirm_delete.html'
    success_url = reverse_lazy('inventory:location_list')
    permission_required = 'inventory.delete_location'

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Location"
        return context 