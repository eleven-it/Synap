"""
Agente de Ventas - Especializado en problemas de ventas
"""
import logging
from typing import Dict, List, Any
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class VentasAgent:
    """Agente especializado en problemas de ventas"""
    
    def __init__(self):
        self.specialized_keywords = [
            'venta', 'vender', 'cliente', 'prospecto', 'cotización', 'presupuesto',
            'pedido', 'orden', 'carrito', 'checkout', 'pago'
        ]
    
    def process(self, message: str, ticket, attachments: List = None) -> Dict[str, Any]:
        """Procesa consultas de ventas"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['cliente', 'prospecto']):
            return self._handle_customer_problem(message)
        elif any(word in message_lower for word in ['cotización', 'presupuesto']):
            return self._handle_quote_problem(message)
        elif any(word in message_lower for word in ['pedido', 'orden']):
            return self._handle_order_problem(message)
        else:
            return self._handle_general_sales(message)
    
    def _handle_customer_problem(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para gestionar clientes:\n• Ve a Ventas > Clientes\n• Crea un nuevo cliente o busca uno existente\n• Completa todos los datos requeridos"),
            'confidence': 0.8,
            'suggestions': [_("Crear cliente"), _("Buscar cliente"), _("Editar cliente")],
            'metadata': {'problem_type': 'customer_management'}
        }
    
    def _handle_quote_problem(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para crear cotizaciones:\n• Ve a Ventas > Cotizaciones\n• Selecciona el cliente\n• Agrega los productos y servicios"),
            'confidence': 0.9,
            'suggestions': [_("Nueva cotización"), _("Editar cotización"), _("Enviar cotización")],
            'metadata': {'problem_type': 'quote_management'}
        }
    
    def _handle_order_problem(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para gestionar pedidos:\n• Ve a Ventas > Pedidos\n• Crea un nuevo pedido desde una cotización\n• Gestiona el estado del pedido"),
            'confidence': 0.8,
            'suggestions': [_("Nuevo pedido"), _("Gestionar pedidos"), _("Estado del pedido")],
            'metadata': {'problem_type': 'order_management'}
        }
    
    def _handle_general_sales(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Te ayudo con ventas. ¿Qué necesitas hacer?\n• Gestionar clientes\n• Crear cotizaciones\n• Gestionar pedidos"),
            'confidence': 0.6,
            'suggestions': [_("Gestión de clientes"), _("Cotizaciones"), _("Pedidos")],
            'metadata': {'problem_type': 'general_sales'}
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {'status': 'active', 'specialization': 'ventas'}
    
    def train(self, training_data: List[Dict]) -> bool:
        logger.info(f"Training ventas agent with {len(training_data)} samples")
        return True 