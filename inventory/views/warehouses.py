from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Warehouse
from core.utils.utils import require_empresa_activa
from django.http import HttpResponseForbidden

class WarehouseListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Warehouse
    template_name = 'inventory/warehouse_list.html'
    context_object_name = 'warehouses'
    permission_required = 'inventory.ver_almacen'
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        empresa = self.request.user.empresa_activa
        branch = self.request.user.branch_activa
        return Warehouse.objects.filter(empresa=empresa, branch=branch)

class WarehouseCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Warehouse
    template_name = 'inventory/warehouse_form.html'
    fields = ['name', 'address', 'is_active']
    permission_required = 'inventory.crear_almacen'
    success_url = reverse_lazy('inventory:warehouse_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Warehouse"
        return context

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        return super().form_valid(form)

class WarehouseUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Warehouse
    template_name = 'inventory/warehouse_form.html'
    fields = ['name', 'address', 'is_active']
    permission_required = 'inventory.editar_almacen'
    success_url = reverse_lazy('inventory:warehouse_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Warehouse"
        return context

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        return super().form_valid(form)

class WarehouseDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Warehouse
    template_name = 'inventory/warehouse_confirm_delete.html'
    success_url = reverse_lazy('inventory:warehouse_list')
    permission_required = 'inventory.eliminar_almacen'

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Warehouse"
        return context 