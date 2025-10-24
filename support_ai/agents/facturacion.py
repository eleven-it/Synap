"""
Agente de Facturación - Especializado en problemas de facturación y AFIP
"""
import logging
from typing import Dict, List, Any
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class FacturacionAgent:
    """Agente especializado en problemas de facturación"""
    
    def __init__(self):
        self.specialized_keywords = [
            'factura', 'afip', 'iva', 'cuit', 'cae', 'caea', 'comprobante',
            'fiscal', 'impuesto', 'monotributo', 'responsable inscripto'
        ]
    
    def process(self, message: str, ticket, attachments: List = None) -> Dict[str, Any]:
        """Procesa consultas relacionadas con facturación"""
        message_lower = message.lower()
        
        # Detectar tipo de problema
        if any(word in message_lower for word in ['error', 'falla', 'no funciona']):
            return self._handle_error_problem(message)
        elif any(word in message_lower for word in ['configurar', 'configuración']):
            return self._handle_configuration_problem(message)
        elif any(word in message_lower for word in ['vencimiento', 'fecha']):
            return self._handle_date_problem(message)
        else:
            return self._handle_general_problem(message)
    
    def _handle_error_problem(self, message: str) -> Dict[str, Any]:
        """Maneja problemas de errores en facturación"""
        return {
            'message': _(
                "Entiendo que tienes un problema con la facturación. Para ayudarte mejor:\n"
                "• ¿Qué error específico estás viendo?\n"
                "• ¿En qué paso del proceso ocurre?\n"
                "• ¿Has verificado tu conexión con AFIP?"
            ),
            'confidence': 0.7,
            'suggestions': [
                _("Verificar conectividad con AFIP"),
                _("Revisar configuración de certificados"),
                _("Comprobar datos del cliente")
            ],
            'metadata': {'problem_type': 'facturacion_error'}
        }
    
    def _handle_configuration_problem(self, message: str) -> Dict[str, Any]:
        """Maneja problemas de configuración"""
        return {
            'message': _(
                "Para configurar la facturación correctamente:\n"
                "• Verifica que tu CUIT esté activo en AFIP\n"
                "• Asegúrate de tener los certificados instalados\n"
                "• Confirma que tu categoría fiscal sea correcta"
            ),
            'confidence': 0.8,
            'suggestions': [
                _("Revisar configuración AFIP"),
                _("Instalar certificados digitales"),
                _("Verificar categoría fiscal")
            ],
            'metadata': {'problem_type': 'facturacion_config'}
        }
    
    def _handle_date_problem(self, message: str) -> Dict[str, Any]:
        """Maneja problemas de fechas y vencimientos"""
        return {
            'message': _(
                "Los vencimientos de facturación dependen de tu categoría fiscal:\n"
                "• Monotributo: 20 de cada mes\n"
                "• Responsable Inscripto: según actividad\n"
                "• Consumidor Final: sin vencimiento"
            ),
            'confidence': 0.9,
            'suggestions': [
                _("Verificar categoría fiscal"),
                _("Consultar calendario AFIP"),
                _("Configurar recordatorios")
            ],
            'metadata': {'problem_type': 'facturacion_dates'}
        }
    
    def _handle_general_problem(self, message: str) -> Dict[str, Any]:
        """Maneja problemas generales de facturación"""
        return {
            'message': _(
                "Te ayudo con tu consulta de facturación. ¿Podrías especificar:\n"
                "• ¿Qué tipo de comprobante necesitas generar?\n"
                "• ¿Es para un cliente nuevo o existente?\n"
                "• ¿Tienes todos los datos del cliente?"
            ),
            'confidence': 0.6,
            'suggestions': [
                _("Generar factura A"),
                _("Generar factura B"),
                _("Generar factura C")
            ],
            'metadata': {'problem_type': 'facturacion_general'}
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene estado del agente"""
        return {
            'status': 'active',
            'specialization': 'facturacion',
            'keywords': self.specialized_keywords
        }
    
    def train(self, training_data: List[Dict]) -> bool:
        """Entrena el agente"""
        logger.info(f"Training facturacion agent with {len(training_data)} samples")
        return True 