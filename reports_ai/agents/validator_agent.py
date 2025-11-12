"""
Agente Validador/Compliance (Guardrails)
Asegura veracidad, coherencia, privacidad y cumplimiento de políticas
"""
import logging
from typing import Dict, Any
from .base import BaseAgent
from reports_ai.tools.validation_tool import ValidationTool

logger = logging.getLogger(__name__)


class ValidatorAgent(BaseAgent):
    """
    Validador - Control final de guardrails
    Bloquea salidas con tecnicismos, incoherencias o fuera de contexto
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="Validador",
            model="gpt-4",
            temperature=0.0,  # Máximo determinismo
            max_tokens=500,
            **kwargs
        )
        
        self.validation_tool = ValidationTool()
    
    def get_system_prompt(self) -> str:
        return """Eres Validador de Reportes de Administranet.

Bloqueas cualquier salida con:
- Tecnicismos (SQL, tablas, campos, código)
- Incoherencias temporales o numéricas
- Contenido fuera de Administranet
- Privacidad comprometida

Exiges:
- Periodo claro
- Redondeos correctos (2 decimales en moneda)
- Lenguaje de negocio exclusivamente

Respondes JSON:
{
  "aprobado": true/false,
  "observaciones": ["...", ...]
}
"""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        report_content = input_data.get('report', '')
        data_sources = input_data.get('data_sources', [])
        
        # Convertir a string si es dict
        if isinstance(report_content, dict):
            import json
            report_content = json.dumps(report_content, ensure_ascii=False)
        
        validation = self.validation_tool.validate_response(
            report_content,
            data_sources
        )
        
        return {
            'success': True,
            'approved': validation['is_valid'],
            'validation': validation,
            'agent': 'validator'
        }

