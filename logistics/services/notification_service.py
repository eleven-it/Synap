import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from logistics.models.notification_config import NotificationConfig
from logistics.models import DeliveryStop, DeliveryRoute, Driver
from typing import List, Dict, Optional
import json
import requests

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Servicio para enviar notificaciones push y email para eventos críticos de logística.
    Soporta múltiples canales y configuración personalizada por usuario.
    """
    
    def __init__(self):
        self.email_enabled = hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST
        self.push_enabled = hasattr(settings, 'FIREBASE_CREDENTIALS_PATH')
    
    def send_notification(self, event_type: str, data: Dict, recipients: List[str] = None, 
                         channels: List[str] = None) -> Dict:
        """
        Envía notificación por los canales especificados.
        
        Args:
            event_type: Tipo de evento (delayed, out_geofence, incident, completed, weather_alert)
            data: Datos del evento
            recipients: Lista de usuarios/roles a notificar
            channels: Canales a usar (email, push, sms)
            
        Returns:
            Dict con resultados del envío
        """
        if not recipients:
            recipients = self._get_default_recipients(event_type)
        
        if not channels:
            channels = ['email', 'push']
        
        results = {
            'event_type': event_type,
            'timestamp': timezone.now(),
            'recipients': recipients,
            'channels': channels,
            'results': {}
        }
        
        # Enviar por cada canal
        for channel in channels:
            if channel == 'email' and self.email_enabled:
                results['results']['email'] = self._send_email_notification(event_type, data, recipients)
            elif channel == 'push' and self.push_enabled:
                results['results']['push'] = self._send_push_notification(event_type, data, recipients)
            elif channel == 'sms':
                results['results']['sms'] = self._send_sms_notification(event_type, data, recipients)
        
        # Log del evento
        logger.info(f"Notification sent: {event_type} to {len(recipients)} recipients via {channels}")
        
        return results
    
    def notify_delivery_delayed(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Notifica retraso en entrega.
        """
        data = {
            'stop_id': delivery_stop.id,
            'route_id': delivery_stop.route.id,
            'client_name': delivery_stop.client.name if delivery_stop.client else 'Unknown',
            'address': delivery_stop.address,
            'scheduled_time': delivery_stop.scheduled_time,
            'current_time': timezone.now(),
            'delay_minutes': int((timezone.now() - delivery_stop.scheduled_time).total_seconds() / 60)
        }
        
        return self.send_notification('delayed', data)
    
    def notify_out_of_geofence(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Notifica que un vehículo está fuera de la geocerca.
        """
        data = {
            'stop_id': delivery_stop.id,
            'route_id': delivery_stop.route.id,
            'client_name': delivery_stop.client.name if delivery_stop.client else 'Unknown',
            'address': delivery_stop.address,
            'driver_name': delivery_stop.route.driver.name if delivery_stop.route.driver else 'Unknown',
            'vehicle_plate': delivery_stop.route.vehicle.license_plate if delivery_stop.route.vehicle else 'Unknown',
            'timestamp': timezone.now()
        }
        
        return self.send_notification('out_geofence', data)
    
    def notify_weather_alert(self, route: DeliveryRoute, weather_data: Dict) -> Dict:
        """
        Notifica alertas meteorológicas que afectan una ruta.
        """
        data = {
            'route_id': route.id,
            'driver_name': route.driver.name if route.driver else 'Unknown',
            'vehicle_plate': route.vehicle.license_plate if route.vehicle else 'Unknown',
            'weather_conditions': weather_data.get('description', 'Unknown'),
            'temperature': weather_data.get('temperature', 0),
            'wind_speed': weather_data.get('wind_speed', 0),
            'visibility': weather_data.get('visibility', 0),
            'recommendations': weather_data.get('recommendations', []),
            'timestamp': timezone.now()
        }
        
        return self.send_notification('weather_alert', data)
    
    def notify_incident(self, delivery_stop: DeliveryStop, incident_type: str, description: str) -> Dict:
        """
        Notifica incidentes durante la entrega.
        """
        data = {
            'stop_id': delivery_stop.id,
            'route_id': delivery_stop.route.id,
            'client_name': delivery_stop.client.name if delivery_stop.client else 'Unknown',
            'address': delivery_stop.address,
            'incident_type': incident_type,
            'description': description,
            'driver_name': delivery_stop.route.driver.name if delivery_stop.route.driver else 'Unknown',
            'timestamp': timezone.now()
        }
        
        return self.send_notification('incident', data)
    
    def notify_delivery_completed(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Notifica entrega completada exitosamente.
        """
        data = {
            'stop_id': delivery_stop.id,
            'route_id': delivery_stop.route.id,
            'client_name': delivery_stop.client.name if delivery_stop.client else 'Unknown',
            'address': delivery_stop.address,
            'delivered_time': delivery_stop.delivered_time or timezone.now(),
            'driver_name': delivery_stop.route.driver.name if delivery_stop.route.driver else 'Unknown',
            'timestamp': timezone.now()
        }
        
        return self.send_notification('completed', data)
    
    def _get_default_recipients(self, event_type: str) -> List[str]:
        """
        Obtiene los destinatarios por defecto según el tipo de evento.
        """
        # Configuraciones de notificación por tipo de evento
        event_configs = {
            'delayed': ['logistics_manager', 'dispatcher'],
            'out_geofence': ['logistics_manager', 'dispatcher', 'driver'],
            'incident': ['logistics_manager', 'dispatcher'],
            'weather_alert': ['logistics_manager', 'dispatcher', 'driver'],
            'completed': ['logistics_manager', 'dispatcher']
        }
        
        roles = event_configs.get(event_type, ['logistics_manager'])
        
        # Obtener usuarios con configuración para estos roles
        recipients = []
        configs = NotificationConfig.objects.filter(
            role__in=roles,
            events__contains=[event_type]
        )
        
        for config in configs:
            if config.user:
                recipients.append(config.user.email)
            elif config.role:
                # Buscar usuarios con ese rol
                from django.contrib.auth import get_user_model
                User = get_user_model()
                users = User.objects.filter(groups__name=config.role)
                recipients.extend([user.email for user in users])
        
        return list(set(recipients))  # Eliminar duplicados
    
    def _send_email_notification(self, event_type: str, data: Dict, recipients: List[str]) -> Dict:
        """
        Envía notificación por email.
        """
        try:
            # Obtener template según tipo de evento
            template_name = f'logistics/emails/{event_type}_notification.html'
            
            # Renderizar contenido del email
            context = {
                'event_type': event_type,
                'data': data,
                'timestamp': timezone.now(),
                'company_name': getattr(settings, 'COMPANY_NAME', 'Synap')
            }
            
            html_content = render_to_string(template_name, context)
            text_content = self._html_to_text(html_content)
            
            # Enviar email
            subject = self._get_email_subject(event_type, data)
            
            send_mail(
                subject=subject,
                message=text_content,
                html_message=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False
            )
            
            return {
                'success': True,
                'recipients_count': len(recipients),
                'message': 'Email sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to send email'
            }
    
    def _send_push_notification(self, event_type: str, data: Dict, recipients: List[str]) -> Dict:
        """
        Envía notificación push usando Firebase Cloud Messaging.
        """
        try:
            if not self.push_enabled:
                return {
                    'success': False,
                    'error': 'Push notifications not configured',
                    'message': 'Firebase not configured'
                }
            
            # Obtener tokens FCM de los usuarios
            tokens = self._get_fcm_tokens(recipients)
            
            if not tokens:
                return {
                    'success': False,
                    'error': 'No FCM tokens found',
                    'message': 'No push tokens available'
                }
            
            # Preparar mensaje FCM
            message = {
                'notification': {
                    'title': self._get_push_title(event_type, data),
                    'body': self._get_push_body(event_type, data)
                },
                'data': {
                    'event_type': event_type,
                    'route_id': str(data.get('route_id', '')),
                    'stop_id': str(data.get('stop_id', '')),
                    'timestamp': str(timezone.now().timestamp())
                },
                'tokens': tokens
            }
            
            # Enviar a Firebase
            response = self._send_fcm_message(message)
            
            return {
                'success': True,
                'recipients_count': len(tokens),
                'fcm_response': response,
                'message': 'Push notification sent successfully'
            }
            
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to send push notification'
            }
    
    def _send_sms_notification(self, event_type: str, data: Dict, recipients: List[str]) -> Dict:
        """
        Envía notificación por SMS (placeholder para implementación futura).
        """
        # TODO: Implementar integración con servicio SMS
        return {
            'success': False,
            'error': 'SMS notifications not implemented',
            'message': 'SMS service not available'
        }
    
    def _get_email_subject(self, event_type: str, data: Dict) -> str:
        """
        Genera el asunto del email según el tipo de evento.
        """
        subjects = {
            'delayed': f'🚨 Entrega Retrasada - Cliente: {data.get("client_name", "Unknown")}',
            'out_geofence': f'📍 Vehículo Fuera de Geocerca - {data.get("driver_name", "Unknown")}',
            'incident': f'⚠️ Incidente Reportado - {data.get("incident_type", "Unknown")}',
            'weather_alert': f'🌦️ Alerta Meteorológica - Ruta {data.get("route_id", "Unknown")}',
            'completed': f'✅ Entrega Completada - Cliente: {data.get("client_name", "Unknown")}'
        }
        
        return subjects.get(event_type, f'Notificación de Logística - {event_type}')
    
    def _get_push_title(self, event_type: str, data: Dict) -> str:
        """
        Genera el título de la notificación push.
        """
        titles = {
            'delayed': '🚨 Entrega Retrasada',
            'out_geofence': '📍 Fuera de Geocerca',
            'incident': '⚠️ Incidente Reportado',
            'weather_alert': '🌦️ Alerta Meteorológica',
            'completed': '✅ Entrega Completada'
        }
        
        return titles.get(event_type, 'Notificación de Logística')
    
    def _get_push_body(self, event_type: str, data: Dict) -> str:
        """
        Genera el cuerpo de la notificación push.
        """
        if event_type == 'delayed':
            return f"Cliente: {data.get('client_name', 'Unknown')} - Retraso: {data.get('delay_minutes', 0)} min"
        elif event_type == 'out_geofence':
            return f"Conductor: {data.get('driver_name', 'Unknown')} - {data.get('address', 'Unknown')}"
        elif event_type == 'weather_alert':
            return f"Ruta {data.get('route_id', 'Unknown')} - {data.get('weather_conditions', 'Unknown')}"
        elif event_type == 'incident':
            return f"{data.get('incident_type', 'Unknown')} - {data.get('client_name', 'Unknown')}"
        elif event_type == 'completed':
            return f"Cliente: {data.get('client_name', 'Unknown')} - Entregado exitosamente"
        
        return f"Evento: {event_type}"
    
    def _get_fcm_tokens(self, recipients: List[str]) -> List[str]:
        """
        Obtiene los tokens FCM de los usuarios.
        """
        # TODO: Implementar obtención de tokens FCM desde base de datos
        # Por ahora retorna lista vacía
        return []
    
    def _send_fcm_message(self, message: Dict) -> Dict:
        """
        Envía mensaje a Firebase Cloud Messaging.
        """
        # TODO: Implementar envío real a FCM
        # Por ahora simula el envío
        logger.info(f"FCM message would be sent: {json.dumps(message, indent=2)}")
        return {'success': True, 'message_id': 'simulated_message_id'}
    
    def _html_to_text(self, html_content: str) -> str:
        """
        Convierte HTML a texto plano para emails.
        """
        # Implementación básica - remover tags HTML
        import re
        text = re.sub(r'<[^>]+>', '', html_content)
        text = re.sub(r'\s+', ' ', text)
        return text.strip() 