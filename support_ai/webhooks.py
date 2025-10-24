import os
import json
import logging
import requests
from typing import Dict, Any, Optional
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from .models import SupportTicket, Conversation, SupportConfiguration
from .agents.supervisor import SupervisorAgent

logger = logging.getLogger(__name__)

class EmailWebhookHandler:
    """Maneja webhooks de servicios de email (Mailgun, SendGrid)"""
    
    def __init__(self):
        self.supervisor = SupervisorAgent()
    
    def process_mailgun_webhook(self, request) -> Dict[str, Any]:
        """Procesa webhook de Mailgun"""
        try:
            # Verificar autenticación
            if not self._verify_mailgun_signature(request):
                return {'error': 'Invalid signature'}
            
            # Extraer datos del email
            email_data = self._extract_mailgun_data(request.POST)
            
            # Crear ticket desde email
            ticket = self._create_ticket_from_email(email_data)
            
            # Procesar con supervisor
            response = self.supervisor.process_message(
                ticket=ticket,
                message=email_data['body'],
                attachments=email_data.get('attachments', [])
            )
            
            # Guardar respuesta
            self._save_ai_response(ticket, response)
            
            # Enviar respuesta por email
            self._send_email_response(email_data['from'], response['message'], ticket)
            
            return {'success': True, 'ticket_id': ticket.id}
            
        except Exception as e:
            logger.error(f"Error processing Mailgun webhook: {e}")
            return {'error': str(e)}
    
    def process_sendgrid_webhook(self, request) -> Dict[str, Any]:
        """Procesa webhook de SendGrid"""
        try:
            # Verificar autenticación
            if not self._verify_sendgrid_signature(request):
                return {'error': 'Invalid signature'}
            
            # Extraer datos del email
            email_data = self._extract_sendgrid_data(request.body)
            
            # Crear ticket desde email
            ticket = self._create_ticket_from_email(email_data)
            
            # Procesar con supervisor
            response = self.supervisor.process_message(
                ticket=ticket,
                message=email_data['body'],
                attachments=email_data.get('attachments', [])
            )
            
            # Guardar respuesta
            self._save_ai_response(ticket, response)
            
            # Enviar respuesta por email
            self._send_email_response(email_data['from'], response['message'], ticket)
            
            return {'success': True, 'ticket_id': ticket.id}
            
        except Exception as e:
            logger.error(f"Error processing SendGrid webhook: {e}")
            return {'error': str(e)}
    
    def _verify_mailgun_signature(self, request) -> bool:
        """Verifica la firma de Mailgun"""
        try:
            timestamp = request.POST.get('timestamp')
            token = request.POST.get('token')
            signature = request.POST.get('signature')
            
            if not all([timestamp, token, signature]):
                return False
            
            # Implementar verificación de firma
            # En producción, usar la clave API de Mailgun
            api_key = getattr(settings, 'MAILGUN_API_KEY', '')
            if not api_key:
                logger.warning("MAILGUN_API_KEY not configured")
                return True  # Permitir en desarrollo
            
            # Verificación real de firma
            import hmac
            import hashlib
            
            expected_signature = hmac.new(
                api_key.encode(),
                f"{timestamp}{token}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying Mailgun signature: {e}")
            return False
    
    def _verify_sendgrid_signature(self, request) -> bool:
        """Verifica la firma de SendGrid"""
        try:
            # SendGrid usa headers específicos para verificación
            # Implementar según documentación de SendGrid
            return True  # Simplificado para desarrollo
            
        except Exception as e:
            logger.error(f"Error verifying SendGrid signature: {e}")
            return False
    
    def _extract_mailgun_data(self, post_data) -> Dict[str, Any]:
        """Extrae datos del webhook de Mailgun"""
        return {
            'from': post_data.get('from', ''),
            'to': post_data.get('to', ''),
            'subject': post_data.get('subject', ''),
            'body': post_data.get('body-plain', ''),
            'html_body': post_data.get('body-html', ''),
            'message_id': post_data.get('message-id', ''),
            'timestamp': post_data.get('timestamp', ''),
            'attachments': self._extract_attachments(post_data)
        }
    
    def _extract_sendgrid_data(self, request_body) -> Dict[str, Any]:
        """Extrae datos del webhook de SendGrid"""
        try:
            data = json.loads(request_body)
            # Implementar según formato de SendGrid
            return {
                'from': data.get('from', ''),
                'to': data.get('to', ''),
                'subject': data.get('subject', ''),
                'body': data.get('text', ''),
                'html_body': data.get('html', ''),
                'message_id': data.get('message-id', ''),
                'timestamp': data.get('timestamp', ''),
                'attachments': []
            }
        except Exception as e:
            logger.error(f"Error parsing SendGrid data: {e}")
            return {}
    
    def _extract_attachments(self, post_data) -> list:
        """Extrae información de archivos adjuntos"""
        attachments = []
        # Implementar extracción de archivos adjuntos según el servicio
        return attachments
    
    def _create_ticket_from_email(self, email_data: Dict[str, Any]) -> SupportTicket:
        """Crea un ticket desde datos de email"""
        try:
            # Buscar configuración de soporte
            config = SupportConfiguration.objects.first()
            
            # Crear ticket
            ticket = SupportTicket.objects.create(
                subject=email_data['subject'] or 'Consulta por email',
                description=email_data['body'],
                channel='email',
                priority='medium',
                status='open',
                customer_email=email_data['from'],
                # Otros campos según el modelo
            )
            
            # Guardar mensaje inicial
            Conversation.objects.create(
                ticket=ticket,
                message_type='user',
                content=email_data['body'],
                sender_email=email_data['from']
            )
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error creating ticket from email: {e}")
            raise
    
    def _save_ai_response(self, ticket: SupportTicket, response: Dict[str, Any]):
        """Guarda la respuesta de la IA"""
        try:
            Conversation.objects.create(
                ticket=ticket,
                message_type='ai',
                content=response['message'],
                ai_agent_used=response.get('agent_used', 'supervisor'),
                confidence=response.get('confidence', 0.0)
            )
        except Exception as e:
            logger.error(f"Error saving AI response: {e}")
    
    def _send_email_response(self, to_email: str, message: str, ticket: SupportTicket):
        """Envía respuesta por email"""
        try:
            # Implementar envío de email usando Django Email
            from django.core.mail import send_mail
            
            subject = f"Re: {ticket.subject} - Ticket #{ticket.ticket_number}"
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@synap.com'),
                recipient_list=[to_email],
                fail_silently=False,
            )
            
        except Exception as e:
            logger.error(f"Error sending email response: {e}")


class WhatsAppWebhookHandler:
    """Maneja webhooks de WhatsApp (Twilio, Meta)"""
    
    def __init__(self):
        self.supervisor = SupervisorAgent()
    
    def process_twilio_webhook(self, request) -> Dict[str, Any]:
        """Procesa webhook de Twilio WhatsApp"""
        try:
            # Verificar autenticación
            if not self._verify_twilio_signature(request):
                return {'error': 'Invalid signature'}
            
            # Extraer datos del mensaje
            message_data = self._extract_twilio_data(request.POST)
            
            # Crear o actualizar ticket
            ticket = self._get_or_create_ticket_from_whatsapp(message_data)
            
            # Procesar con supervisor
            response = self.supervisor.process_message(
                ticket=ticket,
                message=message_data['body'],
                attachments=message_data.get('attachments', [])
            )
            
            # Guardar respuesta
            self._save_ai_response(ticket, response)
            
            # Enviar respuesta por WhatsApp
            self._send_whatsapp_response(message_data['from'], response['message'], ticket)
            
            return {'success': True, 'ticket_id': ticket.id}
            
        except Exception as e:
            logger.error(f"Error processing Twilio webhook: {e}")
            return {'error': str(e)}
    
    def process_meta_webhook(self, request) -> Dict[str, Any]:
        """Procesa webhook de Meta WhatsApp"""
        try:
            # Verificar autenticación
            if not self._verify_meta_signature(request):
                return {'error': 'Invalid signature'}
            
            # Extraer datos del mensaje
            message_data = self._extract_meta_data(request.body)
            
            # Crear o actualizar ticket
            ticket = self._get_or_create_ticket_from_whatsapp(message_data)
            
            # Procesar con supervisor
            response = self.supervisor.process_message(
                ticket=ticket,
                message=message_data['body'],
                attachments=message_data.get('attachments', [])
            )
            
            # Guardar respuesta
            self._save_ai_response(ticket, response)
            
            # Enviar respuesta por WhatsApp
            self._send_whatsapp_response(message_data['from'], response['message'], ticket)
            
            return {'success': True, 'ticket_id': ticket.id}
            
        except Exception as e:
            logger.error(f"Error processing Meta webhook: {e}")
            return {'error': str(e)}
    
    def _verify_twilio_signature(self, request) -> bool:
        """Verifica la firma de Twilio"""
        try:
            # Implementar verificación de firma de Twilio
            return True  # Simplificado para desarrollo
            
        except Exception as e:
            logger.error(f"Error verifying Twilio signature: {e}")
            return False
    
    def _verify_meta_signature(self, request) -> bool:
        """Verifica la firma de Meta"""
        try:
            # Implementar verificación de firma de Meta
            return True  # Simplificado para desarrollo
            
        except Exception as e:
            logger.error(f"Error verifying Meta signature: {e}")
            return False
    
    def _extract_twilio_data(self, post_data) -> Dict[str, Any]:
        """Extrae datos del webhook de Twilio"""
        return {
            'from': post_data.get('From', ''),
            'to': post_data.get('To', ''),
            'body': post_data.get('Body', ''),
            'message_id': post_data.get('MessageSid', ''),
            'timestamp': post_data.get('MessageTimestamp', ''),
            'attachments': self._extract_whatsapp_attachments(post_data)
        }
    
    def _extract_meta_data(self, request_body) -> Dict[str, Any]:
        """Extrae datos del webhook de Meta"""
        try:
            data = json.loads(request_body)
            # Implementar según formato de Meta
            return {
                'from': data.get('from', ''),
                'to': data.get('to', ''),
                'body': data.get('text', ''),
                'message_id': data.get('id', ''),
                'timestamp': data.get('timestamp', ''),
                'attachments': []
            }
        except Exception as e:
            logger.error(f"Error parsing Meta data: {e}")
            return {}
    
    def _extract_whatsapp_attachments(self, post_data) -> list:
        """Extrae archivos adjuntos de WhatsApp"""
        attachments = []
        # Implementar extracción de archivos según el servicio
        return attachments
    
    def _get_or_create_ticket_from_whatsapp(self, message_data: Dict[str, Any]) -> SupportTicket:
        """Obtiene o crea un ticket desde WhatsApp"""
        try:
            # Buscar ticket existente por número de WhatsApp
            existing_ticket = SupportTicket.objects.filter(
                customer_phone=message_data['from'],
                status__in=['open', 'waiting_customer']
            ).first()
            
            if existing_ticket:
                # Actualizar ticket existente
                existing_ticket.description += f"\n\nNuevo mensaje: {message_data['body']}"
                existing_ticket.save()
                return existing_ticket
            
            # Crear nuevo ticket
            config = SupportConfiguration.objects.first()
            
            ticket = SupportTicket.objects.create(
                subject='Consulta por WhatsApp',
                description=message_data['body'],
                channel='whatsapp',
                priority='medium',
                status='open',
                customer_phone=message_data['from']
            )
            
            # Guardar mensaje inicial
            Conversation.objects.create(
                ticket=ticket,
                message_type='user',
                content=message_data['body'],
                sender_phone=message_data['from']
            )
            
            return ticket
            
        except Exception as e:
            logger.error(f"Error creating ticket from WhatsApp: {e}")
            raise
    
    def _save_ai_response(self, ticket: SupportTicket, response: Dict[str, Any]):
        """Guarda la respuesta de la IA"""
        try:
            Conversation.objects.create(
                ticket=ticket,
                message_type='ai',
                content=response['message'],
                ai_agent_used=response.get('agent_used', 'supervisor'),
                confidence=response.get('confidence', 0.0)
            )
        except Exception as e:
            logger.error(f"Error saving AI response: {e}")
    
    def _send_whatsapp_response(self, to_phone: str, message: str, ticket: SupportTicket):
        """Envía respuesta por WhatsApp"""
        try:
            # Implementar envío usando Twilio o Meta API
            # Por ahora, solo log
            logger.info(f"WhatsApp response to {to_phone}: {message}")
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp response: {e}")


# Instancias globales
email_handler = EmailWebhookHandler()
whatsapp_handler = WhatsAppWebhookHandler() 