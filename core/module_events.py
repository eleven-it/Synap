"""
Eventos estándar del sistema Synap
Define eventos comunes que pueden ser utilizados por todos los módulos
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class EventPriority(Enum):
    """Prioridades de eventos"""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    CRITICAL = 'critical'


class ModuleEvents:
    """Eventos estándar del sistema"""
    
    # Eventos de Módulos
    MODULE_ACTIVATED = 'module.activated'
    MODULE_DEACTIVATED = 'module.deactivated'
    MODULE_INSTALLED = 'module.installed'
    MODULE_UNINSTALLED = 'module.uninstalled'
    MODULE_UPDATED = 'module.updated'
    MODULE_ERROR = 'module.error'
    
    # Eventos de Usuario
    USER_CREATED = 'user.created'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'
    USER_LOGIN = 'user.login'
    USER_LOGOUT = 'user.logout'
    USER_PASSWORD_CHANGED = 'user.password_changed'
    USER_PERMISSIONS_CHANGED = 'user.permissions_changed'
    
    # Eventos de Empresa
    COMPANY_CREATED = 'company.created'
    COMPANY_UPDATED = 'company.updated'
    COMPANY_DELETED = 'company.deleted'
    BRANCH_CREATED = 'branch.created'
    BRANCH_UPDATED = 'branch.updated'
    BRANCH_DELETED = 'branch.deleted'
    
    # Eventos de Ventas
    SALE_CREATED = 'sale.created'
    SALE_UPDATED = 'sale.updated'
    SALE_CANCELLED = 'sale.cancelled'
    SALE_COMPLETED = 'sale.completed'
    INVOICE_CREATED = 'invoice.created'
    INVOICE_PAID = 'invoice.paid'
    PAYMENT_RECEIVED = 'payment.received'
    
    # Eventos de Compras
    PURCHASE_CREATED = 'purchase.created'
    PURCHASE_UPDATED = 'purchase.updated'
    PURCHASE_CANCELLED = 'purchase.cancelled'
    PURCHASE_COMPLETED = 'purchase.completed'
    SUPPLIER_CREATED = 'supplier.created'
    SUPPLIER_UPDATED = 'supplier.updated'
    
    # Eventos de Inventario
    PRODUCT_CREATED = 'product.created'
    PRODUCT_UPDATED = 'product.updated'
    PRODUCT_DELETED = 'product.deleted'
    STOCK_MOVEMENT = 'stock.movement'
    STOCK_LOW = 'stock.low'
    STOCK_OUT = 'stock.out'
    
    # Eventos de Contabilidad
    ACCOUNT_CREATED = 'account.created'
    ACCOUNT_UPDATED = 'account.updated'
    JOURNAL_ENTRY_CREATED = 'journal_entry.created'
    JOURNAL_ENTRY_POSTED = 'journal_entry.posted'
    TAX_CALCULATED = 'tax.calculated'
    
    # Eventos del Sistema
    SYSTEM_STARTUP = 'system.startup'
    SYSTEM_SHUTDOWN = 'system.shutdown'
    SYSTEM_ERROR = 'system.error'
    SYSTEM_WARNING = 'system.warning'
    BACKUP_CREATED = 'backup.created'
    BACKUP_RESTORED = 'backup.restored'
    
    # Eventos de Integración
    INTEGRATION_CONNECTED = 'integration.connected'
    INTEGRATION_DISCONNECTED = 'integration.disconnected'
    INTEGRATION_SYNC_STARTED = 'integration.sync_started'
    INTEGRATION_SYNC_COMPLETED = 'integration.sync_completed'
    INTEGRATION_ERROR = 'integration.error'


class EventDataBuilder:
    """Constructor de datos de eventos"""
    
    @staticmethod
    def module_event(module_name: str, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de módulos"""
        return {
            'module_name': module_name,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def user_event(user_id: int, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de usuario"""
        return {
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def company_event(company_id: int, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de empresa"""
        return {
            'company_id': company_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def sale_event(sale_id: int, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de ventas"""
        return {
            'sale_id': sale_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def purchase_event(purchase_id: int, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de compras"""
        return {
            'purchase_id': purchase_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def product_event(product_id: int, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de productos"""
        return {
            'product_id': product_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def stock_event(product_id: int, quantity: int, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de inventario"""
        return {
            'product_id': product_id,
            'quantity': quantity,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def system_event(action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos del sistema"""
        return {
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
    
    @staticmethod
    def integration_event(integration_name: str, action: str, details: Dict = None) -> Dict:
        """Construye datos para eventos de integración"""
        return {
            'integration_name': integration_name,
            'action': action,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }


class EventHandler:
    """Clase base para manejadores de eventos"""
    
    def __init__(self, event_name: str, priority: EventPriority = EventPriority.NORMAL):
        self.event_name = event_name
        self.priority = priority
    
    def handle(self, event_data: Dict) -> Any:
        """
        Maneja el evento
        
        Args:
            event_data: Datos del evento
            
        Returns:
            Resultado del procesamiento del evento
        """
        raise NotImplementedError("Subclasses must implement handle method")
    
    def can_handle(self, event_data: Dict) -> bool:
        """
        Verifica si puede manejar el evento
        
        Args:
            event_data: Datos del evento
            
        Returns:
            True si puede manejar el evento
        """
        return True
    
    def get_priority(self) -> EventPriority:
        """Obtiene la prioridad del manejador"""
        return self.priority


class EventFilter:
    """Filtro de eventos"""
    
    def __init__(self, name: str, filter_func: callable):
        self.name = name
        self.filter_func = filter_func
    
    def apply(self, event_data: Dict) -> bool:
        """
        Aplica el filtro al evento
        
        Args:
            event_data: Datos del evento
            
        Returns:
            True si el evento pasa el filtro
        """
        return self.filter_func(event_data)


# Funciones de utilidad para disparar eventos
def dispatch_module_event(event_name: str, module_name: str, action: str, 
                         details: Dict = None, priority: EventPriority = EventPriority.NORMAL):
    """Dispara un evento de módulo"""
    from core.event_dispatcher import event_dispatcher
    
    event_data = EventDataBuilder.module_event(module_name, action, details)
    event_dispatcher.dispatch_event(
        event_name, 
        event_data, 
        source_module=module_name,
        priority=priority.value
    )


def dispatch_user_event(event_name: str, user_id: int, action: str, 
                       details: Dict = None, priority: EventPriority = EventPriority.NORMAL):
    """Dispara un evento de usuario"""
    from core.event_dispatcher import event_dispatcher
    
    event_data = EventDataBuilder.user_event(user_id, action, details)
    event_dispatcher.dispatch_event(
        event_name, 
        event_data, 
        priority=priority.value
    )


def dispatch_system_event(event_name: str, action: str, 
                         details: Dict = None, priority: EventPriority = EventPriority.NORMAL):
    """Dispara un evento del sistema"""
    from core.event_dispatcher import event_dispatcher
    
    event_data = EventDataBuilder.system_event(action, details)
    event_dispatcher.dispatch_event(
        event_name, 
        event_data, 
        priority=priority.value
    ) 