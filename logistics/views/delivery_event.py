from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from logistics.models import DeliveryEvent
from django.utils.translation import gettext_lazy as _

class DeliveryEventListView(ListView):
    model = DeliveryEvent
    template_name = 'logistics/delivery_events/delivery_event_list.html'
    context_object_name = 'events'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Delivery Events')
        return context

class DeliveryEventDetailView(DetailView):
    model = DeliveryEvent
    template_name = 'logistics/delivery_events/delivery_event_detail.html'
    context_object_name = 'event'

class DeliveryEventCreateView(CreateView):
    model = DeliveryEvent
    template_name = 'logistics/delivery_events/delivery_event_form.html'
    fields = ['stop', 'timestamp', 'event_type', 'location', 'description']
    success_url = reverse_lazy('logistics:deliveryevent_list')

class DeliveryEventUpdateView(UpdateView):
    model = DeliveryEvent
    template_name = 'logistics/delivery_events/delivery_event_form.html'
    fields = ['stop', 'timestamp', 'event_type', 'location', 'description']
    success_url = reverse_lazy('logistics:deliveryevent_list')

class DeliveryEventDeleteView(DeleteView):
    model = DeliveryEvent
    template_name = 'logistics/delivery_events/delivery_event_confirm_delete.html'
    success_url = reverse_lazy('logistics:deliveryevent_list') 