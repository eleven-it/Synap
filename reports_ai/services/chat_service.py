"""
Servicio de Chat Conversacional
Gestiona conversaciones y mensajes
"""
import json
from typing import Dict, List, Optional
from django.utils import timezone

from ..models import ChatConversation, ChatMessage, ReportRequest


class ConversationManager:
    """
    Gestor de contexto de conversaciones
    Mantiene estado y contexto entre mensajes
    """
    
    def __init__(self):
        pass
    
    def create_conversation(self, user, first_message: str) -> ChatConversation:
        """
        Crea una nueva conversación
        
        Args:
            user: Usuario propietario
            first_message: Primer mensaje del usuario
        
        Returns:
            ChatConversation creada
        """
        # Generar título desde el primer mensaje (máximo 50 chars)
        title = first_message[:47] + '...' if len(first_message) > 50 else first_message
        
        conversation = ChatConversation.objects.create(
            user=user,
            title=title,
            is_active=True
        )
        
        return conversation
    
    def get_or_create_active_conversation(self, user) -> ChatConversation:
        """
        Obtiene la conversación activa del usuario o crea una nueva
        """
        conversation = ChatConversation.objects.filter(
            user=user,
            is_active=True
        ).first()
        
        if not conversation:
            conversation = ChatConversation.objects.create(
                user=user,
                title="Nueva conversación",
                is_active=True
            )
        
        return conversation
    
    def get_conversation_context(self, conversation: ChatConversation) -> Dict:
        """
        Obtiene el contexto de una conversación para el siguiente mensaje
        Incluye últimos mensajes, reportes generados, etc.
        """
        messages = conversation.messages.order_by('-created_at')[:10]
        
        # Último reporte generado
        last_report = None
        for msg in messages:
            if msg.report_request:
                last_report = {
                    'id': str(msg.report_request.id),
                    'query': msg.report_request.query,
                    'has_data': bool(msg.report_request.result_data)
                }
                break
        
        # Últimas entidades mencionadas
        entities = []
        for msg in messages:
            if msg.entities:
                entities.extend(msg.entities.get('entities', []))
        
        # Remover duplicados
        unique_entities = list(set(entities))[:5]
        
        # NUEVO: Construir historial de mensajes para el LLM
        # Últimos 10 mensajes en orden cronológico (más antiguos primero)
        message_history = []
        for msg in reversed(list(messages)):
            message_history.append({
                'role': msg.role,
                'content': msg.content,
                'message_type': msg.message_type,
                'intent': msg.intent,
                'timestamp': msg.created_at.isoformat()
            })
        
        return {
            'conversation_id': str(conversation.conversation_id),
            'message_count': conversation.get_message_count(),
            'last_report': last_report,
            'recent_entities': unique_entities,
            'recent_intents': [msg.intent for msg in messages if msg.intent][:5],
            'message_history': message_history  # NUEVO: Historial completo
        }
    
    def archive_conversation(self, conversation: ChatConversation):
        """Archiva una conversación"""
        conversation.is_active = False
        conversation.save()


class ChatService:
    """
    Servicio principal de chat
    Coordina entre conversaciones y agentes
    """
    
    def __init__(self):
        self.conversation_manager = ConversationManager()
        
        # Inicializar sistema de agentes completo
        from ..services.crew_service import CrewService
        self.crew_service = CrewService()
        
        # Habilitar Data Analyst V2 de forma persistente en el proceso web
        # Si no puede inicializarse, CrewService dejará el original como fallback
        try:
            self.crew_service.enable_data_analyst_v2()
        except Exception:
            # En caso de fallo, mantener funcionamiento con Data Analyst original
            pass
    
    def process_message(
        self,
        user,
        message_text: str,
        conversation_id: Optional[str] = None
    ) -> Dict:
        """
        Procesa un mensaje del usuario y genera respuesta del asistente
        
        Args:
            user: Usuario que envía el mensaje
            message_text: Texto del mensaje
            conversation_id: ID de conversación existente (opcional)
        
        Returns:
            Dict con mensaje del usuario, respuesta del asistente, y metadata
        """
        # 1. Obtener o crear conversación
        if conversation_id:
            conversation = ChatConversation.objects.get(conversation_id=conversation_id)
        else:
            # Primera interacción: crear conversación
            if ChatConversation.objects.filter(user=user, is_active=True).exists():
                conversation = ChatConversation.objects.filter(user=user, is_active=True).first()
            else:
                conversation = self.conversation_manager.create_conversation(user, message_text)
        
        # 2. Guardar mensaje del usuario
        user_message = ChatMessage.objects.create(
            conversation=conversation,
            role='user',
            content=message_text,
            message_type='text'
        )
        
        # 3. Obtener contexto de la conversación
        context = self.conversation_manager.get_conversation_context(conversation)
        
        # 4. Procesar con el sistema AI (usando CrewService con todos los agentes)
        ai_response = self.crew_service.orchestrator.execute({
            'query': message_text,
            'conversation_context': context
        })
        
        # 5. Guardar respuesta del asistente
        assistant_message = self._create_assistant_message(
            conversation,
            ai_response
        )
        
        # 6. Retornar ambos mensajes
        return {
            'success': True,
            'conversation_id': str(conversation.conversation_id),
            'user_message': self._serialize_message(user_message),
            'assistant_message': self._serialize_message(assistant_message),
            'context': context
        }
    
    def _create_assistant_message(
        self,
        conversation: ChatConversation,
        ai_response: Dict
    ) -> ChatMessage:
        """
        Crea mensaje del asistente desde la respuesta del AI
        """
        # Determinar tipo de mensaje
        message_type = ai_response.get('type', 'text')
        
        # Si no hay 'type' pero hay 'report', es un reporte de datos
        if not message_type and ai_response.get('report'):
            message_type = 'report_data'
        
        # Mapear tipos del AI a tipos de mensaje
        type_mapping = {
            'procedure': 'procedure',
            'report_data': 'report_data',
            'clarification': 'clarification',
            'export_options': 'download_offer',
            'general_response': 'text',
            'not_found': 'clarification',
            'error': 'error',
            'text': 'text'
        }
        
        mapped_type = type_mapping.get(message_type, 'text')
        
        # Extraer content según el tipo de respuesta
        content = ''
        if ai_response.get('content'):
            content = ai_response['content']
        elif ai_response.get('message'):
            content = ai_response['message']
        elif ai_response.get('report'):
            # Reporte de datos: construir narrativa desde el reporte
            report = ai_response['report']
            content = self._build_narrative_from_report(report)
        else:
            content = 'No se pudo generar respuesta'
        
        # Crear mensaje
        message = ChatMessage.objects.create(
            conversation=conversation,
            role='assistant',
            content=content,
            message_type=mapped_type,
            intent=ai_response.get('intent', ''),
            entities=ai_response.get('entities', {}),
            report_request_id=ai_response.get('report_id'),
            metadata=ai_response.get('metadata', {})
        )
        
        return message
    
    def _build_narrative_from_report(self, report: Dict) -> str:
        """
        Construye una narrativa CONCISA y DIRECTA desde el reporte
        
        Args:
            report: Reporte con resumen, metricas, desglose, notas
        
        Returns:
            String con narrativa simple y directa (solo lo esencial)
        """
        # Si hay datos directos (data), mostrar solo esos de forma simple
        if report.get('data') and isinstance(report['data'], list):
            data = report['data']
            row_count = len(data)
            
            if data:
                first_row = data[0]
                
                # Buscar columnas candidatas por nombre semántico (evitar IDs)
                candidate_cols = [k for k in first_row.keys() if any(
                    kw in k.lower() for kw in ['nombre', 'name', 'descripcion', 'desc']
                ) and 'id' not in k.lower()]
                
                # Si no hay por nombre, probar columnas que contengan 'cliente', 'articulo', 'producto' pero evitar IDs
                if not candidate_cols:
                    candidate_cols = [k for k in first_row.keys() if any(
                        kw in k.lower() for kw in ['cliente', 'articulo', 'producto']
                    ) and 'id' not in k.lower()]
                
                # Priorizar columnas cuyo valor sea texto (no numérico)
                def is_textual(col: str) -> bool:
                    val = first_row.get(col)
                    return isinstance(val, str) and len(val.strip()) > 0
                
                text_cols = [c for c in candidate_cols if is_textual(c)]
                
                name_columns = text_cols or candidate_cols
                
                if name_columns:
                    # Es un listado simple: mostrar solo nombres
                    name_col = name_columns[0]
                    names = []
                    for row in data:
                        value = row.get(name_col)
                        if isinstance(value, str) and value.strip():
                            names.append(value.strip())
                    
                    if names:
                        entity_type = self._infer_entity_type(name_col)
                        result = f"Encontramos {row_count} {entity_type}:\n\n"
                        for name in names:
                            result += f"- {name}\n"
                        return result.strip()
            
            # Si no es simple, usar formato de tabla mínima
            return self._format_table_data(data)
        
        # Si no hay data directa, construir narrativa mínima (solo lo esencial)
        parts = []
        
        # Solo resumen si existe (sin'títulos innecesarios)
        if report.get('resumen'):
            for bullet in report['resumen']:
                parts.append(bullet)
        
        # Solo desglose si hay datos (sin títulos)
        if report.get('desglose'):
            desglose = report['desglose']
            if isinstance(desglose, list) and desglose:
                parts.append(self._format_table_data(desglose))
        
        return "\n".join(parts).strip() if parts else "No se encontraron datos."
    
    def _infer_entity_type(self, column_name: str) -> str:
        """Infiere el tipo de entidad desde el nombre de columna"""
        col_lower = column_name.lower()
        if 'cliente' in col_lower or 'client' in col_lower:
            return 'clientes'
        elif 'articulo' in col_lower or 'producto' in col_lower or 'item' in col_lower:
            return 'artículos'
        elif 'pedido' in col_lower or 'order' in col_lower:
            return 'pedidos'
        elif 'factura' in col_lower or 'invoice' in col_lower:
            return 'facturas'
        else:
            return 'registros'
    
    def _format_table_data(self, data: list) -> str:
        """Formatea datos tabulares para mostrar en el chat"""
        if not data:
            return ''
        
        # Tomar máximo 10 filas para el chat
        rows = data[:10]
        if not rows:
            return ''
        
        # Crear tabla simple
        headers = list(rows[0].keys())
        
        table_str = "```\n"
        # Headers
        table_str += " | ".join(headers) + "\n"
        table_str += "-" * (len(" | ".join(headers))) + "\n"
        
        # Rows
        for row in rows:
            values = [str(row.get(h, '')) for h in headers]
            table_str += " | ".join(values) + "\n"
        
        if len(data) > 10:
            table_str += f"\n... y {len(data) - 10} filas más\n"
        
        table_str += "```"
        return table_str
    
    def _serialize_message(self, message: ChatMessage) -> Dict:
        """
        Serializa un mensaje para enviar al frontend
        """
        return {
            'message_id': str(message.message_id),
            'role': message.role,
            'content': message.content,
            'message_type': message.message_type,
            'intent': message.intent,
            'entities': message.entities,
            'metadata': message.metadata,
            'created_at': message.created_at.isoformat(),
            'report_id': str(message.report_request_id) if message.report_request_id else None
        }
    
    def get_conversation_history(
        self,
        conversation: ChatConversation,
        limit: int = 50
    ) -> List[Dict]:
        """
        Obtiene el historial de mensajes de una conversación
        """
        messages = conversation.messages.order_by('created_at')[:limit]
        return [self._serialize_message(msg) for msg in messages]

