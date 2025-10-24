"""
Módulo de agentes especializados para soporte IA
"""

from .supervisor import SupervisorAgent
from .facturacion import FacturacionAgent
from .configuracion import ConfiguracionAgent
from .ventas import VentasAgent
from .inventario import InventarioAgent
from .multimodal import MultimodalAgent
from .voz import VozAgent

__all__ = [
    'SupervisorAgent',
    'FacturacionAgent',
    'ConfiguracionAgent',
    'VentasAgent',
    'InventarioAgent',
    'MultimodalAgent',
    'VozAgent',
] 