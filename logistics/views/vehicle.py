from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from logistics.models import Vehicle
from django.utils.translation import gettext_lazy as _

class VehicleListView(ListView):
    model = Vehicle
    template_name = 'logistics/vehicles/vehicle_list.html'
    context_object_name = 'vehicles'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Vehicles')
        return context

class VehicleDetailView(DetailView):
    model = Vehicle
    template_name = 'logistics/vehicles/vehicle_detail.html'
    context_object_name = 'vehicle'

class VehicleCreateView(CreateView):
    model = Vehicle
    fields = ['company', 'license_plate', 'type', 'capacity_kg', 'brand', 'model', 'is_active']
    template_name = 'logistics/vehicles/vehicle_form.html'
    success_url = reverse_lazy('logistics:vehicle_list')

class VehicleUpdateView(UpdateView):
    model = Vehicle
    fields = ['company', 'license_plate', 'type', 'capacity_kg', 'brand', 'model', 'is_active']
    template_name = 'logistics/vehicles/vehicle_form.html'
    success_url = reverse_lazy('logistics:vehicle_list')

class VehicleDeleteView(DeleteView):
    model = Vehicle
    template_name = 'logistics/vehicles/vehicle_confirm_delete.html'
    success_url = reverse_lazy('logistics:vehicle_list') 