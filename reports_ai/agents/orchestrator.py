"""
Agente Orquestador (Lead/Router)
Coordina el flujo extremo a extremo del sistema de reportes
"""
import logging
import time
from typing import Dict, List, Any, Optional
from .base import BaseAgent
from reports_ai.tools.validation_tool import ValidationTool

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    Agente Orquestador - Coordina todos los demás agentes
    
    Responsabilidades:
    1. Entender la intención del usuario
    2. Convocar agentes en el orden correcto
    3. Consolidar resultados
    4. Entregar respuesta de negocio clara y veraz
    5. Rechazar consultas fuera del contexto de Administranet
    """
    
    def __init__(self, **kwargs):
        """Inicializa el Orquestador con temperature=0.1 para máxima precisión"""
        super().__init__(
            agent_name="Orquestador",
            model="gpt-4",
            temperature=0.1,  # Más bajo que default para máximo determinismo
            max_tokens=3000,
            **kwargs
        )
        
        self.validation_tool = ValidationTool()
        
        # Referencias a otros agentes (se inyectarán después)
        self.query_interpreter = None
        self.data_analyst = None  # Puede ser original o V2
        self.data_analyst_v2 = None  # NUEVO: Data Analyst V2 independiente
        self.logic_interpreter = None
        self.report_generator = None
        self.validator = None
        
        # Configuración
        self.use_data_analyst_v2 = True  # Por defecto usar V2
        
        # Historial de conversación (se inyecta en execute)
        self.message_history = []
    
    def get_system_prompt(self) -> str:
        """System prompt del Orquestador según el documento"""
        return """Actúas como orquestador de un sistema de reportes de Administranet Gestión.

A partir de una intención de negocio, convocas a los agentes especializados en el orden correcto:
1. Intérprete de Consulta (NLU)
2. Intérprete de Lógica (reglas de negocio)
3. Analista de Datos (MySQL)
4. Generador de Reportes
5. Validador (control final)

PRINCIPIOS INNEGOCIABLES:
- Respondes SIEMPRE en lenguaje de negocio
- NUNCA expones SQL, nombres de tablas/campos, rutas, ni código
- TODO está limitado al contexto de Administranet Gestión
- Si algo es ambiguo, intentas resolverlo internamente
- Si es imprescindible, pides precisión en términos de negocio
- Rechazas amable y brevemente lo que no esté en el contexto de Administranet
- Mantienes coherencia con el historial de la conversación
- Puedes referenciar información de mensajes anteriores

Tu salida final es clara, breve, veraz y accionable."""
    
    def _build_messages_with_history(self, current_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Construye la lista de mensajes incluyendo el historial de conversación
        
        Args:
            current_messages: Mensajes actuales (system + user)
            
        Returns:
            Lista completa de mensajes con historial
        """
        if not self.message_history:
            return current_messages
        
        # Separar system prompt del resto
        system_prompt = None
        other_messages = []
        
        for msg in current_messages:
            if msg['role'] == 'system':
                system_prompt = msg
            else:
                other_messages.append(msg)
        
        # Construir lista final: system + historial + current
        final_messages = []
        
        if system_prompt:
            final_messages.append(system_prompt)
        
        # Agregar historial (últimos 10 mensajes)
        for hist_msg in self.message_history[-10:]:
            final_messages.append({
                'role': hist_msg['role'],
                'content': hist_msg['content']
            })
        
        # Agregar mensajes actuales (sin system prompt)
        final_messages.extend(other_messages)
        
        return final_messages
    
    def _inject_history_to_agents(self):
        """Inyecta el historial de conversación a todos los agentes"""
        agents_to_inject = [
            self.query_interpreter,
            self.data_analyst,
            self.logic_interpreter,
            self.report_generator
        ]
        
        for agent in agents_to_inject:
            if agent and hasattr(agent, 'message_history'):
                agent.message_history = self.message_history
    
    def _call_llm(self, messages: List[Dict[str, str]], **override_params) -> Dict[str, Any]:
        """
        Sobrescribe _call_llm para incluir historial de conversación
        
        Args:
            messages: Mensajes actuales
            **override_params: Parámetros opcionales
            
        Returns:
            Respuesta del LLM
        """
        # Construir mensajes con historial
        messages_with_history = self._build_messages_with_history(messages)
        
        # Llamar al método padre
        return super()._call_llm(messages_with_history, **override_params)
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta el flujo completo de generación de reporte
        
        Args:
            input_data: {
                'query': str,  # Consulta del usuario
                'context': dict (opcional),  # Contexto adicional
                'conversation_context': dict (opcional)  # Historial de conversación
            }
            
        Returns:
            Dict con reporte generado o error
        """
        start_time = time.time()
        
        query = input_data.get('query', '')
        context = input_data.get('context', {})
        conversation_context = input_data.get('conversation_context', {})
        
        # Extraer historial de mensajes para contexto del LLM
        self.message_history = conversation_context.get('message_history', [])
        
        logger.info(f"[Orquestador] Iniciando procesamiento de: {query[:100]}...")
        
        try:
            # Paso 1: Verificar que sea sobre Administranet
            if not self._is_administranet_context(query):
                return self._reject_out_of_scope(query)
            
            # Paso 2: Clasificar intención
            intent_classification = self._classify_intent(query)
            
            if not intent_classification['success']:
                return {
                    'success': False,
                    'error': 'No se pudo clasificar la intención de la consulta',
                    'agent': 'orchestrator'
                }
            
            # Paso 3: Invocar agentes en secuencia
            # Inyectar historial a los agentes
            self._inject_history_to_agents()
            
            # 3.1: Intérprete de Consulta (PRIMERO - clasifica el tipo de intent)
            if self.query_interpreter:
                logger.info(f"[Orquestador] Invocando Intérprete de Consulta")
                nlu_result = self.query_interpreter.execute({'query': query})
                brief = nlu_result.get('brief', {}) if nlu_result.get('success') else {}
            else:
                # Fallback: usar clasificación básica
                brief = {
                    'intencion': intent_classification['intent'],
                    'categoria': intent_classification['category'],
                    'intent_category': 'report',  # Asumir reporte si no hay NLU
                    'periodo': {},
                    'filtros': {},
                    'segmentaciones': [],
                    'granularidad': 'mensual',
                    'limites': {'top_n': 10}
                }
            
            # 3.2: ENRUTAMIENTO según tipo de intent (ANTES de procesar datos)
            intent = brief.get('intent', brief.get('intencion', ''))
            intent_category = brief.get('intent_category', 'report')
            
            logger.info(f"[Orquestador] Intent clasificado: {intent} (categoría: {intent_category})")
            
            # Enrutar según tipo de intent
            if intent_category == 'procedure' or intent == 'procedure_query':
                return self._handle_procedure_query(brief, query, time.time() - start_time)
            
            elif intent_category == 'help' or intent == 'help_query':
                return self._handle_help_query(brief, query, time.time() - start_time)
            
            elif intent_category == 'export' or intent == 'export_request':
                return self._handle_export_request(brief, conversation_context, time.time() - start_time)
            
            # Si llegamos aquí, es un REPORTE DE DATOS → continuar con flujo normal
            # 3.3: Intérprete de Lógica (reglas de negocio)
            business_rules = []
            # Mapa de persistencia para el Analista de Datos
            persistence_map = {}
            
            if self.logic_interpreter:
                logger.info(f"[Orquestador] Invocando Intérprete de Lógica")
                logic_result = self.logic_interpreter.execute({
                    'intent': {'category': brief.get('categoria', 'general')},
                    'query': query
                })
                if logic_result.get('success'):
                    business_rules = logic_result.get('rules', [])
                    persistence_map = logic_result.get('persistence_map', {})
            
            # 3.3: Analista de Datos (consulta MySQL)
            data_result = {}
            
            # NUEVO: Usar Data Analyst V2 si está disponible y configurado
            if self.use_data_analyst_v2 and self.data_analyst_v2:
                logger.info(f"[Orquestador] Invocando Data Analyst V2 (independiente)")
                
                # Cargar active learnings si están disponibles
                if hasattr(self.data_analyst_v2, 'load_active_learnings'):
                    try:
                        self.data_analyst_v2.load_active_learnings()
                    except Exception as e:
                        logger.warning(f"[Orquestador] Error cargando active learnings: {e}")
                
                data_result = self.data_analyst_v2.execute({
                    'query': query,
                    'periodo': brief.get('periodo', {}),
                    'filters': brief.get('filtros', {}),
                    'limit': brief.get('limites', {}).get('top_n', 100),
                    # NO pasar persistence_map (V2 es independiente)
                })
                
                if not data_result.get('success'):
                    logger.warning(f"[Orquestador] Error en Data Analyst V2: {data_result.get('error')}")
            
            # Fallback: Usar Data Analyst original si V2 no está disponible
            elif self.data_analyst:
                logger.info(f"[Orquestador] Invocando Data Analyst original con mapa de persistencia")
                data_result = self.data_analyst.execute({
                    'query': query,
                    'periodo': brief.get('periodo', {}),
                    'filters': brief.get('filtros', {}),
                    'limit': brief.get('limites', {}).get('top_n', 100),
                    'persistence_map': persistence_map  # Pasar mapa de persistencia
                })
                
                if not data_result.get('success'):
                    logger.warning(f"[Orquestador] Error en Analista de Datos original: {data_result.get('error')}")
            
            # 3.4: Generador de Reportes (solo para consultas complejas)
            # Para consultas simples (listados), usar datos directamente sin procesamiento adicional
            report = {}
            validation = {'is_valid': True, 'warnings': []}
            
            # Detectar si es consulta simple (listado)
            is_simple_listing = self._is_simple_listing_query(query, brief, data_result)
            
            if is_simple_listing and data_result.get('success'):
                # Consulta simple: usar datos directamente sin ReportGenerator
                logger.info(f"[Orquestador] Consulta simple detectada, omitiendo ReportGenerator")
                report = {
                    'data': data_result.get('data', []),
                    'row_count': data_result.get('row_count', 0)
                }
            elif self.report_generator and data_result.get('success'):
                logger.info(f"[Orquestador] Invocando Generador de Reportes")
                report_result = self.report_generator.execute({
                    'data': data_result,
                    'business_rules': business_rules,
                    'intent': brief,
                    'periodo': brief.get('periodo', {})
                })
                
                if report_result.get('success'):
                    report = report_result.get('report', {})
                    
                    # 3.5: Validador (solo para reportes complejos)
                    if self.validator and report:
                        logger.info(f"[Orquestador] Invocando Validador")
                        validation_result = self.validator.execute({
                            'report': report,
                            'data_sources': [data_result] if data_result.get('success') else []
                        })
                        
                        if validation_result.get('success'):
                            validation = validation_result.get('validation', {})
                            
                            if not validation.get('approved', True):
                                logger.warning(f"[Orquestador] Reporte no aprobado: {validation.get('observaciones')}")
            else:
                # Fallback: reporte simple sin datos
                report = self._generate_placeholder_report(query, intent_classification)
            
            # Si no hay datos o reporte generado, crear respuesta informativa
            # Verificar que el reporte tenga contenido útil
            has_content = (
                (report.get('data') and len(report.get('data', [])) > 0) or
                (report.get('resumen')) or 
                (report.get('metricas')) or 
                (report.get('narrativa'))
            )
            
            if not has_content:
                # Fallback: Generar respuesta general con LLM
                return self._generate_general_response(query, brief, business_rules, time.time() - start_time)
            
            # REPORTE DE DATOS (flujo existente)
            result = {
                'success': True,
                'intent': brief.get('intencion', intent_classification['intent']),
                'category': brief.get('categoria', intent_classification['category']),
                'report': report,
                'validation': validation,
                'processing_time': time.time() - start_time,
                'agent': 'orchestrator'
            }
            
            # Registrar ejecución
            self.log_execution(
                input_summary=query[:100],
                output_summary=str(result)[:100],
                success=True,
                duration=time.time() - start_time
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[Orquestador] Error: {e}")
            
            self.log_execution(
                input_summary=query[:100],
                output_summary=f"Error: {str(e)}",
                success=False,
                duration=time.time() - start_time
            )
            
            return {
                'success': False,
                'error': str(e),
                'agent': 'orchestrator'
            }
    
    def _is_administranet_context(self, query: str) -> bool:
        """
        Verifica si la consulta está en el contexto de Administranet
        
        Args:
            query: Consulta del usuario
            
        Returns:
            True si es sobre Administranet
        """
        # Palabras clave relacionadas con Administranet
        administranet_keywords = [
            'venta', 'cliente', 'producto', 'articulo', 'stock', 'inventario',
            'pedido', 'factura', 'cobranza', 'sucursal', 'proveedor',
            'margen', 'precio', 'descuento', 'comision', 'caja',
            'administranet', 'gestión', 'negocio'
        ]
        
        query_lower = query.lower()
        
        # Si contiene al menos una palabra clave, se considera válido
        for keyword in administranet_keywords:
            if keyword in query_lower:
                return True
        
        # Verificación con LLM para casos ambiguos
        messages = [
            {
                'role': 'system',
                'content': 'Eres un clasificador. Responde SOLO "SI" o "NO". '
                           '¿La siguiente consulta está relacionada con gestión empresarial, '
                           'ventas, inventario, clientes, facturación o Administranet?'
            },
            {
                'role': 'user',
                'content': query
            }
        ]
        
        response = self._call_llm(messages, max_tokens=10, temperature=0.0)
        
        if response['success']:
            answer = response['content'].strip().upper()
            return answer.startswith('SI') or answer.startswith('YES')
        
        # En caso de duda, rechazar (principio conservador)
        return False
    
    def _reject_out_of_scope(self, query: str) -> Dict[str, Any]:
        """
        Rechaza cortésmente consultas fuera de contexto
        
        Args:
            query: Consulta fuera de contexto
            
        Returns:
            Dict con mensaje de rechazo
        """
        return {
            'success': False,
            'error': 'Esta consulta no está relacionada con Administranet Gestión.',
            'message': (
                'Lo siento, solo puedo responder consultas sobre '
                'Administranet Gestión: ventas, clientes, inventario, '
                'facturación, cobranzas y gestión empresarial. '
                '¿Podrías reformular tu pregunta en ese contexto?'
            ),
            'agent': 'orchestrator'
        }
    
    def _classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Clasifica la intención de la consulta
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Dict con intención clasificada
        """
        messages = [
            {
                'role': 'system',
                'content': self.get_system_prompt() + '\n\n' +
                           'Clasifica la intención de la consulta en UNA de estas categorías:\n'
                           '- ventas\n'
                           '- inventario\n'
                           '- clientes\n'
                           '- cobranzas\n'
                           '- finanzas\n'
                           '- general\n\n'
                           'Responde en formato JSON: {"category": "...", "intent": "descripción breve"}'
            },
            {
                'role': 'user',
                'content': f"Consulta: {query}"
            }
        ]
        
        response = self._call_llm(messages, max_tokens=100)
        
        if not response['success']:
            return {'success': False}
        
        try:
            import json
            content = response['content']
            
            # Extraer JSON del contenido (puede venir con texto adicional)
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                result = json.loads(json_str)
                
                return {
                    'success': True,
                    'category': result.get('category', 'general'),
                    'intent': result.get('intent', query[:100])
                }
            
        except Exception as e:
            logger.error(f"Error parseando clasificación de intención: {e}")
        
        # Fallback: clasificación por defecto
        return {
            'success': True,
            'category': 'general',
            'intent': query[:100]
        }
    
    def _generate_placeholder_report(
        self,
        query: str,
        intent_classification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera un reporte placeholder hasta que los otros agentes estén implementados
        
        Args:
            query: Consulta original
            intent_classification: Clasificación de intención
            
        Returns:
            Dict con reporte placeholder
        """
        return {
            'resumen': [
                f"Solicitud clasificada como: {intent_classification['category']}",
                "El sistema de reportes está procesando tu consulta.",
                "Próximamente se implementarán los agentes especializados para análisis completo."
            ],
            'metricas': {
                'categoria': intent_classification['category'],
                'intencion': intent_classification['intent']
            },
            'notas': [
                "Este es un reporte preliminar del sistema de Reportes AI.",
                "Los agentes especializados se están desarrollando según las especificaciones."
            ]
        }
    
    def _handle_procedure_query(self, brief: Dict, query: str, duration: float) -> Dict:
        """
        Maneja consultas de procedimientos ("Cómo crear un pedido?")
        Enruta al Logic Interpreter para buscar en Business Rules
        """
        entities = brief.get('entities', [])
        action = brief.get('action')
        
        entity = entities[0] if entities else None
        
        if not entity:
            return {
                'success': False,
                'type': 'clarification',
                'message': 'No pude identificar sobre qué quieres saber el procedimiento. ¿Puedes ser más específico?',
                'suggestions': ['pedido', 'factura', 'cliente', 'artículo', 'stock'],
                'processing_time': duration
            }
        
        # Buscar procedimiento en Business Rules
        if self.logic_interpreter:
            procedure_result = self.logic_interpreter.find_business_procedure(entity, action)
            
            if procedure_result.get('success'):
                return {
                    'success': True,
                    'type': 'procedure',
                    'content': procedure_result['procedure'],
                    'metadata': {
                        'rule_name': procedure_result.get('rule_name'),
                        'description': procedure_result.get('description'),
                        'source': f"{procedure_result.get('source_file', 'N/A')} - {procedure_result.get('source_function', 'N/A')}",
                        'category': procedure_result.get('category'),
                        'tags': procedure_result.get('tags')
                    },
                    'processing_time': duration
                }
            else:
                return {
                    'success': False,
                    'type': 'not_found',
                    'message': procedure_result.get('message', f'No encontré procedimiento para "{entity}"'),
                    'suggestion': procedure_result.get('suggestion', 'Intenta con: pedido, factura, cliente, artículo'),
                    'processing_time': duration
                }
        else:
            return {
                'success': False,
                'type': 'error',
                'message': 'El módulo de procedimientos no está disponible',
                'processing_time': duration
            }
    
    def _handle_help_query(self, brief: Dict, query: str, duration: float) -> Dict:
        """
        Maneja consultas de ayuda ("Qué es un artículo discontinuado?")
        Busca definiciones en el Glosario
        """
        from ..models import GlossaryTerm
        
        entities = brief.get('entities', [])
        entity = entities[0] if entities else None
        
        if not entity:
            return {
                'success': False,
                'type': 'clarification',
                'message': '¿Sobre qué término necesitas ayuda?',
                'processing_time': duration
            }
        
        # Buscar en glosario
        term = GlossaryTerm.objects.filter(
            term__icontains=entity,
            is_active=True
        ).first()
        
        if term:
            return {
                'success': True,
                'type': 'help',
                'content': term.definition,
                'metadata': {
                    'term': term.term,
                    'category': term.category,
                    'synonyms': term.synonyms,
                    'examples': term.examples
                },
                'processing_time': duration
            }
        else:
            return {
                'success': False,
                'type': 'not_found',
                'message': f'No encontré definición para "{entity}" en el glosario',
                'suggestion': 'Puedo ayudarte con términos del glosario de administraNET',
                'processing_time': duration
            }
    
    def _generate_general_response(self, query: str, brief: Dict, business_rules: List, duration: float) -> Dict:
        """
        Genera una respuesta general cuando no hay datos o no es un reporte típico
        Usa el LLM para responder de forma informativa
        """
        # Construir contexto para el LLM
        context_parts = [f"Consulta del usuario: {query}"]
        
        if brief:
            context_parts.append(f"Categoría detectada: {brief.get('categoria', 'general')}")
            if brief.get('entities'):
                context_parts.append(f"Entidades: {', '.join(brief.get('entities', []))}")
        
        if business_rules:
            context_parts.append(f"\nReglas de negocio relevantes encontradas: {len(business_rules)}")
            for rule in business_rules[:3]:  # Máximo 3 reglas
                if rule.get('description'):
                    context_parts.append(f"- {rule['description']}")
        
        context_str = "\n".join(context_parts)
        
        # Generar respuesta con LLM
        messages = [
            {
                'role': 'system',
                'content': """Eres un asistente AI de Administranet Gestión.

Responde la consulta del usuario de forma clara y útil, usando SOLO lenguaje de negocio.

PRINCIPIOS:
- Si preguntan por un proceso o workflow, explica los pasos principales del flujo de trabajo
- Si preguntan sobre datos que no tienes, sugiere qué información específica necesitas
- Si es ambiguo, pide aclaración de forma amable
- NUNCA menciones tablas, campos SQL, código o detalles técnicos
- Mantén un tono profesional y ejecutivo
- Sé específico sobre procesos de administración comercial (pedidos, facturación, entregas, stock)

Si no sabes la respuesta exacta, reconócelo y ofrece ayuda relacionada."""
            },
            {
                'role': 'user',
                'content': context_str
            }
        ]
        
        response = self._call_llm(messages, max_tokens=500, temperature=0.3)
        
        if response['success']:
            return {
                'success': True,
                'type': 'general_response',
                'content': response['content'],
                'metadata': {
                    'category': brief.get('categoria', 'general'),
                    'entities': brief.get('entities', []),
                    'rules_found': len(business_rules)
                },
                'processing_time': duration
            }
        else:
            return {
                'success': False,
                'type': 'error',
                'message': 'No pude procesar tu consulta. ¿Podrías reformularla?',
                'processing_time': duration
            }
    
    def _is_simple_listing_query(self, query: str, brief: Dict, data_result: Dict) -> bool:
        """
        Detecta si es una consulta simple de listado (ej: "dame los clientes que...")
        
        Args:
            query: Query original del usuario
            brief: Brief del NLU
            data_result: Resultado del Data Analyst
            
        Returns:
            True si es un listado simple, False si requiere análisis complejo
        """
        query_lower = query.lower()
        
        # Palabras clave que indican listado simple
        listing_keywords = [
            'dame', 'muestra', 'lista', 'listado', 'buscar', 'busca',
            'que se llamen', 'que se llaman', 'que contengan', 'que tengan',
            'nombre', 'llamado', 'llamada'
        ]
        
        # Si la consulta contiene palabras de listado
        has_listing_keyword = any(keyword in query_lower for keyword in listing_keywords)
        
        # Si hay datos y son una lista simple (no requiere análisis complejo)
        has_simple_data = (
            data_result.get('success') and 
            isinstance(data_result.get('data'), list) and
            len(data_result.get('data', [])) > 0
        )
        
        # Si la intención es simple búsqueda/listado
        intent_category = brief.get('intent_category', 'report')
        intent = brief.get('intent', brief.get('intencion', ''))
        is_simple_intent = (
            'buscar' in intent.lower() or 
            'listado' in intent.lower() or
            'lista' in intent.lower()
        )
        
        # Es listado simple si tiene keyword + datos simples + intención simple
        return has_listing_keyword and has_simple_data and (is_simple_intent or intent_category == 'report')
    
    def _handle_export_request(self, brief: Dict, conversation_context: Optional[Dict], duration: float) -> Dict:
        """
        Maneja solicitudes de exportación ("Descargar en Excel")
        Requiere un reporte previo en el contexto
        """
        export_format = brief.get('export_format', 'excel')
        
        # Verificar que hay un reporte previo
        if not conversation_context or not conversation_context.get('last_report'):
            return {
                'success': False,
                'type': 'clarification',
                'message': 'No hay ningún reporte para exportar. ¿Qué información necesitas?',
                'processing_time': duration
            }
        
        last_report = conversation_context['last_report']
        
        return {
            'success': True,
            'type': 'export_options',
            'report_id': last_report['id'],
            'message': '¿En qué formato quieres el reporte?',
            'options': ['Excel', 'PDF'],
            'metadata': {
                'last_report_query': last_report.get('query'),
                'has_data': last_report.get('has_data', False)
            },
            'processing_time': duration
        }
    
    def set_agents(
        self,
        query_interpreter=None,
        data_analyst=None,
        data_analyst_v2=None,
        logic_interpreter=None,
        report_generator=None,
        validator=None,
        use_data_analyst_v2=True
    ):
        """
        Inyecta las referencias a los otros agentes
        
        Args:
            query_interpreter: Agente NLU
            data_analyst: Agente de datos (original)
            data_analyst_v2: Agente de datos V2 (independiente)
            logic_interpreter: Agente de lógica
            report_generator: Agente generador
            validator: Agente validador
        """
        self.query_interpreter = query_interpreter
        self.data_analyst = data_analyst
        self.data_analyst_v2 = data_analyst_v2
        self.logic_interpreter = logic_interpreter
        self.report_generator = report_generator
        self.validator = validator
        self.use_data_analyst_v2 = use_data_analyst_v2
        
        logger.info("[Orquestador] Agentes especializados configurados")

