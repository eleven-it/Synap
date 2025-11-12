"""
Agente Intérprete de Lógica de Negocio (Code Insight VB6/PHP) - VERSIÓN ENRIQUECIDA
Deriva reglas de negocio y genera mapa de persistencia del análisis estático de código
"""
import logging
import time
from typing import Dict, List, Any, Optional
from django.db import models
from .base import BaseAgent
from reports_ai.tools.vb6_analyzer import VB6AnalyzerTool
from reports_ai.tools.vb6_form_analyzer import VB6FormAnalyzer
from reports_ai.models import BusinessRule

logger = logging.getLogger(__name__)


class LogicInterpreterAgent(BaseAgent):
    """
    Intérprete de Lógica - VERSIÓN ENRIQUECIDA
    
    Analiza formularios VB6/PHP para crear mapas de persistencia
    y sugerir tablas/campos al Analista de Datos (solo interno)
    
    NUNCA expone nombres técnicos al usuario
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="Intérprete de Lógica",
            model="gpt-4",
            temperature=0.1,
            max_tokens=2000,
            top_p=0.85,
            **kwargs
        )
        
        self.vb6_analyzer = VB6AnalyzerTool()
        self.form_analyzer = VB6FormAnalyzer()  # NUEVO: Analizador de formularios
        self.message_history = []
    
    def _build_messages_with_history(self, current_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Construye mensajes incluyendo historial de conversación"""
        if not self.message_history:
            return current_messages
        
        # Separar system prompt
        system_prompt = None
        other_messages = []
        
        for msg in current_messages:
            if msg['role'] == 'system':
                system_prompt = msg
            else:
                other_messages.append(msg)
        
        # Construir lista final
        final_messages = []
        if system_prompt:
            final_messages.append(system_prompt)
        
        # Agregar historial (últimos 3 mensajes)
        for hist_msg in self.message_history[-3:]:
            final_messages.append({
                'role': hist_msg['role'],
                'content': hist_msg['content']
            })
        
        final_messages.extend(other_messages)
        return final_messages
    
    def _call_llm(self, messages: List[Dict[str, str]], **override_params) -> Dict[str, Any]:
        """Sobrescribe _call_llm para incluir historial"""
        messages_with_history = self._build_messages_with_history(messages)
        return super()._call_llm(messages_with_history, **override_params)
    
    def get_system_prompt(self) -> str:
        return """Eres Intérprete de Lógica de Negocio de Administranet - VERSIÓN ENRIQUECIDA.

RESPONSABILIDADES:
1. Analizar formularios VB6/PHP para inferir entidades funcionales
2. Mapear entidades a tablas de persistencia candidatas
3. Sugerir campos clave y relaciones
4. Extraer reglas funcionales en lenguaje de negocio
5. Calcular scores de confianza para evitar alucinaciones

SALIDA (SOLO para uso interno de otros agentes):
{
  "entidades_funcionales": ["cliente", "pedido", "articulo"],
  "tablas_sugeridas": [
    {"nombre": "articulo", "rol": "catalogo", "confianza": 0.92,
     "campos_clave_sugeridos": ["IDArt", "NombreArticulo", "saldo_articulo"]}
  ],
  "relaciones_candidatas": [],
  "reglas_funcionales_resumidas": [
    "Un artículo tiene stock actual (saldo_articulo)",
    "El stock se valida antes de confirmar una venta"
  ]
}

ANTI-ALUCINACIÓN:
- Solo sugerir tablas/campos con evidencia del formulario o schema
- Confianza >= 0.80 para incluir en tablas_sugeridas
- Si confianza < 0.80, marcar como "en revisión"
- Nunca inventar nombres sin respaldo

PROHIBIDO EXPONER AL USUARIO:
- Nombres de tablas/campos
- Rutas de archivos
- Código VB6/PHP
- Consultas SQL

Todo lo técnico queda ESTRICTAMENTE INTERNO.
"""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta análisis de lógica de negocio y genera mapa de persistencia
        
        Args:
            input_data: {
                'intent': dict con intención y categoría,
                'query': str (opcional)
            }
            
        Returns:
            Dict con reglas de negocio Y mapa de persistencia
        """
        start_time = time.time()
        
        intent = input_data.get('intent', {})
        category = intent.get('category', 'general')
        query = input_data.get('query', '')
        
        logger.info(
            f"\n{'='*70}\n"
            f"[{self.agent_name}] 📖 INICIO DE INTERPRETACIÓN DE LÓGICA\n"
            f"{'='*70}\n"
            f"  🎯 Query: {query[:100]}...\n"
            f"  📂 Categoría: {category}\n"
            f"{'='*70}"
        )
        
        try:
            # Paso 1: Analizar formularios VB6 para mapa de persistencia
            logger.info(f"[{self.agent_name}] 🔧 PASO 1: Analizando formularios VB6")
            form_analysis = self.form_analyzer.analyze_forms_for_intent(query, category)
            
            # Paso 2: Extraer reglas del código VB6
            logger.info(f"[{self.agent_name}] 🔧 PASO 2: Extrayendo reglas de código VB6")
            vb6_rules = self.vb6_analyzer.extract_business_rules(category)
            
            # Paso 3: Buscar reglas existentes en BD
            logger.info(f"[{self.agent_name}] 🔧 PASO 3: Consultando reglas en BD")
            db_rules = list(BusinessRule.objects.filter(
                module__iexact=category,
                is_active=True
            ).values('name', 'description', 'conditions', 'actions', 'category'))
            
            # Paso 4: Consolidar todo
            logger.info(f"[{self.agent_name}] 🔧 PASO 4: Consolidando información")
            
            # Combinar reglas de todas las fuentes
            all_rules = db_rules + vb6_rules.get('rules', [])
            
            # Agregar reglas de formularios al mapa
            form_rules = form_analysis.get('reglas_funcionales_resumidas', [])
            for rule in form_rules:
                all_rules.append({
                    'name': 'Regla de formulario',
                    'description': rule,
                    'category': category
                })
            
            # Construir mapa de persistencia completo
            persistence_map = {
                'entidades_funcionales': form_analysis.get('entidades_funcionales', []),
                'tablas_sugeridas': form_analysis.get('tablas_sugeridas', []),
                'relaciones_candidatas': form_analysis.get('relaciones_candidatas', []),
                'reglas_funcionales_resumidas': form_analysis.get('reglas_funcionales_resumidas', []),
                'vigencia_reglas': form_analysis.get('vigencia_reglas', {}),
                'notas': form_analysis.get('notas', []),
                'para': 'analista_datos',
                'categoria': category
            }
            
            duration = time.time() - start_time
            
            logger.info(
                f"[{self.agent_name}] ✅ LÓGICA INTERPRETADA\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  📚 Reglas de negocio: {len(all_rules)}\n"
                f"  🏷️  Entidades: {len(persistence_map['entidades_funcionales'])}\n"
                f"  🗄️  Tablas sugeridas: {len(persistence_map['tablas_sugeridas'])}\n"
                f"  🔗 Relaciones: {len(persistence_map['relaciones_candidatas'])}"
            )
            
            return {
                'success': True,
                'rules': all_rules,
                'count': len(all_rules),
                'persistence_map': persistence_map,  # NUEVO: Mapa de persistencia
                'agent': 'logic_interpreter',
                'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{self.agent_name}] ❌ ERROR EN INTERPRETACIÓN\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  🚫 Error: {type(e).__name__}: {str(e)}"
            )
            
            return {
                'success': False,
                'error': str(e),
                'rules': [],
                'count': 0,
                'persistence_map': {},
                'agent': 'logic_interpreter'
            }
    
    def find_business_procedure(
        self,
        entity: str,
        action: Optional[str] = None
    ) -> Dict:
        """
        Busca procedimientos de negocio en las Business Rules
        Para responder preguntas como "¿Cómo crear un pedido?"
        
        Args:
            entity: Entidad de negocio (pedido, factura, cliente, artículo)
            action: Acción opcional (crear, modificar, eliminar)
        
        Returns:
            Dict con el procedimiento encontrado o mensaje de no disponible
        """
        from ..models import BusinessRule
        
        try:
            # Buscar reglas que mencionen la entidad
            rules = BusinessRule.objects.filter(
                is_active=True,
                business_procedure__isnull=False
            ).exclude(business_procedure='')
            
            # Filtrar por entidad (en tags o description)
            entity_lower = entity.lower()
            rules = rules.filter(
                models.Q(tags__icontains=entity_lower) |
                models.Q(description__icontains=entity_lower) |
                models.Q(name__icontains=entity_lower)
            )
            
            if rules.exists():
                # PRIORIDAD 1: Manual de Usuario (SIN filtrar por acción para no excluirlo)
                # Los manuales tienen nombres genéricos como "Manual de Usuario: Pedido"
                # NO contienen "crear", "modificar", etc. en el nombre
                user_manual_rules = rules.filter(
                    models.Q(tags__icontains='manual') |
                    models.Q(tags__icontains='usuario') |
                    models.Q(name__icontains='Manual de Usuario')
                )
                
                if user_manual_rules.exists():
                    # Usar manual de usuario (procedimiento para usuario final)
                    rule = user_manual_rules.first()
                else:
                    # PRIORIDAD 2: Procedimiento técnico (filtrar por acción si se especificó)
                    # Estos sí tienen "crear", "modificar", etc. en el nombre
                    if action:
                        action_lower = action.lower()
                        action_rules = rules.filter(
                            models.Q(description__icontains=action_lower) |
                            models.Q(name__icontains=action_lower) |
                            models.Q(tags__icontains=action_lower)
                        )
                        
                        if action_rules.exists():
                            rule = action_rules.first()
                        else:
                            # Fallback: cualquier regla técnica de la entidad
                            rule = rules.first()
                    else:
                        # Sin acción específica: primera regla técnica disponible
                        rule = rules.first()
                
                return {
                    'success': True,
                    'procedure': rule.business_procedure,
                    'rule_name': rule.name,
                    'description': rule.description,
                    'source_file': rule.source_file,
                    'source_function': rule.source_function,
                    'category': rule.category,
                    'tags': rule.tags,
                    'agent': 'logic_interpreter'
                }
            else:
                return {
                    'success': False,
                    'message': f'No se encontró procedimiento para "{entity}"' + (f' ({action})' if action else ''),
                    'suggestion': 'Intenta con: cliente, pedido, factura, artículo, stock',
                    'agent': 'logic_interpreter'
                }
        
        except Exception as e:
            logger.error(f"[{self.agent_name}] Error buscando procedimiento: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent': 'logic_interpreter'
            }
