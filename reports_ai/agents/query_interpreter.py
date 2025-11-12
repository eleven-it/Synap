"""
Agente Intérprete de Consulta (NLU de Dominio)
Traduce solicitud a intención de negocio estructurada
"""
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from .base import BaseAgent
from reports_ai.tools.glossary_tool import GlossaryTool

logger = logging.getLogger(__name__)


class QueryInterpreterAgent(BaseAgent):
    """
    Intérprete de Consulta - NLU de Dominio
    
    Extrae intención, periodo, filtros, granularidad y segmentaciones
    con definiciones alineadas al glosario funcional de Administranet
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="Intérprete de Consulta",
            model="gpt-4",
            temperature=0.2,  # Permite comprensión natural
            max_tokens=1000,
            **kwargs
        )
        
        self.glossary_tool = GlossaryTool()
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
        
        # Agregar historial (últimos 5 mensajes para no saturar el contexto)
        for hist_msg in self.message_history[-5:]:
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
        return """Eres Intérprete de Consulta de Administranet.

Tu objetivo es clasificar la consulta del usuario en uno de estos tipos:

1. REPORTE DE DATOS (report_*)
   - Usuario pide datos, métricas, listados
   - Ejemplos: "ventas de septiembre", "stock actual", "clientes activos"

2. PROCEDIMIENTO (procedure_query)
   - Usuario pregunta CÓMO funciona algo o pide explicación de un proceso
   - Palabras clave: "cómo crear", "cómo hacer", "pasos para", "procedimiento", "tutorial", "workflow", "flujo de trabajo", "proceso", "cual es el flujo", "desde... hasta"
   - Ejemplos: "cómo crear un pedido", "workflow desde pedido hasta entrega", "flujo de trabajo de ventas", "proceso de facturación"

3. AYUDA/DEFINICIÓN (help_query)
   - Usuario pregunta QUÉ ES algo
   - Palabras clave: "qué es", "qué significa", "para qué sirve", "explícame"
   - Ejemplos: "qué es un artículo discontinuado", "qué significa estado pendiente"

4. EXPORTACIÓN (export_request)
   - Usuario quiere descargar reporte previo
   - Palabras clave: "descargar", "exportar", "guardar", "dame en excel", "quiero en pdf"
   - Ejemplos: "descargar en excel", "exportar a pdf"

Produces un brief estructurado (JSON):
{
  "intent": "procedure_query|help_query|export_request|report_ventas|report_stock|...",
  "intent_category": "procedure|help|export|report",
  "entities": ["pedido", "cliente", ...],
  "action": "crear|modificar|consultar|eliminar|...",
  "export_format": "excel|pdf|null",
  
  // Solo para reportes (intent_category == "report"):
  "categoria": "ventas|inventario|clientes|cobranzas|finanzas|general",
  "periodo": {"desde": "YYYY-MM-DD", "hasta": "YYYY-MM-DD"},
  "filtros": {"campo": "valor", ...},
  "segmentaciones": ["sucursal", "linea_producto", ...],
  "granularidad": "diaria|mensual|trimestral|anual",
  "limites": {"top_n": 10, "min_valor": null}
}

Defaults para reportes:
- Periodo: últimos 12 meses si no se especifica
- Moneda: ARS
- Granularidad: mensual
- Top_n: 10

PROHIBIDO: nombres técnicos, tablas, campos SQL.
Solo lenguaje de negocio."""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        import time
        start_time = time.time()
        
        query = input_data.get('query', '')
        
        logger.info(
            f"\n{'='*70}\n"
            f"[{self.agent_name}] 🔍 INICIO DE INTERPRETACIÓN\n"
            f"{'='*70}\n"
            f"  📝 Query: {query}\n"
            f"  📊 Longitud: {len(query)} caracteres\n"
            f"{'='*70}"
        )
        
        messages = [
            {'role': 'system', 'content': self.get_system_prompt()},
            {'role': 'user', 'content': f"Consulta: {query}"}
        ]
        
        response = self._call_llm(messages)
        
        if not response['success']:
            duration = time.time() - start_time
            logger.error(
                f"[{self.agent_name}] ❌ FALLO EN INTERPRETACIÓN\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  🚫 Error: {response.get('error', 'Desconocido')}"
            )
            return {'success': False, 'agent': 'query_interpreter'}
        
        try:
            # Parsear JSON
            content = response['content']
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start >= 0 and end > start:
                brief = json.loads(content[start:end])
                
                # Aplicar defaults
                brief = self._apply_defaults(brief)
                
                duration = time.time() - start_time
                
                logger.info(
                    f"[{self.agent_name}] ✅ INTERPRETACIÓN EXITOSA\n"
                    f"  ⏱️  Duración Total: {duration:.2f}s\n"
                    f"  🎯 Intención: {brief.get('intencion', 'N/A')}\n"
                    f"  📂 Categoría: {brief.get('categoria', 'N/A')}\n"
                    f"  📅 Periodo: {brief.get('periodo', {}).get('desde', 'N/A')} → {brief.get('periodo', {}).get('hasta', 'N/A')}\n"
                    f"  🔍 Filtros: {len(brief.get('filtros', {}))} filtro(s)\n"
                    f"  📊 Granularidad: {brief.get('granularidad', 'N/A')}\n"
                    f"  🎚️  Segmentaciones: {', '.join(brief.get('segmentaciones', [])) or 'Ninguna'}\n"
                    f"  🔝 Top N: {brief.get('limites', {}).get('top_n', 'N/A')}"
                )
                
                return {
                    'success': True,
                    'brief': brief,
                    'agent': 'query_interpreter',
                    'duration': duration,
                    'tokens_used': response.get('tokens_used', 0)
                }
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{self.agent_name}] ❌ ERROR PARSEANDO BRIEF\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  🚫 Error: {type(e).__name__}: {str(e)}\n"
                f"  📄 Contenido recibido: {content[:200]}..."
            )
        
        return {'success': False, 'agent': 'query_interpreter'}
    
    def _apply_defaults(self, brief: Dict) -> Dict:
        """Aplica valores por defecto al brief"""
        if 'periodo' not in brief or not brief['periodo']:
            # Últimos 12 meses
            hasta = datetime.now()
            desde = hasta - timedelta(days=365)
            brief['periodo'] = {
                'desde': desde.strftime('%Y-%m-%d'),
                'hasta': hasta.strftime('%Y-%m-%d')
            }
        
        if 'granularidad' not in brief:
            brief['granularidad'] = 'mensual'
        
        if 'filtros' not in brief:
            brief['filtros'] = {}
        
        if 'limites' not in brief:
            brief['limites'] = {'top_n': 10}
        
        return brief

