from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from logistics.services.weather_service import WeatherService
from logistics.services.notification_service import NotificationService
from logistics.models.logistics_config import LogisticsConfig
from logistics.models.notification_config import NotificationConfig
from django.shortcuts import get_object_or_404
from logistics.models import DeliveryRoute, DeliveryStop
import json

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weather_current(request):
    """
    Obtiene el clima actual para una ubicación específica
    """
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    if not lat or not lon:
        return Response(
            {'error': 'Latitude and longitude parameters are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return Response(
            {'error': 'Invalid latitude or longitude values'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar si el clima está habilitado
    config = LogisticsConfig.objects.first()
    if not config or not config.weather_api_key:
        return Response(
            {'error': 'Weather service not configured'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    weather_service = WeatherService()
    weather_data = weather_service.get_current_weather(lat, lon)
    
    if weather_data:
        return Response(weather_data)
    else:
        return Response(
            {'error': 'Unable to fetch weather data'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weather_forecast(request):
    """
    Obtiene el pronóstico del tiempo para una ubicación
    """
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    days = request.GET.get('days', '5')
    
    if not lat or not lon:
        return Response(
            {'error': 'Latitude and longitude parameters are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lat = float(lat)
        lon = float(lon)
        days = int(days)
        if days > 5:
            days = 5
    except ValueError:
        return Response(
            {'error': 'Invalid parameters'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar si el clima está habilitado
    config = LogisticsConfig.objects.first()
    if not config or not config.weather_api_key:
        return Response(
            {'error': 'Weather service not configured'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    weather_service = WeatherService()
    forecast_data = weather_service.get_forecast(lat, lon, days)
    
    if forecast_data:
        return Response(forecast_data)
    else:
        return Response(
            {'error': 'Unable to fetch forecast data'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weather_route_impact(request, route_id):
    """
    Analiza el impacto meteorológico en una ruta específica
    """
    try:
        route = get_object_or_404(DeliveryRoute, id=route_id)
    except ValueError:
        return Response(
            {'error': 'Invalid route ID'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar si el clima está habilitado
    config = LogisticsConfig.objects.first()
    if not config or not config.weather_api_key:
        return Response(
            {'error': 'Weather service not configured'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    # Obtener paradas de la ruta con coordenadas
    route_stops = []
    for stop in route.stops.all():
        if stop.latitude and stop.longitude:
            route_stops.append({
                'address': stop.address,
                'latitude': stop.latitude,
                'longitude': stop.longitude,
                'state': stop.state,
                'client': stop.client.name if stop.client else 'Unknown'
            })
    
    if not route_stops:
        return Response(
            {'error': 'No stops with coordinates found for this route'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    weather_service = WeatherService()
    impact_analysis = weather_service.get_route_weather_impact(route_stops)
    
    # Agregar información de la ruta
    impact_analysis['route'] = {
        'id': route.id,
        'date': route.date,
        'vehicle': route.vehicle.name if route.vehicle else 'Unknown',
        'driver': route.driver.name if route.driver else 'Unknown',
        'state': route.state
    }
    
    return Response(impact_analysis)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weather_delivery_suitability(request):
    """
    Determina si las condiciones meteorológicas son adecuadas para entrega
    """
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    
    if not lat or not lon:
        return Response(
            {'error': 'Latitude and longitude parameters are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        return Response(
            {'error': 'Invalid latitude or longitude values'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar si el clima está habilitado
    config = LogisticsConfig.objects.first()
    if not config or not config.weather_api_key:
        return Response(
            {'error': 'Weather service not configured'}, 
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    weather_service = WeatherService()
    suitability = weather_service.is_weather_suitable_for_delivery(lat, lon)
    
    return Response(suitability)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weather_config_status(request):
    """
    Obtiene el estado de configuración del servicio meteorológico
    """
    config = LogisticsConfig.objects.first()
    
    status_data = {
        'enabled': bool(config and config.weather_api_key),
        'provider': config.weather_provider if config else None,
        'has_api_key': bool(config and config.weather_api_key),
        'last_updated': config.updated_at if config else None
    }
    
    return Response(status_data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_notification(request):
    """
    Envía una notificación de prueba
    """
    event_type = request.data.get('event_type')
    test_data = request.data.get('test_data', {})
    
    if not event_type:
        return Response(
            {'error': 'event_type is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Datos de prueba por defecto
    default_test_data = {
        'delayed': {
            'stop_id': 1,
            'route_id': 1,
            'client_name': 'Cliente de Prueba',
            'address': 'Dirección de Prueba 123',
            'scheduled_time': '2024-01-15T10:00:00Z',
            'current_time': '2024-01-15T10:30:00Z',
            'delay_minutes': 30
        },
        'out_geofence': {
            'stop_id': 1,
            'route_id': 1,
            'client_name': 'Cliente de Prueba',
            'address': 'Dirección de Prueba 123',
            'driver_name': 'Conductor de Prueba',
            'vehicle_plate': 'ABC123',
            'timestamp': '2024-01-15T10:30:00Z'
        },
        'weather_alert': {
            'route_id': 1,
            'driver_name': 'Conductor de Prueba',
            'vehicle_plate': 'ABC123',
            'weather_conditions': 'Lluvia intensa',
            'temperature': 15.5,
            'wind_speed': 25.0,
            'visibility': 2000,
            'recommendations': ['Considerar retrasar la entrega', 'Notificar al conductor'],
            'timestamp': '2024-01-15T10:30:00Z'
        },
        'incident': {
            'stop_id': 1,
            'route_id': 1,
            'client_name': 'Cliente de Prueba',
            'address': 'Dirección de Prueba 123',
            'incident_type': 'Accidente menor',
            'description': 'Vehículo con daños menores en el parachoques',
            'driver_name': 'Conductor de Prueba',
            'timestamp': '2024-01-15T10:30:00Z'
        },
        'completed': {
            'stop_id': 1,
            'route_id': 1,
            'client_name': 'Cliente de Prueba',
            'address': 'Dirección de Prueba 123',
            'delivered_time': '2024-01-15T10:30:00Z',
            'driver_name': 'Conductor de Prueba',
            'timestamp': '2024-01-15T10:30:00Z'
        }
    }
    
    # Usar datos de prueba por defecto si no se proporcionan
    data = test_data or default_test_data.get(event_type, {})
    
    # Enviar notificación de prueba
    notification_service = NotificationService()
    result = notification_service.send_notification(
        event_type=event_type,
        data=data,
        recipients=[request.user.email] if request.user.email else [],
        channels=['email', 'push']
    )
    
    return Response({
        'success': True,
        'message': f'Test notification sent for event: {event_type}',
        'result': result
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_config_list(request):
    """
    Lista las configuraciones de notificaciones del usuario
    """
    configs = NotificationConfig.objects.filter(user=request.user)
    
    config_data = []
    for config in configs:
        config_data.append({
            'id': config.id,
            'role': config.role,
            'events': config.events,
            'channels': config.channels,
            'receive_push': config.receive_push,
            'receive_email': config.receive_email,
            'created_at': config.created_at,
            'updated_at': config.updated_at
        })
    
    return Response({
        'configs': config_data,
        'total': len(config_data)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_config_create(request):
    """
    Crea una nueva configuración de notificaciones
    """
    events = request.data.get('events', [])
    channels = request.data.get('channels', [])
    role = request.data.get('role', '')
    receive_push = request.data.get('receive_push', True)
    receive_email = request.data.get('receive_email', True)
    
    config = NotificationConfig.objects.create(
        user=request.user,
        role=role,
        events=events,
        channels=channels,
        receive_push=receive_push,
        receive_email=receive_email
    )
    
    return Response({
        'success': True,
        'message': 'Notification configuration created successfully',
        'config_id': config.id
    }, status=status.HTTP_201_CREATED)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def notification_config_update(request, config_id):
    """
    Actualiza una configuración de notificaciones existente
    """
    try:
        config = NotificationConfig.objects.get(id=config_id, user=request.user)
    except NotificationConfig.DoesNotExist:
        return Response(
            {'error': 'Configuration not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    events = request.data.get('events', config.events)
    channels = request.data.get('channels', config.channels)
    role = request.data.get('role', config.role)
    receive_push = request.data.get('receive_push', config.receive_push)
    receive_email = request.data.get('receive_email', config.receive_email)
    
    config.events = events
    config.channels = channels
    config.role = role
    config.receive_push = receive_push
    config.receive_email = receive_email
    config.save()
    
    return Response({
        'success': True,
        'message': 'Notification configuration updated successfully'
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def notification_config_delete(request, config_id):
    """
    Elimina una configuración de notificaciones
    """
    try:
        config = NotificationConfig.objects.get(id=config_id, user=request.user)
        config.delete()
        return Response({
            'success': True,
            'message': 'Notification configuration deleted successfully'
        })
    except NotificationConfig.DoesNotExist:
        return Response(
            {'error': 'Configuration not found'}, 
            status=status.HTTP_404_NOT_FOUND
        ) 