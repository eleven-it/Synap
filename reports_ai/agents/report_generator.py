"""
Agente Generador de Reportes (Narrativa de Negocio)
Transforma resultados y reglas en narrativa ejecutiva comprensible
"""
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import BaseAgent
from reports_ai.tools.validation_tool import ValidationTool

logger = logging.getLogger(__name__)


class ReportGeneratorAgent(BaseAgent):
    """
    Agente Generador de Reportes - Narrativa de Negocio
    
    Responsabilidades según documento:
    1. Construir Resumen Ejecutivo (2-4 bullets)
    2. Presentar KPIs con nombres funcionales
    3. Desgloses por dimensiones (sucursal, línea, segmento)
    4. Notas de interpretación en lenguaje de negocio
    5. Formateo: moneda 2 decimales, fechas DD/MM/YYYY, listas ordenadas
    6. Limitar extensión, solo lo accionable
    7. NUNCA incluir SQL, tablas, campos, rutas
    8. NUNCA citar código o símbolos
    9. No exponer razonamiento interno
    """
    
    def __init__(self, **kwargs):
        """Inicializa el Generador con temperature=0.2 (permite narrativa natural sin alterar hechos)"""
        super().__init__(
            agent_name="Generador de Reportes",
            model="gpt-4",
            temperature=0.2,
            max_tokens=3000,
            **kwargs
        )
        
        self.validation_tool = ValidationTool()
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
        
        # Agregar historial (últimos 5 mensajes - más contexto para narrativa)
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
        """System prompt del Generador según el documento"""
        return """Eres Generador de Reportes de Administranet Gestión.

Transformas resultados y reglas en una narrativa ejecutiva comprensible.

FORMATO DE SALIDA (siempre JSON):
{
  "resumen": [lista de 2-4 bullets con hallazgos clave],
  "metricas": {dict con KPIs en nombres funcionales},
  "desglose": [lista con dimensiones solicitadas],
  "periodo_cubierto": "DD/MM/YYYY al DD/MM/YYYY",
  "notas": [lista de notas de interpretación]
}

REGLAS ESTRICTAS:
1. Resumen ejecutivo: 2-4 bullets, hallazgos clave, tendencias, factores explicativos
2. KPIs: nombres funcionales ("ventas netas", "margen bruto estimado", "rotación de stock")
3. Desgloses: por dimensiones solicitadas (sucursal, línea, segmento, estado)
4. Notas: explicar definiciones aplicadas, supuestos, alcance temporal
5. Formateo:
   - Moneda: 2 decimales, separadores de miles (ej: "ARS 184.200,50")
   - Fechas: DD/MM/YYYY
   - Listas ordenadas cuando aplique
6. Brevedad: solo lo accionable, evitar sobrecarga de números
7. PROHIBIDO:
   - SQL, nombres de tablas/campos, rutas
   - Código o símbolos técnicos
   - Razonamiento interno o deliberaciones
   
TONO:
Ejecutivo, simple, directo, no técnico.

Ejemplo:
"Las ventas netas del periodo crecieron 8,4% respecto del mes anterior. 
La línea de Electrónica aportó el 62% del aumento, destacándose la sucursal Mendoza."
"""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera reporte en narrativa de negocio
        
        Args:
            input_data: {
                'data': dict/list,  # Datos del Analista
                'business_rules': list,  # Reglas del Intérprete de Lógica
                'intent': dict,  # Intención del NLU
                'periodo': dict (opcional)
            }
            
        Returns:
            Dict con reporte estructurado
        """
        start_time = time.time()
        
        data = input_data.get('data', {})
        business_rules = input_data.get('business_rules', [])
        intent = input_data.get('intent', {})
        periodo = input_data.get('periodo', {})
        
        logger.info(f"[Generador de Reportes] Generando narrativa para: {intent.get('category', 'general')}")
        
        try:
            # Construir prompt con todos los datos
            generation_prompt = self._build_generation_prompt(
                data, business_rules, intent, periodo
            )
            
            messages = [
                {
                    'role': 'system',
                    'content': self.get_system_prompt()
                },
                {
                    'role': 'user',
                    'content': generation_prompt
                }
            ]
            
            # Generar reporte
            response = self._call_llm(messages)
            
            if not response['success']:
                return {
                    'success': False,
                    'error': 'No se pudo generar el reporte',
                    'agent': 'report_generator'
                }
            
            # Parsear JSON del reporte
            report = self._parse_report(response['content'])
            
            if not report:
                return {
                    'success': False,
                    'error': 'Error parseando el reporte generado',
                    'agent': 'report_generator'
                }
            
            # Validar el reporte (guardrails)
            validation = self.validation_tool.validate_response(
                response['content'],
                data_sources=[{'type': 'mysql', 'data': data}]
            )
            
            if not validation['is_valid']:
                logger.warning(f"[Generador] Reporte con errores de validación: {validation['errors']}")
                # Aquí se podría regenerar o aplicar correcciones
            
            result = {
                'success': True,
                'report': report,
                'validation': {
                    'factual_confidence': validation['factual_confidence'],
                    'speculative_phrases_rate': validation['speculative_phrases_rate'],
                    'warnings': validation['warnings']
                },
                'processing_time': time.time() - start_time,
                'agent': 'report_generator'
            }
            
            # Registrar ejecución
            self.log_execution(
                input_summary=f"Categoría: {intent.get('category', 'N/A')}",
                output_summary=f"Reporte con {len(report.get('resumen', []))} puntos clave",
                success=True,
                duration=time.time() - start_time
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[Generador de Reportes] Error: {e}")
            
            self.log_execution(
                input_summary=f"Categoría: {intent.get('category', 'N/A')}",
                output_summary=f"Error: {str(e)}",
                success=False,
                duration=time.time() - start_time
            )
            
            return {
                'success': False,
                'error': str(e),
                'agent': 'report_generator'
            }
    
    def _build_generation_prompt(
        self,
        data: Any,
        business_rules: List[Dict],
        intent: Dict,
        periodo: Dict
    ) -> str:
        """
        Construye el prompt para generar el reporte
        
        Args:
            data: Datos del análisis
            business_rules: Reglas de negocio aplicables
            intent: Intención clasificada
            periodo: Periodo consultado
            
        Returns:
            Prompt completo
        """
        prompt_parts = []
        
        # Intención
        prompt_parts.append(f"Categoría: {intent.get('category', 'general')}")
        prompt_parts.append(f"Intención: {intent.get('intent', 'Consulta general')}")
        
        # Periodo
        if periodo:
            desde = periodo.get('desde', '')
            hasta = periodo.get('hasta', '')
            if desde and hasta:
                prompt_parts.append(f"Periodo: {desde} al {hasta}")
        else:
            prompt_parts.append("Periodo: No especificado (usar 'últimos 12 meses' como referencia)")
        
        # Datos
        prompt_parts.append("\n--- DATOS DISPONIBLES ---")
        if isinstance(data, dict):
            if 'summary' in data:
                prompt_parts.append(f"Resumen: {data['summary']}")
            if 'row_count' in data:
                prompt_parts.append(f"Cantidad de registros: {data['row_count']}")
            if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                # Mostrar primeros registros
                sample_data = data['data'][:5]
                prompt_parts.append(f"Muestra de datos: {sample_data}")
        elif isinstance(data, list):
            prompt_parts.append(f"Total de registros: {len(data)}")
            if len(data) > 0:
                prompt_parts.append(f"Muestra: {data[:5]}")
        
        # Reglas de negocio
        if business_rules:
            prompt_parts.append("\n--- REGLAS DE NEGOCIO APLICABLES ---")
            for rule in business_rules[:5]:  # Máximo 5 reglas
                prompt_parts.append(f"- {rule.get('name', 'N/A')}: {rule.get('description', '')}")
        
        # Instrucción final
        prompt_parts.append("\n--- INSTRUCCIÓN ---")
        prompt_parts.append("Genera el reporte en formato JSON según el template del sistema.")
        prompt_parts.append("Resalta hallazgos clave, tendencias y factores explicativos.")
        prompt_parts.append("Usa lenguaje ejecutivo, sin tecnicismos.")
        
        return '\n'.join(prompt_parts)
    
    def _parse_report(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parsea el JSON del reporte desde el contenido del LLM
        
        Args:
            content: Contenido de la respuesta
            
        Returns:
            Dict con reporte o None si falla
        """
        try:
            import json
            
            # Buscar JSON en el contenido
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                report = json.loads(json_str)
                
                # Validar estructura mínima
                required_keys = ['resumen', 'metricas', 'notas']
                if all(key in report for key in required_keys):
                    return report
            
            logger.warning("[Generador] No se pudo parsear JSON del reporte")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"[Generador] Error parseando JSON: {e}")
            return None
    
    def format_currency(self, amount: float, currency: str = "ARS") -> str:
        """
        Formatea un monto en formato de moneda
        
        Args:
            amount: Monto numérico
            currency: Código de moneda
            
        Returns:
            String formateado (ej: "ARS 1.234,56")
        """
        # Redondear a 2 decimales
        rounded = round(amount, 2)
        
        # Formatear con separadores
        formatted = f"{rounded:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return f"{currency} {formatted}"
    
    def format_percentage(self, value: float) -> str:
        """
        Formatea un porcentaje
        
        Args:
            value: Valor numérico (0.0 - 1.0 o 0 - 100)
            
        Returns:
            String formateado (ej: "15,5%")
        """
        # Si el valor es menor a 1, asumimos que es 0.0-1.0
        if value < 1.0:
            value = value * 100
        
        rounded = round(value, 1)
        return f"{rounded:,.1f}%".replace('.', ',')
    
    def format_date(self, date_obj) -> str:
        """
        Formatea una fecha
        
        Args:
            date_obj: Objeto datetime o string
            
        Returns:
            String en formato DD/MM/YYYY
        """
        if isinstance(date_obj, datetime):
            return date_obj.strftime('%d/%m/%Y')
        elif isinstance(date_obj, str):
            # Intentar parsear si es string
            try:
                dt = datetime.strptime(date_obj, '%Y-%m-%d')
                return dt.strftime('%d/%m/%Y')
            except:
                return date_obj
        return str(date_obj)

