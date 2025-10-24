"""
Agente de Configuración - Especializado en problemas de configuración
"""
import logging
from typing import Dict, List, Any
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class ConfiguracionAgent:
    """Agente especializado en problemas de configuración"""
    
    def __init__(self):
        self.specialized_keywords = [
            'configurar', 'configuración', 'ajustes', 'parámetros', 'setup',
            'instalación', 'config', 'preferencias', 'opciones'
        ]
    
    def process(self, message: str, ticket, attachments: List = None) -> Dict[str, Any]:
        """Procesa consultas de configuración"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['usuario', 'perfil']):
            return self._handle_user_config(message)
        elif any(word in message_lower for word in ['empresa', 'sucursal']):
            return self._handle_company_config(message)
        elif any(word in message_lower for word in ['módulo', 'funcionalidad']):
            return self._handle_module_config(message)
        else:
            return self._handle_general_config(message)
    
    def _handle_user_config(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para configurar tu perfil de usuario:\n• Ve a Configuración > Perfil\n• Actualiza tus datos personales\n• Configura tus preferencias"),
            'confidence': 0.8,
            'suggestions': [_("Editar perfil"), _("Cambiar contraseña"), _("Configurar notificaciones")],
            'metadata': {'problem_type': 'user_config'}
        }
    
    def _handle_company_config(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para configurar tu empresa:\n• Ve a Configuración > Empresa\n• Completa los datos fiscales\n• Configura las sucursales"),
            'confidence': 0.9,
            'suggestions': [_("Datos de empresa"), _("Configurar sucursales"), _("Datos fiscales")],
            'metadata': {'problem_type': 'company_config'}
        }
    
    def _handle_module_config(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Para configurar módulos:\n• Ve a Configuración > Módulos\n• Activa los módulos que necesites\n• Configura los parámetros específicos"),
            'confidence': 0.7,
            'suggestions': [_("Activar módulos"), _("Configurar parámetros"), _("Permisos de usuario")],
            'metadata': {'problem_type': 'module_config'}
        }
    
    def _handle_general_config(self, message: str) -> Dict[str, Any]:
        return {
            'message': _("Te ayudo con la configuración. ¿Qué específicamente necesitas configurar?\n• Perfil de usuario\n• Datos de empresa\n• Módulos del sistema"),
            'confidence': 0.6,
            'suggestions': [_("Configuración de usuario"), _("Configuración de empresa"), _("Configuración de módulos")],
            'metadata': {'problem_type': 'general_config'}
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {'status': 'active', 'specialization': 'configuracion'}
    
    def train(self, training_data: List[Dict]) -> bool:
        logger.info(f"Training configuracion agent with {len(training_data)} samples")
        return True 