from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Location

class LocationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Location
    template_name = 'inventory/location_list.html'
    context_object_name = 'locations'
    permission_required = 'inventory.view_location'
    paginate_by = 20

    def get_queryset(self):
        return Location.objects.select_related('warehouse').order_by('warehouse__name', 'name')


class LocationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Location
    template_name = 'inventory/location_form.html'
    fields = ['name', 'location_type', 'warehouse', 'parent_location', 'is_active', 'allow_operations']
    permission_required = 'inventory.add_location'
    success_url = reverse_lazy('inventory:location_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Location"
        return context

class LocationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Location
    template_name = 'inventory/location_form.html'
    fields = ['name', 'location_type', 'warehouse', 'parent_location', 'is_active', 'allow_operations']
    permission_required = 'inventory.change_location'
    success_url = reverse_lazy('inventory:location_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Location"
        return context

class LocationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Location
    template_name = 'inventory/location_confirm_delete.html'
    success_url = reverse_lazy('inventory:location_list')
    permission_required = 'inventory.delete_location'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Location"
        return context 