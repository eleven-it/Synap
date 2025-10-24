"""
Consumidores WebSocket para notificaciones en tiempo real
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import SupportTicket, Conversation


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Consumidor WebSocket para el chat en tiempo real
    """
    
    async def connect(self):
        """
        Maneja la conexión WebSocket
        """
        self.user = self.scope["user"]
        self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
        self.room_group_name = f'chat_{self.ticket_id}'
        
        # Verificar autenticación
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Verificar permisos para el ticket
        if not await self.can_access_ticket():
            await self.close()
            return
        
        # Unirse al grupo del chat
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Enviar mensaje de conexión
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Conectado al chat en tiempo real'
        }))
    
    async def disconnect(self, close_code):
        """
        Maneja la desconexión WebSocket
        """
        # Salir del grupo del chat
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Maneja mensajes recibidos del WebSocket
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                message = text_data_json['message']
                sender = text_data_json.get('sender', self.user.username)
                
                # Guardar mensaje en la base de datos
                await self.save_message(message, sender)
                
                # Enviar mensaje al grupo
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'sender': sender,
                        'timestamp': text_data_json.get('timestamp')
                    }
                )
            
            elif message_type == 'typing':
                # Notificar que alguien está escribiendo
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_typing',
                        'user': self.user.username
                    }
                )
            
            elif message_type == 'stop_typing':
                # Notificar que alguien dejó de escribir
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_stop_typing',
                        'user': self.user.username
                    }
                )
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Formato de mensaje inválido'
            }))
    
    async def chat_message(self, event):
        """
        Envía mensaje de chat al WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event.get('timestamp')
        }))
    
    async def user_typing(self, event):
        """
        Notifica que un usuario está escribiendo
        """
        await self.send(text_data=json.dumps({
            'type': 'user_typing',
            'user': event['user']
        }))
    
    async def user_stop_typing(self, event):
        """
        Notifica que un usuario dejó de escribir
        """
        await self.send(text_data=json.dumps({
            'type': 'user_stop_typing',
            'user': event['user']
        }))
    
    async def notification(self, event):
        """
        Envía notificación al WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'notification_type': event.get('notification_type', 'info')
        }))
    
    @database_sync_to_async
    def can_access_ticket(self):
        """
        Verifica si el usuario puede acceder al ticket
        """
        try:
            ticket = SupportTicket.objects.get(id=self.ticket_id)
            return (self.user == ticket.customer or 
                   self.user == ticket.assigned_agent or 
                   self.user.groups.filter(name__in=['agent', 'supervisor']).exists())
        except SupportTicket.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, message, sender):
        """
        Guarda el mensaje en la base de datos
        """
        try:
            ticket = SupportTicket.objects.get(id=self.ticket_id)
            Conversation.objects.create(
                ticket=ticket,
                message_type='user' if sender == self.user.username else 'agent',
                content=message
            )
        except SupportTicket.DoesNotExist:
            pass


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumidor WebSocket para notificaciones generales
    """
    
    async def connect(self):
        """
        Maneja la conexión WebSocket para notificaciones
        """
        self.user = self.scope["user"]
        
        # Verificar autenticación
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Unirse al grupo de notificaciones del usuario
        self.room_group_name = f'notifications_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Enviar mensaje de conexión
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Conectado a notificaciones en tiempo real'
        }))
    
    async def disconnect(self, close_code):
        """
        Maneja la desconexión WebSocket
        """
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Maneja mensajes recibidos del WebSocket
        """
        # Los usuarios no envían mensajes a las notificaciones
        pass
    
    async def notification(self, event):
        """
        Envía notificación al WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'notification_type': event.get('notification_type', 'info'),
            'data': event.get('data', {})
        }))
    
    async def ticket_update(self, event):
        """
        Envía actualización de ticket al WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'ticket_update',
            'ticket_id': event['ticket_id'],
            'update_type': event['update_type'],
            'data': event.get('data', {})
        })) 