from django.views.generic import TemplateView
from logistics.models import DeliveryRoute, DeliveryStop, Vehicle
from logistics.services.tracking_service import TrackingService
from logistics.services.weather_service import WeatherService
from logistics.models.logistics_config import LogisticsConfig
from django.utils import timezone
from django.db.models import Count, Q

class DashboardLogisticsView(TemplateView):
    template_name = 'logistics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # Configuración de clima
        weather_config = LogisticsConfig.objects.first()
        context['weather_enabled'] = bool(weather_config and weather_config.weather_api_key)
        
        # KPIs básicos
        context['routes_today'] = DeliveryRoute.objects.filter(date=today).count()
        context['deliveries_completed'] = DeliveryStop.objects.filter(state='delivered', route__date=today).count()
        context['deliveries_in_progress'] = DeliveryStop.objects.filter(state='in_progress', route__date=today).count()
        context['deliveries_delayed'] = DeliveryStop.objects.filter(state='delayed', route__date=today).count()
        context['deliveries_out_geofence'] = DeliveryStop.objects.filter(state='in_progress', out_geofence=True, route__date=today).count()
        context['vehicles_active'] = Vehicle.objects.filter(is_active=True).count()
        
        # Eficiencia de rutas (entregas/ruta)
        context['route_efficiency'] = DeliveryStop.objects.filter(route__date=today).count() / (DeliveryRoute.objects.filter(date=today).count() or 1)
        
        # Heatmap de entregas (coordenadas de stops entregados)
        stops = DeliveryStop.objects.filter(state='delivered', route__date=today).exclude(latitude=None, longitude=None)
        context['heatmap_points'] = [{'lat': s.latitude, 'lng': s.longitude} for s in stops]
        
        # Incidencias
        context['incidents'] = DeliveryStop.objects.filter(Q(state='delayed') | Q(out_geofence=True), route__date=today).select_related('route', 'client')
        
        # Datos de clima si está habilitado
        if context['weather_enabled']:
            weather_service = WeatherService()
            
            # Clima actual en la sede principal (usar coordenadas por defecto)
            default_lat, default_lon = -34.6037, -58.3816  # Buenos Aires por defecto
            context['current_weather'] = weather_service.get_current_weather(default_lat, default_lon)
            
            # Análisis de impacto meteorológico en rutas del día
            routes_today = DeliveryRoute.objects.filter(date=today)
            weather_impact = {
                'total_routes': routes_today.count(),
                'routes_with_weather_data': 0,
                'adverse_conditions_count': 0,
                'weather_alerts': []
            }
            
            for route in routes_today:
                route_stops = []
                for stop in route.stops.all():
                    if stop.latitude and stop.longitude:
                        route_stops.append({
                            'address': stop.address,
                            'latitude': stop.latitude,
                            'longitude': stop.longitude,
                            'state': stop.state
                        })
                
                if route_stops:
                    impact = weather_service.get_route_weather_impact(route_stops)
                    if impact.get('weather_checked', 0) > 0:
                        weather_impact['routes_with_weather_data'] += 1
                        weather_impact['adverse_conditions_count'] += len(impact.get('adverse_conditions', []))
                        
                        # Agregar alertas meteorológicas
                        for condition in impact.get('adverse_conditions', []):
                            weather_impact['weather_alerts'].append({
                                'route': f"Ruta {route.id}",
                                'condition': condition['condition'],
                                'description': condition['description'],
                                'stop': condition['stop']
                            })
            
            context['weather_impact'] = weather_impact
            
            # Pronóstico para los próximos días
            context['weather_forecast'] = weather_service.get_forecast(default_lat, default_lon, days=3)
        
        return context 