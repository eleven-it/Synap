from django.views.generic import TemplateView
from logistics.models import Vehicle
from logistics.services.tracking_service import TrackingService
from logistics.models.tracking_config import TrackingConfig
from django.utils.translation import gettext as _
from django.http import JsonResponse

class RealTimeTrackingView(TemplateView):
    template_name = 'logistics/tracking_realtime.html'

    def get(self, request, *args, **kwargs):
        if request.GET.get('ajax') == '1':
            config = TrackingConfig.objects.first()
            service = TrackingService()
            vehicles = Vehicle.objects.filter(is_active=True)
            vehicle_locations = []
            for v in vehicles:
                loc = service.get_vehicle_location(v)
                if loc:
                    vehicle_locations.append({
                        'id': v.id,
                        'name': str(v),
                        'lat': loc['lat'],
                        'lng': loc['lng'],
                        'driver': str(v.driver_set.first()) if v.driver_set.exists() else '',
                        'timestamp': str(loc.get('timestamp')) if loc.get('timestamp') else '',
                    })
            # Geofences activos
            from logistics.models.geofence import Geofence
            geofences = list(Geofence.objects.filter(active=True).values('id','center_lat','center_lng','radius_m','polygon'))
            return JsonResponse({'vehicle_locations': vehicle_locations, 'geofences': geofences})
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = TrackingConfig.objects.first()
        service = TrackingService()
        vehicles = Vehicle.objects.filter(is_active=True)
        vehicle_locations = []
        vehicle_histories = {}
        vehicle_alerts = {}
        for v in vehicles:
            loc = service.get_vehicle_location(v)
            if loc:
                vehicle_locations.append({
                    'id': v.id,
                    'name': str(v),
                    'lat': loc['lat'],
                    'lng': loc['lng'],
                    'driver': str(v.driver_set.first()) if v.driver_set.exists() else '',
                    'timestamp': loc.get('timestamp'),
                })
            vehicle_histories[v.id] = service.get_vehicle_history(v, limit=30)
            vehicle_alerts[v.id] = service.get_alerts(v)
        # Geofences activos
        from logistics.models.geofence import Geofence
        context['geofences'] = list(Geofence.objects.filter(active=True).values('id','center_lat','center_lng','radius_m','polygon'))
        context['vehicle_locations'] = vehicle_locations
        context['vehicle_histories'] = vehicle_histories
        context['vehicle_alerts'] = vehicle_alerts
        context['use_google_maps'] = config and config.use_smartphone_tracking
        context['google_maps_api_key'] = config.google_maps_api_key if config else ''
        context['use_traccar'] = config and config.use_traccar
        return context 