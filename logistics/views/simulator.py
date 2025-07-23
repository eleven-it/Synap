from django.views.generic import TemplateView
from logistics.models import DeliveryRoute, DeliveryStop
from logistics.services.weather_service import WeatherService
from logistics.models.logistics_config import LogisticsConfig
from django.shortcuts import get_object_or_404

class LogisticsSimulatorView(TemplateView):
    template_name = 'logistics/simulator.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Configuración de clima
        weather_config = LogisticsConfig.objects.first()
        context['weather_enabled'] = bool(weather_config and weather_config.weather_api_key)
        
        # Lista de rutas disponibles para el selector
        context['routes'] = DeliveryRoute.objects.order_by('-date')[:20]
        
        route_id = self.request.GET.get('route_id')
        if route_id:
            route = get_object_or_404(DeliveryRoute, id=route_id)
            stops = route.stops.all().order_by('sequence')
            
            context['route'] = route
            context['stops'] = stops
            context['selected_route_id'] = int(route_id)
            
            # Datos de clima para cada parada si está habilitado
            if context['weather_enabled']:
                weather_service = WeatherService()
                stops_with_weather = []
                
                for stop in stops:
                    stop_data = {
                        'stop': stop,
                        'weather': None,
                        'weather_suitable': None
                    }
                    
                    if stop.latitude and stop.longitude:
                        # Clima actual en la parada
                        weather = weather_service.get_current_weather(stop.latitude, stop.longitude)
                        if weather:
                            stop_data['weather'] = weather
                            stop_data['weather_suitable'] = weather_service.is_weather_suitable_for_delivery(
                                stop.latitude, stop.longitude
                            )
                    
                    stops_with_weather.append(stop_data)
                
                context['stops_with_weather'] = stops_with_weather
                
                # Análisis de impacto meteorológico en la ruta
                route_stops_data = []
                for stop in stops:
                    if stop.latitude and stop.longitude:
                        route_stops_data.append({
                            'address': stop.address,
                            'latitude': stop.latitude,
                            'longitude': stop.longitude,
                            'state': stop.state
                        })
                
                if route_stops_data:
                    context['weather_impact'] = weather_service.get_route_weather_impact(route_stops_data)
        
        return context 