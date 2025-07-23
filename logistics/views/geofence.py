from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from logistics.models.geofence import Geofence
from django.utils.translation import gettext as _

class GeofenceCreateView(CreateView):
    model = Geofence
    fields = ['name', 'description', 'center_lat', 'center_lng', 'radius_m', 'polygon', 'route', 'vehicle', 'client_id', 'active']
    template_name = 'logistics/geofence_form.html'
    success_url = reverse_lazy('logistics:tracking_realtime')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['google_maps_api_key'] = self.request.GET.get('google_maps_api_key', '')
        return context

class GeofenceUpdateView(UpdateView):
    model = Geofence
    fields = ['name', 'description', 'center_lat', 'center_lng', 'radius_m', 'polygon', 'route', 'vehicle', 'client_id', 'active']
    template_name = 'logistics/geofence_form.html'
    success_url = reverse_lazy('logistics:tracking_realtime')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['google_maps_api_key'] = self.request.GET.get('google_maps_api_key', '')
        return context 