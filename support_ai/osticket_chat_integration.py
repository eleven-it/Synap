"""
Integración Bidireccional entre Chat Multiagente y osTicket
Permite crear tickets desde el chat y sincronizar respuestas
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.conf import settings
from .osticket_integration import get_osticket_integration
from .dynamic_agent_models import DynamicAgent
from .dynamic_agent_service import DynamicAgentService
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class OsTicketChatIntegration:
    """
    Integración bidireccional entre el chat multiagente y osTicket
    """
    
    def __init__(self):
        self.osticket_integration = get_osticket_integration()
        self.dynamic_agent_service = DynamicAgentService()
    
    def create_ticket_from_chat(
        self, 
        user_message: str, 
        user_id: str, 
        user_email: str,
        conversation_context: List[Dict[str, Any]] = None,
        agent_id: str = None
    ) -> Dict[str, Any]:
        """
        Crea un ticket en osTicket desde el chat
        """
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {
                    'success': False,
                    'error': 'No se pudo conectar con osTicket'
                }
            
            cursor = conn.cursor(dictionary=True)
            
            # 1. Crear el ticket
            ticket_data = {
                'user_id': self._get_or_create_user(cursor, user_id, user_email),
                'status_id': 1,  # Abierto
                'priority_id': self._determine_priority(user_message),
                'dept_id': self._determine_department(user_message),
                'topic_id': self._determine_topic(user_message),
                'created': timezone.now(),
                'updated': timezone.now()
            }
            
            # Generar número de ticket
            ticket_number = self._generate_ticket_number()
            
            # Insertar ticket
            insert_query = """
                INSERT INTO ost_ticket (
                    user_id, status_id, dept_id, topic_id, 
                    created, updated, source, source_extra, number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                ticket_data['user_id'],
                ticket_data['status_id'],
                
                ticket_data['dept_id'],
                ticket_data['topic_id'],
                ticket_data['created'],
                ticket_data['updated'],
                'chat_ai',
                json.dumps({'agent_id': agent_id, 'platform': 'eleven_support'}),
                ticket_number
            ))
            
            ticket_id = cursor.lastrowid
            
            # 2. Crear el thread
            thread_query = """
                INSERT INTO ost_thread (
                    object_id, object_type, created
                ) VALUES (%s, %s, %s)
            """
            
            cursor.execute(thread_query, (ticket_id, 'T', timezone.now()))
            thread_id = cursor.lastrowid
            
            # 3. Crear la entrada del thread (mensaje del usuario)
            entry_query = """
                INSERT INTO ost_thread_entry (
                    thread_id, user_id, type, title, body, format, created
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            # Determinar título del ticket
            ticket_title = self._generate_ticket_title(user_message, conversation_context)
            
            cursor.execute(entry_query, (
                thread_id,
                ticket_data['user_id'],
                'M',  # Mensaje
                ticket_title,
                user_message,
                'html',
                timezone.now()
            ))
            
            # 4. Si hay contexto de conversación, agregarlo como notas
            if conversation_context and len(conversation_context) > 1:
                context_summary = self._create_conversation_summary(conversation_context)
                
                # Agregar nota con el contexto
                note_query = """
                    INSERT INTO ost_note (
                        pid, user_id,  type, title, body, created
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(note_query, (
                    ticket_id,
                    ticket_data['user_id'],
                    None,  # No es staff
                    'note',
                    'Contexto de Chat AI',
                    context_summary,
                    timezone.now()
                ))
            
            conn.commit()
            cursor.close()
            
            logger.info(f"✅ Ticket creado exitosamente: {ticket_id}")
            
            return {
                'success': True,
                'ticket_id': ticket_id,
                'ticket_number': ticket_number,
                'status': 'abierto',
                'priority': self._get_priority_name(ticket_data['priority_id']),
                'department': self._get_department_name(ticket_data['dept_id']),
                'message': f'Ticket creado exitosamente. Número: {ticket_number}'
            }
            
        except Exception as e:
            logger.error(f"Error creando ticket desde chat: {e}")
            if conn:
                conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_response_to_ticket(
        self, 
        ticket_id: int, 
        response_message: str, 
        staff_id: str = None,
        response_type: str = 'R'
    ) -> Dict[str, Any]:
        """
        Agrega una respuesta al ticket existente
        """
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {
                    'success': False,
                    'error': 'No se pudo conectar con osTicket'
                }
            
            cursor = conn.cursor(dictionary=True)
            
            # Obtener el thread del ticket
            thread_query = """
                SELECT id FROM ost_thread 
                WHERE object_id = %s AND object_type = 'T'
            """
            cursor.execute(thread_query, (ticket_id,))
            thread_result = cursor.fetchone()
            
            if not thread_result:
                return {
                    'success': False,
                    'error': 'Thread no encontrado para el ticket'
                }
            
            thread_id = thread_result['id']
            
            # Crear entrada de respuesta
            entry_query = """
                INSERT INTO ost_thread_entry (
                    thread_id,  user_id, type, title, body, format, created
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(entry_query, (
                thread_id,
                
                None if staff_id else 1,  # Usuario por defecto si no es staff
                response_type,
                'Respuesta del Sistema',
                response_message,
                'html',
                timezone.now()
            ))
            
            # Actualizar timestamp del ticket
            update_query = """
                UPDATE ost_ticket 
                SET updated = %s, lastupdate = %s
                WHERE ticket_id = %s
            """
            cursor.execute(update_query, (timezone.now(), timezone.now(), ticket_id))
            
            conn.commit()
            cursor.close()
            
            logger.info(f"✅ Respuesta agregada al ticket {ticket_id}")
            
            return {
                'success': True,
                'message': 'Respuesta agregada exitosamente',
                'ticket_id': ticket_id
            }
            
        except Exception as e:
            logger.error(f"Error agregando respuesta al ticket: {e}")
            if conn:
                conn.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_ticket_status(self, ticket_id: int) -> Dict[str, Any]:
        """Obtiene el estado actual de un ticket"""
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {'error': 'No se pudo conectar'}
            
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    t.ticket_id,
                    t.number,
                    t.status_id,
                    
                    t.dept_id,
                    t.created,
                    t.updated,
                    t.closed,
                    s.name as status_name,
                    p.priority as priority_name,
                    d.name as dept_name
                FROM ost_ticket t
                LEFT JOIN ost_ticket_status s ON t.status_id = s.id
                LEFT JOIN ost_ticket_priority p ON t.priority_id = p.id
                LEFT JOIN ost_department d ON t.dept_id = d.id
                WHERE t.ticket_id = %s
            """
            
            cursor.execute(query, (ticket_id,))
            ticket = cursor.fetchone()
            
            if not ticket:
                return {'error': 'Ticket no encontrado'}
            
            # Obtener conversación del ticket
            conversation_query = """
                SELECT 
                    te.id,
                    te.type,
                    te.title,
                    te.body,
                    te.created,
                    te.
                    te.user_id
                FROM ost_thread th
                JOIN ost_thread_entry te ON th.id = te.thread_id
                WHERE th.object_id = %s AND th.object_type = 'T'
                ORDER BY te.created
            """
            
            cursor.execute(conversation_query, (ticket_id,))
            conversation = cursor.fetchall()
            
            cursor.close()
            
            return {
                'success': True,
                'ticket': ticket,
                'conversation': conversation
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del ticket: {e}")
            return {'error': str(e)}
    
    def update_ticket_status(
        self, 
        ticket_id: int, 
        new_status: str, 
        staff_id: str = None
    ) -> Dict[str, Any]:
        """Actualiza el estado de un ticket"""
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return {'error': 'No se pudo conectar'}
            
            cursor = conn.cursor(dictionary=True)
            
            # Mapear estados
            status_mapping = {
                'open': 1,
                'answered': 2,
                'closed': 3,
                'pending': 4
            }
            
            new_status_id = status_mapping.get(new_status.lower(), 1)
            
            # Actualizar estado
            update_query = """
                UPDATE ost_ticket 
                SET status_id = %s, updated = %s
                WHERE ticket_id = %s
            """
            
            cursor.execute(update_query, (new_status_id, timezone.now(), ticket_id))
            
            # Agregar nota de cambio de estado
            if staff_id:
                note_query = """
                    INSERT INTO ost_note (
                        pid, user_id,  type, title, body, created
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(note_query, (
                    ticket_id,
                    None,
                    
                    'note',
                    'Cambio de Estado',
                    f'Estado cambiado a: {new_status}',
                    timezone.now()
                ))
            
            conn.commit()
            cursor.close()
            
            return {
                'success': True,
                'message': f'Estado del ticket actualizado a: {new_status}'
            }
            
        except Exception as e:
            logger.error(f"Error actualizando estado del ticket: {e}")
            if conn:
                conn.rollback()
            return {'error': str(e)}
    
    # Métodos auxiliares privados
    
    def _get_or_create_user(self, cursor, user_id: str, user_email: str) -> int:
        """Obtiene o crea un usuario en osTicket"""
        # Buscar usuario existente por email en ost_user_email
        cursor.execute("""
            SELECT u.id FROM ost_user u
            JOIN ost_user_email ue ON u.id = ue.user_id
            WHERE ue.address = %s
        """, (user_email,))
        user = cursor.fetchone()
        
        if user:
            return user['id']
        
        # Crear nuevo usuario
        cursor.execute("""
            INSERT INTO ost_user (org_id, status, name, created, updated) 
            VALUES (1, 1, %s, %s, %s)
        """, (f"Usuario {user_id[:8]}", timezone.now(), timezone.now()))
        
        new_user_id = cursor.lastrowid
        
        # Crear el email para el usuario
        cursor.execute("""
            INSERT INTO ost_user_email (user_id, flags, address) 
            VALUES (%s, 0, %s)
        """, (new_user_id, user_email))
        
        return new_user_id
    
    def _determine_priority(self, message: str) -> int:
        """Determina la prioridad basada en el mensaje"""
        message_lower = message.lower()
        
        # Palabras clave de alta prioridad
        high_priority = ['urgente', 'crítico', 'error', 'falla', 'no funciona', 'bloqueado']
        medium_priority = ['problema', 'ayuda', 'consulta', 'duda']
        
        if any(keyword in message_lower for keyword in high_priority):
            return 3  # Alta prioridad
        elif any(keyword in message_lower for keyword in medium_priority):
            return 2  # Media prioridad
        else:
            return 1  # Baja prioridad
    
    def _determine_department(self, message: str) -> int:
        """Determina el departamento basado en el mensaje"""
        message_lower = message.lower()
        
        # Mapeo de palabras clave a departamentos
        dept_mapping = {
            'técnico': 1,      # Soporte Técnico
            'facturación': 2,   # Facturación
            'ventas': 3,        # Ventas
            'configuración': 1, # Soporte Técnico
            'error': 1,         # Soporte Técnico
            'pago': 2,          # Facturación
            'cobro': 2,         # Facturación
            'producto': 3,      # Ventas
            'precio': 3         # Ventas
        }
        
        for keyword, dept_id in dept_mapping.items():
            if keyword in message_lower:
                return dept_id
        
        return 1  # Soporte Técnico por defecto
    
    def _determine_topic(self, message: str) -> int:
        """Determina el tópico basado en el mensaje"""
        # Por ahora, usar tópico por defecto
        return 1
    
    def _generate_ticket_title(self, message: str, context: List[Dict[str, Any]] = None) -> str:
        """Genera un título para el ticket basado en el mensaje"""
        # Limpiar mensaje y generar título
        clean_message = re.sub(r'<[^>]+>', '', message)  # Remover HTML
        clean_message = clean_message.strip()
        
        if len(clean_message) <= 50:
            return clean_message
        
        # Truncar y agregar ...
        return clean_message[:47] + "..."
    
    def _create_conversation_summary(self, context: List[Dict[str, Any]]) -> str:
        """Crea un resumen de la conversación para el ticket"""
        summary = "Contexto de la conversación en Chat AI:\n\n"
        
        for i, msg in enumerate(context[-5:], 1):  # Últimos 5 mensajes
            role = "Usuario" if msg.get('role') == 'user' else "Agente"
            content = msg.get('content', '')[:100]  # Primeros 100 caracteres
            summary += f"{i}. {role}: {content}\n"
        
        return summary
    
    def _generate_ticket_number(self) -> str:
        """Genera un número único de ticket"""
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return f"T{int(timezone.now().timestamp())}"
            
            cursor = conn.cursor()
            
            # Obtener el último número de ticket
            cursor.execute("SELECT MAX(CAST(number AS UNSIGNED)) FROM ost_ticket WHERE number REGEXP '^[0-9]+$'")
            result = cursor.fetchone()
            
            if result and result[0]:
                next_number = int(result[0]) + 1
            else:
                next_number = 1000  # Número inicial
            
            cursor.close()
            
            return str(next_number)
            
        except Exception as e:
            logger.warning(f"Error generando número de ticket: {e}")
            # Fallback: usar timestamp
            return f"T{int(timezone.now().timestamp())}"
    
    def _get_ticket_number(self, ticket_id: int) -> str:
        """Obtiene el número del ticket"""
        try:
            conn = self.osticket_integration.get_connection()
            if not conn:
                return str(ticket_id)
            
            cursor = conn.cursor()
            cursor.execute("SELECT number FROM ost_ticket WHERE ticket_id = %s", (ticket_id,))
            result = cursor.fetchone()
            cursor.close()
            
            return str(result[0]) if result else str(ticket_id)
        except:
            return str(ticket_id)
    
    def _get_priority_name(self, priority_id: int) -> str:
        """Obtiene el nombre de la prioridad"""
        priority_names = {1: 'Baja', 2: 'Media', 3: 'Alta'}
        return priority_names.get('Baja')
    
    def _get_department_name(self, dept_id: int) -> str:
        """Obtiene el nombre del departamento"""
        dept_names = {1: 'Soporte Técnico', 2: 'Facturación', 3: 'Ventas'}
        return dept_names.get(dept_id, 'Soporte Técnico')


# Instancia global
_osticket_chat_integration = None


def get_osticket_chat_integration() -> OsTicketChatIntegration:
    """Obtiene la instancia global de integración de chat con osTicket"""
    global _osticket_chat_integration
    
    if _osticket_chat_integration is None:
        _osticket_chat_integration = OsTicketChatIntegration()
    
    return _osticket_chat_integration


def test_osticket_chat_integration() -> Dict[str, Any]:
    """Prueba la integración de chat con osTicket"""
    try:
        integration = get_osticket_chat_integration()
        
        # Simular creación de ticket
        test_message = "Necesito ayuda con la configuración del sistema"
        test_user_id = "test_user_123"
        test_email = "test@example.com"
        
        result = integration.create_ticket_from_chat(
            test_message, test_user_id, test_email
        )
        
        if result['success']:
            ticket_id = result['ticket_id']
            
            # Obtener estado del ticket
            status = integration.get_ticket_status(ticket_id)
            
            # Agregar respuesta de prueba
            response_result = integration.add_response_to_ticket(
                ticket_id, 
                "Hemos recibido tu consulta y la estamos procesando."
            )
            
            return {
                'success': True,
                'ticket_created': True,
                'ticket_id': ticket_id,
                'ticket_number': result['ticket_number'],
                'status_retrieved': status.get('success', False),
                'response_added': response_result.get('success', False),
                'message': f'Integración exitosa: Ticket {result["ticket_number"]} creado'
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Error desconocido')
            }
            
    except Exception as e:
        logger.error(f"Error en prueba de integración de chat con osTicket: {e}")
        return {
            'success': False,
            'error': str(e),
            'details': 'Error inesperado durante la prueba'
        }
