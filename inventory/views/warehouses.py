from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Warehouse

class WarehouseListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Warehouse
    template_name = 'inventory/warehouse_list.html'
    context_object_name = 'warehouses'
    permission_required = 'inventory.ver_almacen'
    paginate_by = 15

class WarehouseCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Warehouse
    template_name = 'inventory/warehouse_form.html'
    fields = ['name', 'address', 'is_active']
    permission_required = 'inventory.crear_almacen'
    success_url = reverse_lazy('inventory:warehouse_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Warehouse"
        return context

class WarehouseUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Warehouse
    template_name = 'inventory/warehouse_form.html'
    fields = ['name', 'address', 'is_active']
    permission_required = 'inventory.editar_almacen'
    success_url = reverse_lazy('inventory:warehouse_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Warehouse"
        return context

class WarehouseDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Warehouse
    template_name = 'inventory/warehouse_confirm_delete.html'
    success_url = reverse_lazy('inventory:warehouse_list')
    permission_required = 'inventory.eliminar_almacen'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Warehouse"
        return context 