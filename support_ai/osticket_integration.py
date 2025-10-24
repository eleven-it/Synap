"""
Integración con osTicket para entrenamiento de agentes
Utiliza las credenciales existentes del proyecto conocimiento
"""

import logging
import json
import mysql.connector
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.conf import settings
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OsTicketIntegration:
    """
    Integración con osTicket para extraer datos de entrenamiento
    """
    
    def __init__(self):
        # Configuración de osTicket desde el proyecto conocimiento
        self.db_config = {
            'host': 'administranet.com.ar',
            'database': 'soporte',
            'user': 'soporteOsTicket',
            'password': 'a7v8xx0805',
            'charset': 'utf8',
            'autocommit': True
        }
        
        self.table_prefix = 'ost_'
        self.connection = None
        self._test_connection()
    
    def _test_connection(self):
        """Prueba la conexión con osTicket"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                logger.info("✅ Conexión exitosa con osTicket")
                return True
        except Exception as e:
            logger.error(f"❌ Error conectando a osTicket: {e}")
            return False
    
    def get_connection(self):
        """Obtiene una conexión activa a osTicket"""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connection = mysql.connector.connect(**self.db_config)
            return self.connection
        except Exception as e:
            logger.error(f"Error obteniendo conexión: {e}")
            return None
    
    def extract_faq_knowledge(self) -> List[Dict[str, Any]]:
        """
        Extrae toda la base de conocimiento de osTicket
        """
        try:
            conn = self.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor(dictionary=True)
            
            # Consulta principal que une categorías y FAQs
            query = f"""
                SELECT 
                    c.category_id,
                    c.name AS category_name,
                    c.description AS category_description,
                    c.ispublic AS category_public,
                    f.faq_id,
                    f.question,
                    f.answer,
                    f.keywords,
                    f.ispublished,
                    f.created,
                    f.updated
                FROM {self.table_prefix}faq_category c
                LEFT JOIN {self.table_prefix}faq f ON c.category_id = f.category_id AND f.ispublished = 1
                WHERE c.ispublic = 1
                ORDER BY c.category_id, f.faq_id
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            knowledge_data = []
            for row in results:
                if row['faq_id']:  # Solo artículos con FAQ
                    knowledge_item = {
                        'source': 'osticket',
                        'category_id': row['category_id'],
                        'category_name': row['category_name'],
                        'category_description': row['category_description'],
                        'faq_id': row['faq_id'],
                        'question': row['question'],
                        'answer': row['answer'],
                        'keywords': row['keywords'].split(',') if row['keywords'] else [],
                        'created': row['created'],
                        'updated': row['updated'],
                        'extracted_at': timezone.now().isoformat()
                    }
                    knowledge_data.append(knowledge_item)
            
            cursor.close()
            logger.info(f"✅ Extraídos {len(knowledge_data)} artículos de conocimiento de osTicket")
            return knowledge_data
            
        except Exception as e:
            logger.error(f"Error extrayendo FAQ de osTicket: {e}")
            return []
    
    def extract_ticket_data(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Extrae datos de tickets para análisis de patrones
        """
        try:
            conn = self.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor(dictionary=True)
            
            # Calcular fecha límite
            limit_date = datetime.now() - timedelta(days=days_back)
            
            # Consulta optimizada para osTicket usando ost_thread_entry
            query = f"""
                SELECT 
                    t.ticket_id,
                    t.number,
                    t.status_id,
                    t.created,
                    t.updated,
                    t.closed,
                    th.id as thread_id,
                    th.object_id,
                    th.object_type,
                    te.id as entry_id,
                    te.type as entry_type,
                    te.title,
                    te.body,
                    te.format,
                    te.created as entry_created,
                    te.staff_id,
                    te.user_id
                FROM {self.table_prefix}ticket t
                JOIN {self.table_prefix}thread th ON t.ticket_id = th.object_id
                JOIN {self.table_prefix}thread_entry te ON th.id = te.thread_id
                WHERE th.object_type = 'T'
                AND te.body IS NOT NULL
                AND te.body != ''
                AND te.created >= %s
                ORDER BY t.ticket_id, te.created
                LIMIT 300  -- Limitar para evitar sobrecarga
            """
            
            cursor.execute(query, (limit_date,))
            results = cursor.fetchall()
            
            ticket_data = []
            current_ticket = None
            
            for row in results:
                if current_ticket is None or current_ticket['ticket_id'] != row['ticket_id']:
                    # Nuevo ticket
                    current_ticket = {
                        'source': 'osticket',
                        'ticket_id': row['ticket_id'],
                        'number': row['number'],
                        'status_id': row['status_id'],
                        'created': row['created'],
                        'updated': row['updated'],
                        'closed': row['closed'],
                        'conversation': []
                    }
                    ticket_data.append(current_ticket)
                
                # Agregar mensaje del thread_entry
                if row['body']:
                    # Determinar tipo de mensaje
                    if row['entry_type'] == 'M':
                        message_type = 'M'  # Mensaje
                    elif row['entry_type'] == 'R':
                        message_type = 'R'  # Respuesta
                    elif row['staff_id']:
                        message_type = 'R'  # Respuesta del staff
                    else:
                        message_type = 'M'  # Por defecto mensaje
                    
                    current_ticket['conversation'].append({
                        'type': message_type,
                        'body': row['body'],
                        'title': row['title'],
                        'created': row['entry_created'],
                        'entry_id': row['entry_id'],
                        'format': row['format'],
                        'staff_id': row['staff_id'],
                        'user_id': row['user_id']
                    })
            
            cursor.close()
            logger.info(f"✅ Extraídos {len(ticket_data)} tickets de osTicket")
            return ticket_data
            
        except Exception as e:
            logger.error(f"Error extrayendo tickets de osTicket: {e}")
            return []
    
    def extract_category_knowledge(self) -> List[Dict[str, Any]]:
        """
        Extrae información de categorías para clasificación
        """
        try:
            conn = self.get_connection()
            if not conn:
                return []
            
            cursor = conn.cursor(dictionary=True)
            
            query = f"""
                SELECT 
                    category_id,
                    name,
                    description,
                    ispublic,
                    created,
                    updated
                FROM {self.table_prefix}faq_category
                WHERE ispublic = 1
                ORDER BY category_id
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            categories = []
            for row in results:
                category = {
                    'source': 'osticket',
                    'category_id': row['category_id'],
                    'name': row['name'],
                    'description': row['description'],
                    'ispublic': bool(row['ispublic']),
                    'created': row['created'],
                    'updated': row['updated'],
                    'extracted_at': timezone.now().isoformat()
                }
                categories.append(category)
            
            cursor.close()
            logger.info(f"✅ Extraídas {len(categories)} categorías de osTicket")
            return categories
            
        except Exception as e:
            logger.error(f"Error extrayendo categorías de osTicket: {e}")
            return []
    
    def generate_training_data(self) -> Dict[str, Any]:
        """
        Genera datos de entrenamiento completos desde osTicket
        """
        try:
            logger.info("🔄 Generando datos de entrenamiento desde osTicket...")
            
            # Extraer todos los tipos de datos
            faq_data = self.extract_faq_knowledge()
            ticket_data = self.extract_ticket_data()
            category_data = self.extract_category_knowledge()
            
            # Generar pares de pregunta-respuesta para entrenamiento
            training_pairs = []
            
            # 1. FAQ directas
            for faq in faq_data:
                training_pair = {
                    'input': faq['question'],
                    'expected_output': faq['answer'],
                    'category': faq['category_name'],
                    'source': 'osticket_faq',
                    'faq_id': faq['faq_id'],
                    'keywords': faq['keywords'],
                    'difficulty': 'medium',
                    'tags': ['faq', 'osticket', faq['category_name'].lower()]
                }
                training_pairs.append(training_pair)
            
            # 2. Patrones de tickets
            for ticket in ticket_data:
                if len(ticket['conversation']) >= 2:
                    # Tomar el primer mensaje como pregunta y la primera respuesta como solución
                    question = ticket['conversation'][0]['body'] if ticket['conversation'] else ""
                    answer = ""
                    
                    # Buscar la primera respuesta
                    for msg in ticket['conversation']:
                        if msg['type'] == 'R' and msg['body']:
                            answer = msg['body']
                            break
                    
                    if question and answer:
                        training_pair = {
                            'input': question[:200] + "..." if len(question) > 200 else question,
                            'expected_output': answer[:500] + "..." if len(answer) > 500 else answer,
                            'category': 'Soporte Técnico',
                            'source': 'osticket_ticket',
                            'ticket_id': ticket['ticket_id'],
                            'status': ticket['status_id'],
                            'priority': 'normal', # No hay campo de prioridad en ost_ticket
                            'difficulty': 'medium',
                            'tags': ['ticket', 'osticket', 'soporte', ticket['status_id']]
                        }
                        training_pairs.append(training_pair)
            
            # 3. Categorías como contexto
            for category in category_data:
                if category['description']:
                    training_pair = {
                        'input': f"¿Qué es {category['name']}?",
                        'expected_output': category['description'],
                        'category': 'Información General',
                        'source': 'osticket_category',
                        'category_id': category['category_id'],
                        'difficulty': 'easy',
                        'tags': ['categoria', 'osticket', 'informacion', category['name'].lower()]
                    }
                    training_pairs.append(training_pair)
            
            # Resumen de datos extraídos
            summary = {
                'total_training_pairs': len(training_pairs),
                'faq_count': len(faq_data),
                'ticket_count': len(ticket_data),
                'category_count': len(category_data),
                'extraction_date': timezone.now().isoformat(),
                'source': 'osticket_integration'
            }
            
            logger.info(f"✅ Generados {len(training_pairs)} pares de entrenamiento")
            
            return {
                'success': True,
                'summary': summary,
                'training_pairs': training_pairs,
                'raw_data': {
                    'faq': faq_data,
                    'tickets': ticket_data,
                    'categories': category_data
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando datos de entrenamiento: {e}")
            return {
                'success': False,
                'error': str(e),
                'training_pairs': []
            }
    
    def get_osticket_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado de la integración con osTicket
        """
        try:
            conn = self.get_connection()
            if not conn:
                return {
                    'connected': False,
                    'error': 'No se pudo establecer conexión'
                }
            
            cursor = conn.cursor()
            
            # Verificar tablas principales
            tables_to_check = [
                f'{self.table_prefix}faq_category',
                f'{self.table_prefix}faq',
                f'{self.table_prefix}ticket',
                f'{self.table_prefix}thread'
            ]
            
            table_status = {}
            for table in tables_to_check:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    table_status[table] = {
                        'exists': True,
                        'record_count': count
                    }
                except Exception as e:
                    table_status[table] = {
                        'exists': False,
                        'error': str(e)
                    }
            
            cursor.close()
            
            return {
                'connected': True,
                'database': self.db_config['database'],
                'host': self.db_config['host'],
                'table_status': table_status,
                'last_check': timezone.now().isoformat()
            }
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def close_connection(self):
        """Cierra la conexión con osTicket"""
        try:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                logger.info("✅ Conexión con osTicket cerrada")
        except Exception as e:
            logger.error(f"Error cerrando conexión: {e}")

    def investigate_table_structure(self) -> Dict[str, Any]:
        """
        Investiga la estructura real de las tablas para entender cómo extraer datos
        """
        try:
            conn = self.get_connection()
            if not conn:
                return {'error': 'No se pudo conectar'}
            
            cursor = conn.cursor(dictionary=True)
            
            investigation = {
                'ticket_table': {},
                'thread_table': {},
                'message_table': None,
                'recommendations': []
            }
            
            # 1. Investigar tabla ticket
            cursor.execute("DESCRIBE ost_ticket")
            ticket_columns = [row['Field'] for row in cursor.fetchall()]
            investigation['ticket_table']['columns'] = ticket_columns
            investigation['ticket_table']['total_records'] = 0
            
            try:
                cursor.execute("SELECT COUNT(*) as count FROM ost_ticket")
                result = cursor.fetchone()
                investigation['ticket_table']['total_records'] = result['count']
            except Exception as e:
                investigation['ticket_table']['error'] = str(e)
            
            # 2. Investigar tabla thread
            cursor.execute("DESCRIBE ost_thread")
            thread_columns = [row['Field'] for row in cursor.fetchall()]
            investigation['thread_table']['columns'] = thread_columns
            investigation['thread_table']['total_records'] = 0
            
            try:
                cursor.execute("SELECT COUNT(*) as count FROM ost_thread")
                result = cursor.fetchone()
                investigation['thread_table']['total_records'] = result['count']
            except Exception as e:
                investigation['thread_table']['error'] = str(e)
            
            # 3. Buscar tabla de mensajes
            cursor.execute("SHOW TABLES LIKE '%message%'")
            message_tables = []
            for row in cursor.fetchall():
                # Obtener el nombre de la tabla del primer campo
                table_name = list(row.values())[0]
                message_tables.append(table_name)
            
            if message_tables:
                investigation['message_table'] = message_tables[0]
                # Investigar estructura de la tabla de mensajes
                cursor.execute(f"DESCRIBE {message_tables[0]}")
                message_columns = [row['Field'] for row in cursor.fetchall()]
                investigation['message_table_structure'] = message_columns
                
                try:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {message_tables[0]}")
                    result = cursor.fetchone()
                    investigation['message_table_records'] = result['count']
                except Exception as e:
                    investigation['message_table_records'] = f"Error: {e}"
            
            # 4. Buscar otras tablas relacionadas
            cursor.execute("SHOW TABLES LIKE '%ost_%'")
            all_tables = []
            for row in cursor.fetchall():
                # Obtener el nombre de la tabla del primer campo
                table_name = list(row.values())[0]
                all_tables.append(table_name)
            investigation['all_ost_tables'] = all_tables
            
            # 5. Analizar relaciones
            if 'ost_thread' in all_tables and 'ost_ticket' in all_tables:
                try:
                    # Ver si hay relación directa
                    cursor.execute("""
                        SELECT t.ticket_id, th.id as thread_id, th.object_id, th.object_type
                        FROM ost_ticket t
                        JOIN ost_thread th ON t.ticket_id = th.object_id
                        WHERE th.object_type = 'T'
                        LIMIT 5
                    """)
                    sample_relations = cursor.fetchall()
                    investigation['sample_relations'] = sample_relations
                except Exception as e:
                    investigation['relation_error'] = str(e)
            
            # 6. Generar recomendaciones
            if 'ost_thread' in all_tables and 'ost_ticket' in all_tables:
                if 'object_id' in thread_columns and 'object_type' in thread_columns:
                    investigation['recommendations'].append(
                        "Usar ost_thread.object_id para relacionar con ost_ticket.ticket_id"
                    )
                    investigation['recommendations'].append(
                        "ost_thread.object_type = 'T' indica tickets"
                    )
            
            if investigation['message_table']:
                investigation['recommendations'].append(
                    f"Usar {investigation['message_table']} para contenido de mensajes"
                )
            
            # 7. Buscar en ost_thread.extra
            if 'extra' in thread_columns:
                try:
                    cursor.execute("SELECT extra FROM ost_thread WHERE extra IS NOT NULL LIMIT 3")
                    extra_samples = cursor.fetchall()
                    investigation['extra_samples'] = [row['extra'] for row in extra_samples if row['extra']]
                except Exception as e:
                    investigation['extra_error'] = str(e)
            
            cursor.close()
            
            return investigation
            
        except Exception as e:
            logger.error(f"Error investigando estructura de tablas: {e}")
            return {'error': str(e)}

    def investigate_extra_field(self) -> Dict[str, Any]:
        """
        Investiga específicamente el contenido del campo extra para entender su estructura
        """
        try:
            conn = self.get_connection()
            if not conn:
                return {'error': 'No se pudo conectar'}
            
            cursor = conn.cursor(dictionary=True)
            
            investigation = {
                'extra_samples': [],
                'extra_analysis': {},
                'recommendations': []
            }
            
            # 1. Obtener muestras del campo extra
            cursor.execute("""
                SELECT 
                    th.id,
                    th.object_id,
                    th.object_type,
                    th.extra,
                    th.created,
                    LENGTH(th.extra) as extra_length
                FROM ost_thread th
                WHERE th.extra IS NOT NULL 
                AND th.extra != ''
                AND th.object_type = 'T'
                ORDER BY th.created DESC
                LIMIT 10
            """)
            
            samples = cursor.fetchall()
            investigation['extra_samples'] = samples
            
            # 2. Analizar patrones
            if samples:
                lengths = [s['extra_length'] for s in samples]
                investigation['extra_analysis']['min_length'] = min(lengths)
                investigation['extra_analysis']['max_length'] = max(lengths)
                investigation['extra_analysis']['avg_length'] = sum(lengths) / len(lengths)
                
                # Verificar si contiene HTML
                html_count = sum(1 for s in samples if '<' in s['extra'] and '>' in s['extra'])
                investigation['extra_analysis']['contains_html'] = html_count > 0
                investigation['extra_analysis']['html_percentage'] = (html_count / len(samples)) * 100
                
                # Verificar si contiene texto plano
                text_count = sum(1 for s in samples if len(s['extra'].strip()) > 10)
                investigation['extra_analysis']['contains_text'] = text_count > 0
                investigation['extra_analysis']['text_percentage'] = (text_count / len(samples)) * 100
            
            # 3. Verificar si hay tickets con contenido
            cursor.execute("""
                SELECT COUNT(*) as total_tickets
                FROM ost_ticket t
                JOIN ost_thread th ON t.ticket_id = th.object_id
                WHERE th.object_type = 'T'
            """)
            
            total_tickets = cursor.fetchone()['total_tickets']
            investigation['total_tickets'] = total_tickets
            
            # 4. Verificar tickets con contenido en extra
            cursor.execute("""
                SELECT COUNT(*) as tickets_with_extra
                FROM ost_ticket t
                JOIN ost_thread th ON t.ticket_id = th.object_id
                WHERE th.object_type = 'T'
                AND th.extra IS NOT NULL
                AND th.extra != ''
            """)
            
            tickets_with_extra = cursor.fetchone()['tickets_with_extra']
            investigation['tickets_with_extra'] = tickets_with_extra
            investigation['extra_coverage'] = (tickets_with_extra / total_tickets * 100) if total_tickets > 0 else 0
            
            # 5. Buscar en otras tablas relacionadas
            cursor.execute("SHOW TABLES LIKE '%entry%'")
            entry_tables = []
            for row in cursor.fetchall():
                table_name = list(row.values())[0]
                entry_tables.append(table_name)
            
            investigation['entry_tables'] = entry_tables
            
            # 6. Verificar ost_thread_entry si existe
            if 'ost_thread_entry' in entry_tables:
                cursor.execute("DESCRIBE ost_thread_entry")
                entry_columns = [row['Field'] for row in cursor.fetchall()]
                investigation['thread_entry_structure'] = entry_columns
                
                # Verificar si tiene contenido
                if 'body' in entry_columns or 'message' in entry_columns or 'content' in entry_columns:
                    investigation['recommendations'].append("Usar ost_thread_entry para contenido de mensajes")
                    
                    # Probar consulta
                    try:
                        cursor.execute("""
                            SELECT 
                                te.id,
                                te.thread_id,
                                te.body,
                                te.message,
                                te.content,
                                te.created
                            FROM ost_thread_entry te
                            JOIN ost_thread th ON te.thread_id = th.id
                            WHERE th.object_type = 'T'
                            LIMIT 5
                        """)
                        entry_samples = cursor.fetchall()
                        investigation['entry_samples'] = entry_samples
                    except Exception as e:
                        investigation['entry_query_error'] = str(e)
            
            cursor.close()
            
            return investigation
            
        except Exception as e:
            logger.error(f"Error investigando campo extra: {e}")
            return {'error': str(e)}


# Instancia global
_osticket_integration = None


def get_osticket_integration() -> OsTicketIntegration:
    """Obtiene la instancia global de integración con osTicket"""
    global _osticket_integration
    
    if _osticket_integration is None:
        _osticket_integration = OsTicketIntegration()
    
    return _osticket_integration


def test_osticket_integration() -> Dict[str, Any]:
    """Prueba la integración completa con osTicket"""
    try:
        integration = get_osticket_integration()
        
        # Verificar estado de conexión
        status = integration.get_osticket_status()
        
        if not status['connected']:
            return {
                'success': False,
                'error': 'No se pudo conectar con osTicket',
                'status': status
            }
        
        # Probar extracción de datos
        training_data = integration.generate_training_data()
        
        if training_data['success']:
            return {
                'success': True,
                'status': status,
                'training_data_summary': training_data['summary'],
                'message': f"Integración exitosa: {training_data['summary']['total_training_pairs']} pares de entrenamiento generados"
            }
        else:
            return {
                'success': False,
                'error': training_data.get('error', 'Error desconocido'),
                'status': status
            }
            
    except Exception as e:
        logger.error(f"Error en prueba de integración con osTicket: {e}")
        return {
            'success': False,
            'error': str(e),
            'details': 'Error inesperado durante la prueba'
        }
