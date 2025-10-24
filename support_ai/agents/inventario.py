"""
Agente de Inventario - Especializado en problemas de inventario
"""
import logging
from typing import Dict, List, Any
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class InventarioAgent:
    """Agente especializado en problemas de inventario"""
    
    def __init__(self):
        self.specialized_keywords = [
            'stock', 'inventario', 'producto', 'mercadería', 'código', 'barcode',
            'categoría', 'proveedor', 'entrada', 'salida', 'movimiento'
        ]
    
    def process(self, message: str, ticket, attachments: List = None) -> Dict[str, Any]:
        """Procesa consultas de inventario"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['producto', 'mercadería']):
            return self._handle_product_problem(message)
        elif any(word in message_lower for word in ['stock', 'cantidad']):
            return self._handle_stock_problem(message)
        elif any(word in message_lower for word in ['movimiento', 'entrada', 'salida']):
            return self._handle_movement_problem(message)
        else:
            return self._handle_general_inventory(message)
    
    def _handle_product_problem(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para gestionar productos:\n• Ve a Inventario > Productos\n• Crea un nuevo producto o edita uno existente\n• Completa código, nombre, categoría y precio"),
            'confidence': 0.8,
            'suggestions': [_("Crear producto"), _("Editar producto"), _("Buscar producto")],
            'metadata': {'problem_type': 'product_management'}
        }
    
    def _handle_stock_problem(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para gestionar stock:\n• Ve a Inventario > Stock\n• Revisa las cantidades actuales\n• Realiza ajustes si es necesario"),
            'confidence': 0.9,
            'suggestions': [_("Ver stock"), _("Ajustar stock"), _("Reporte de stock")],
            'metadata': {'problem_type': 'stock_management'}
        }
    
    def _handle_movement_problem(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para gestionar movimientos:\n• Ve a Inventario > Movimientos\n• Registra entradas y salidas\n• Revisa el historial de movimientos"),
            'confidence': 0.8,
            'suggestions': [_("Nuevo movimiento"), _("Historial movimientos"), _("Ajuste de inventario")],
            'metadata': {'problem_type': 'movement_management'}
        }
    
    def _handle_general_inventory(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Te ayudo con inventario. ¿Qué necesitas hacer?\n• Gestionar productos\n• Controlar stock\n• Registrar movimientos"),
            'confidence': 0.6,
            'suggestions': [_("Gestión de productos"), _("Control de stock"), _("Movimientos")],
            'metadata': {'problem_type': 'general_inventory'}
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {'status': 'active', 'specialization': 'inventario'}
    
    def train(self, training_data: List[Dict]) -> bool:
        logger.info(f"Training inventario agent with {len(training_data)} samples")
        return True 