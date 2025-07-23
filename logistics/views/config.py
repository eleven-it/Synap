from django.views.generic import UpdateView
from logistics.models.logistics_config import LogisticsConfig
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

class LogisticsConfigView(UpdateView):
    model = LogisticsConfig
    fields = ['weather_api_key', 'weather_provider', 'traccar_api_url', 'traccar_api_token', 'use_traccar', 'use_smartphone_tracking', 'google_maps_api_key']
    template_name = 'logistics/config.html'
    success_url = reverse_lazy('logistics:config')

    def get_object(self, queryset=None):
        obj, created = LogisticsConfig.objects.get_or_create(pk=1)
        return obj 