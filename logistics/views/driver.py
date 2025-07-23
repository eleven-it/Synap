from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from logistics.models import Driver
from django.utils.translation import gettext_lazy as _

class DriverListView(ListView):
    model = Driver
    template_name = 'logistics/drivers/driver_list.html'
    context_object_name = 'drivers'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Drivers')
        return context

class DriverDetailView(DetailView):
    model = Driver
    template_name = 'logistics/drivers/driver_detail.html'
    context_object_name = 'driver'

class DriverCreateView(CreateView):
    model = Driver
    fields = ['company', 'name', 'license_number', 'phone', 'is_active']
    template_name = 'logistics/drivers/driver_form.html'
    success_url = reverse_lazy('logistics:driver_list')

class DriverUpdateView(UpdateView):
    model = Driver
    fields = ['company', 'name', 'license_number', 'phone', 'is_active']
    template_name = 'logistics/drivers/driver_form.html'
    success_url = reverse_lazy('logistics:driver_list')

class DriverDeleteView(DeleteView):
    model = Driver
    template_name = 'logistics/drivers/driver_confirm_delete.html'
    success_url = reverse_lazy('logistics:driver_list') 