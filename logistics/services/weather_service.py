import requests
import logging
from django.core.cache import cache
from django.conf import settings
from logistics.models.logistics_config import LogisticsConfig
from typing import Dict, Optional, List
import json

logger = logging.getLogger(__name__)

class WeatherService:
    """
    Servicio para obtener datos meteorológicos de OpenWeatherMap API.
    Incluye clima actual y pronóstico para optimización de rutas logísticas.
    """
    
    def __init__(self):
        self.config = LogisticsConfig.objects.first()
        self.api_key = self.config.weather_api_key if self.config else None
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.cache_timeout = 1800  # 30 minutos
        
    def get_current_weather(self, lat: float, lon: float) -> Optional[Dict]:
        """
        Obtiene el clima actual para una ubicación específica.
        
        Args:
            lat: Latitud
            lon: Longitud
            
        Returns:
            Dict con datos del clima actual o None si hay error
        """
        if not self.api_key:
            logger.warning("Weather API key not configured")
            return None
            
        cache_key = f"weather_current_{lat}_{lon}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            url = f"{self.base_url}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'es'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            weather_data = {
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed'],
                'wind_direction': data['wind'].get('deg', 0),
                'visibility': data.get('visibility', 0),
                'clouds': data['clouds']['all'],
                'timestamp': data['dt']
            }
            
            cache.set(cache_key, weather_data, self.cache_timeout)
            return weather_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching current weather: {str(e)}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing weather data: {str(e)}")
            return None
    
    def get_forecast(self, lat: float, lon: float, days: int = 5) -> Optional[List[Dict]]:
        """
        Obtiene el pronóstico del tiempo para los próximos días.
        
        Args:
            lat: Latitud
            lon: Longitud
            days: Número de días (máximo 5)
            
        Returns:
            Lista de pronósticos diarios o None si hay error
        """
        if not self.api_key:
            logger.warning("Weather API key not configured")
            return None
            
        cache_key = f"weather_forecast_{lat}_{lon}_{days}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            url = f"{self.base_url}/forecast"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric',
                'lang': 'es',
                'cnt': days * 8  # 8 mediciones por día (cada 3 horas)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            forecast_data = []
            
            for item in data['list']:
                forecast_data.append({
                    'datetime': item['dt'],
                    'temperature': item['main']['temp'],
                    'feels_like': item['main']['feels_like'],
                    'humidity': item['main']['humidity'],
                    'description': item['weather'][0]['description'],
                    'icon': item['weather'][0]['icon'],
                    'wind_speed': item['wind']['speed'],
                    'wind_direction': item['wind'].get('deg', 0),
                    'clouds': item['clouds']['all'],
                    'pop': item.get('pop', 0)  # Probability of precipitation
                })
            
            cache.set(cache_key, forecast_data, self.cache_timeout)
            return forecast_data
            
        except requests.RequestException as e:
            logger.error(f"Error fetching weather forecast: {str(e)}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing forecast data: {str(e)}")
            return None
    
    def get_route_weather_impact(self, route_stops: List[Dict]) -> Dict:
        """
        Analiza el impacto del clima en una ruta de entrega.
        
        Args:
            route_stops: Lista de paradas con coordenadas
            
        Returns:
            Dict con análisis de impacto meteorológico
        """
        if not route_stops:
            return {}
            
        impact_analysis = {
            'total_stops': len(route_stops),
            'weather_checked': 0,
            'adverse_conditions': [],
            'recommendations': []
        }
        
        for stop in route_stops:
            lat = stop.get('latitude')
            lon = stop.get('longitude')
            
            if lat and lon:
                weather = self.get_current_weather(lat, lon)
                if weather:
                    impact_analysis['weather_checked'] += 1
                    
                    # Analizar condiciones adversas
                    if weather['temperature'] < 0:
                        impact_analysis['adverse_conditions'].append({
                            'stop': stop.get('address', 'Unknown'),
                            'condition': 'freezing_temperature',
                            'description': f"Temperatura bajo cero: {weather['temperature']}°C"
                        })
                    
                    if weather['wind_speed'] > 20:
                        impact_analysis['adverse_conditions'].append({
                            'stop': stop.get('address', 'Unknown'),
                            'condition': 'high_wind',
                            'description': f"Viento fuerte: {weather['wind_speed']} m/s"
                        })
                    
                    if weather['visibility'] < 5000:
                        impact_analysis['adverse_conditions'].append({
                            'stop': stop.get('address', 'Unknown'),
                            'condition': 'low_visibility',
                            'description': f"Baja visibilidad: {weather['visibility']}m"
                        })
        
        # Generar recomendaciones
        if impact_analysis['adverse_conditions']:
            impact_analysis['recommendations'].append(
                "Considerar retrasar entregas en áreas con condiciones adversas"
            )
            impact_analysis['recommendations'].append(
                "Notificar a conductores sobre condiciones meteorológicas"
            )
        
        return impact_analysis
    
    def is_weather_suitable_for_delivery(self, lat: float, lon: float) -> Dict:
        """
        Determina si las condiciones meteorológicas son adecuadas para entrega.
        
        Args:
            lat: Latitud
            lon: Longitud
            
        Returns:
            Dict con evaluación de condiciones
        """
        weather = self.get_current_weather(lat, lon)
        if not weather:
            return {'suitable': True, 'reason': 'No weather data available'}
        
        # Criterios de evaluación
        suitable = True
        reasons = []
        
        if weather['temperature'] < -10:
            suitable = False
            reasons.append("Temperatura extremadamente baja")
        
        if weather['wind_speed'] > 25:
            suitable = False
            reasons.append("Viento muy fuerte")
        
        if weather['visibility'] < 1000:
            suitable = False
            reasons.append("Visibilidad muy baja")
        
        if weather['description'].lower() in ['tormenta', 'tormenta eléctrica', 'huracán']:
            suitable = False
            reasons.append("Condiciones meteorológicas extremas")
        
        return {
            'suitable': suitable,
            'reason': '; '.join(reasons) if reasons else "Condiciones adecuadas",
            'weather_data': weather
        } 