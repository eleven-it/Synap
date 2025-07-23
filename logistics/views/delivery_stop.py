from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from logistics.models import DeliveryStop
from django.utils.translation import gettext_lazy as _

class DeliveryStopListView(ListView):
    model = DeliveryStop
    template_name = 'logistics/delivery_stops/delivery_stop_list.html'
    context_object_name = 'stops'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-scheduled_time')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Delivery Stops')
        return context

class DeliveryStopDetailView(DetailView):
    model = DeliveryStop
    template_name = 'logistics/delivery_stops/delivery_stop_detail.html'
    context_object_name = 'stop'

class DeliveryStopCreateView(CreateView):
    model = DeliveryStop
    template_name = 'logistics/delivery_stops/delivery_stop_form.html'
    fields = ['route', 'sales_order', 'client', 'address', 'scheduled_time', 'state', 'proof_of_delivery']
    success_url = reverse_lazy('logistics:deliverystop_list')

class DeliveryStopUpdateView(UpdateView):
    model = DeliveryStop
    template_name = 'logistics/delivery_stops/delivery_stop_form.html'
    fields = ['route', 'sales_order', 'client', 'address', 'scheduled_time', 'state', 'proof_of_delivery']
    success_url = reverse_lazy('logistics:deliverystop_list')

class DeliveryStopDeleteView(DeleteView):
    model = DeliveryStop
    template_name = 'logistics/delivery_stops/delivery_stop_confirm_delete.html'
    success_url = reverse_lazy('logistics:deliverystop_list') 