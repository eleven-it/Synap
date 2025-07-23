from django.utils import timezone
from logistics.models import DeliveryStop, DeliveryRoute, Driver
from logistics.models.driver_location import DriverLocation, DriverLocationHistory
from logistics.services.notification_service import NotificationService
from logistics.services.weather_service import WeatherService
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class TrackingService:
    """
    Servicio para tracking en tiempo real de vehículos y entregas.
    Integra notificaciones automáticas para eventos críticos.
    """
    
    def __init__(self):
        self.notification_service = NotificationService()
        self.weather_service = WeatherService()
    
    def update_driver_location(self, driver: Driver, latitude: float, longitude: float, 
                              accuracy: float = None, source: str = 'smartphone') -> Dict:
        """
        Actualiza la ubicación del conductor y verifica eventos críticos.
        """
        try:
            # Actualizar ubicación actual
            location, created = DriverLocation.objects.update_or_create(
                driver=driver,
                defaults={
                    'latitude': latitude,
                    'longitude': longitude,
                    'accuracy': accuracy,
                    'source': source,
                    'timestamp': timezone.now()
                }
            )
            
            # Guardar en historial
            DriverLocationHistory.objects.create(
                driver=driver,
                latitude=latitude,
                longitude=longitude,
                accuracy=accuracy,
                source=source
            )
            
            # Verificar eventos críticos
            events = self._check_critical_events(driver, latitude, longitude)
            
            return {
                'success': True,
                'location_updated': True,
                'events_detected': events,
                'timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error updating driver location: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_delivery_status(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Verifica el estado de una entrega y envía notificaciones si es necesario.
        """
        try:
            events = []
            
            # Verificar retrasos
            if self._is_delivery_delayed(delivery_stop):
                events.append('delayed')
                self.notification_service.notify_delivery_delayed(delivery_stop)
            
            # Verificar si está fuera de geocerca
            if self._is_out_of_geofence(delivery_stop):
                events.append('out_geofence')
                self.notification_service.notify_out_of_geofence(delivery_stop)
            
            # Verificar clima si está habilitado
            if delivery_stop.latitude and delivery_stop.longitude:
                weather_impact = self.weather_service.is_weather_suitable_for_delivery(
                    delivery_stop.latitude, delivery_stop.longitude
                )
                if not weather_impact['suitable']:
                    events.append('weather_alert')
                    self.notification_service.notify_weather_alert(
                        delivery_stop.route, weather_impact
                    )
            
            return {
                'success': True,
                'events_detected': events,
                'delivery_status': delivery_stop.state,
                'timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error checking delivery status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def complete_delivery(self, delivery_stop: DeliveryStop, proof_file=None, notes: str = None) -> Dict:
        """
        Marca una entrega como completada y envía notificación.
        """
        try:
            delivery_stop.state = 'delivered'
            delivery_stop.delivered_time = timezone.now()
            if proof_file:
                delivery_stop.proof_of_delivery = proof_file
            if notes:
                delivery_stop.notes = notes
            delivery_stop.save()
            
            # Enviar notificación de entrega completada
            self.notification_service.notify_delivery_completed(delivery_stop)
            
            return {
                'success': True,
                'delivery_completed': True,
                'delivered_time': delivery_stop.delivered_time,
                'timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error completing delivery: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def report_incident(self, delivery_stop: DeliveryStop, incident_type: str, 
                       description: str, location: str = None) -> Dict:
        """
        Reporta un incidente durante la entrega y envía notificación.
        """
        try:
            # Crear evento de incidente
            from logistics.models import DeliveryEvent
            event = DeliveryEvent.objects.create(
                stop=delivery_stop,
                event_type='incident',
                location=location or delivery_stop.address,
                description=description
            )
            
            # Enviar notificación de incidente
            self.notification_service.notify_incident(
                delivery_stop, incident_type, description
            )
            
            return {
                'success': True,
                'incident_reported': True,
                'event_id': event.id,
                'timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error reporting incident: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_route_progress(self, route: DeliveryRoute) -> Dict:
        """
        Obtiene el progreso de una ruta con información detallada.
        """
        try:
            stops = route.stops.all()
            total_stops = stops.count()
            completed_stops = stops.filter(state='delivered').count()
            delayed_stops = stops.filter(state='delayed').count()
            in_progress_stops = stops.filter(state='in_progress').count()
            
            # Verificar alertas meteorológicas para la ruta
            weather_alerts = []
            if self.weather_service:
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
                    weather_impact = self.weather_service.get_route_weather_impact(route_stops_data)
                    if weather_impact.get('adverse_conditions'):
                        weather_alerts = weather_impact['adverse_conditions']
            
            return {
                'success': True,
                'route_id': route.id,
                'total_stops': total_stops,
                'completed_stops': completed_stops,
                'delayed_stops': delayed_stops,
                'in_progress_stops': in_progress_stops,
                'completion_percentage': (completed_stops / total_stops * 100) if total_stops > 0 else 0,
                'weather_alerts': weather_alerts,
                'timestamp': timezone.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting route progress: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _check_critical_events(self, driver: Driver, latitude: float, longitude: float) -> List[str]:
        """
        Verifica eventos críticos basados en la ubicación del conductor.
        """
        events = []
        
        # Verificar entregas activas del conductor
        active_routes = DeliveryRoute.objects.filter(
            driver=driver,
            state='in_transit',
            date=timezone.now().date()
        )
        
        for route in active_routes:
            for stop in route.stops.filter(state='in_progress'):
                # Verificar retrasos
                if self._is_delivery_delayed(stop):
                    events.append('delayed')
                
                # Verificar geocerca
                if self._is_out_of_geofence(stop):
                    events.append('out_geofence')
        
        return events
    
    def _is_delivery_delayed(self, delivery_stop: DeliveryStop) -> bool:
        """
        Verifica si una entrega está retrasada.
        """
        if delivery_stop.state != 'in_progress':
            return False
        
        # Considerar retrasado si pasó más de 15 minutos de la hora programada
        delay_threshold = timezone.timedelta(minutes=15)
        return timezone.now() > delivery_stop.scheduled_time + delay_threshold
    
    def _is_out_of_geofence(self, delivery_stop: DeliveryStop) -> bool:
        """
        Verifica si el conductor está fuera de la geocerca de la entrega.
        """
        if not delivery_stop.latitude or not delivery_stop.longitude:
            return False
        
        # Obtener ubicación actual del conductor
        try:
            driver_location = DriverLocation.objects.get(driver=delivery_stop.route.driver)
        except DriverLocation.DoesNotExist:
            return False
        
        # Calcular distancia (simplificado - en producción usar geopy)
        from math import sqrt
        lat_diff = driver_location.latitude - delivery_stop.latitude
        lon_diff = driver_location.longitude - delivery_stop.longitude
        distance = sqrt(lat_diff**2 + lon_diff**2) * 111000  # Aproximación en metros
        
        # Considerar fuera de geocerca si está a más de 500 metros
        geofence_radius = 500  # metros
        return distance > geofence_radius 