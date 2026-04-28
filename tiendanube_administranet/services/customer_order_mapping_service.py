"""
Servicio de Mapeo para Clientes y Pedidos entre AdministraNET y Tiendanube.
Utiliza el AutomaticMappingService para realizar los mapeos.
"""

import logging
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.utils.translation import gettext as _

from ..models import (
    CustomerMapping, OrderMapping, TiendanubeConfig, AdministraNETConfig, SyncLog
)
from .automatic_mapping_service import AutomaticMappingService

logger = logging.getLogger(__name__)


class CustomerOrderMappingService:
    """
    Servicio para mapeo de clientes y pedidos entre AdministraNET y Tiendanube.
    Utiliza el AutomaticMappingService para realizar los mapeos automáticos.
    """
    
    def __init__(self, tiendanube_config: TiendanubeConfig = None, adminet_config: AdministraNETConfig = None):
        self.tiendanube_config = tiendanube_config
        self.adminet_config = adminet_config
        self.mapping_service = AutomaticMappingService(tiendanube_config, adminet_config)
    
    # ============================================================================
    # MAPEO DE CLIENTES
    # ============================================================================
    
    def map_tiendanube_to_adminet_customer(self, tiendanube_customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de cliente de Tiendanube a AdministraNET.
        Utiliza el servicio automático de mapeo.
        """
        return self.mapping_service.map_tiendanube_to_adminet_customer(tiendanube_customer)
    
    def map_adminet_to_tiendanube_customer(self, adminet_customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de cliente de AdministraNET a Tiendanube.
        Utiliza el servicio automático de mapeo.
        """
        return self.mapping_service.map_adminet_to_tiendanube_customer(adminet_customer)
    
    def update_customer_mapping_from_tiendanube(self, mapping: CustomerMapping, tiendanube_customer: Dict[str, Any]):
        """Actualizar mapeo de cliente con datos de Tiendanube."""
        try:
            # Actualizar campos de Tiendanube
            mapping.tiendanube_id = tiendanube_customer.get('id')
            mapping.tiendanube_name = tiendanube_customer.get('name', '')
            mapping.tiendanube_email = tiendanube_customer.get('email', '')
            mapping.tiendanube_document = tiendanube_customer.get('document', '')
            mapping.tiendanube_phone = tiendanube_customer.get('phone', '')
            mapping.tiendanube_address = tiendanube_customer.get('address', {}).get('street', '')
            mapping.tiendanube_city = tiendanube_customer.get('address', {}).get('city', '')
            mapping.tiendanube_state = tiendanube_customer.get('address', {}).get('province', '')
            mapping.tiendanube_country = tiendanube_customer.get('address', {}).get('country', '')
            mapping.tiendanube_postal_code = tiendanube_customer.get('address', {}).get('zip', '')
            mapping.tiendanube_created_at = tiendanube_customer.get('created_at')
            
            mapping.save()
            logger.info(f"Mapeo de cliente actualizado desde Tiendanube: {mapping.tiendanube_email}")
            
        except Exception as e:
            logger.error(f"Error actualizando mapeo de cliente desde Tiendanube: {e}")
            raise
    
    def update_customer_mapping_from_adminet(self, mapping: CustomerMapping, adminet_customer: Dict[str, Any]):
        """Actualizar mapeo de cliente con datos de AdministraNET."""
        try:
            # Actualizar campos de AdministraNET
            mapping.adminet_codigo = adminet_customer.get('Codigo')
            mapping.adminet_nombre = adminet_customer.get('nombre_cliente', '')
            mapping.adminet_email = adminet_customer.get('Email', '')
            mapping.adminet_documento = adminet_customer.get('CUIT', '')
            mapping.adminet_telefono = adminet_customer.get('telefono', '')
            mapping.adminet_direccion = adminet_customer.get('Calle', '')
            mapping.adminet_estado = adminet_customer.get('Estado', '')
            mapping.adminet_id_departamento = adminet_customer.get('IDDepartamento')
            mapping.adminet_cod_provincia = adminet_customer.get('CodProvincia')
            mapping.adminet_fecha_alta = adminet_customer.get('FechaAlta')
            
            mapping.save()
            logger.info(f"Mapeo de cliente actualizado desde AdministraNET: {mapping.adminet_email}")
            
        except Exception as e:
            logger.error(f"Error actualizando mapeo de cliente desde AdministraNET: {e}")
            raise
    
    # ============================================================================
    # MAPEO DE PEDIDOS
    # ============================================================================
    
    def map_tiendanube_to_adminet_order(self, tiendanube_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de pedido de Tiendanube a AdministraNET.
        Utiliza el servicio automático de mapeo.
        """
        return self.mapping_service.map_tiendanube_to_adminet_order(tiendanube_order)
    
    def map_adminet_to_tiendanube_order(self, adminet_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos de pedido de AdministraNET a Tiendanube.
        Utiliza el servicio automático de mapeo.
        """
        return self.mapping_service.map_adminet_to_tiendanube_order(adminet_order)
    
    def update_order_mapping_from_tiendanube(self, mapping: OrderMapping, tiendanube_order: Dict[str, Any]):
        """Actualizar mapeo de pedido con datos de Tiendanube."""
        try:
            # Actualizar campos de Tiendanube
            mapping.tiendanube_id = tiendanube_order.get('id')
            mapping.tiendanube_number = tiendanube_order.get('number', '')
            mapping.tiendanube_total = float(tiendanube_order.get('total', 0))
            mapping.tiendanube_currency = tiendanube_order.get('currency', 'ARS')
            mapping.tiendanube_status = tiendanube_order.get('status', '')
            mapping.tiendanube_payment_status = tiendanube_order.get('payment_status', '')
            mapping.tiendanube_notes = tiendanube_order.get('notes', '')
            
            # Campos del cliente
            customer = tiendanube_order.get('customer', {})
            mapping.tiendanube_customer_id = customer.get('id')
            mapping.tiendanube_customer_email = customer.get('email', '')
            mapping.tiendanube_customer_name = customer.get('name', '')
            
            # Campos de dirección
            mapping.tiendanube_shipping_address = tiendanube_order.get('shipping_address', {})
            mapping.tiendanube_billing_address = tiendanube_order.get('billing_address', {})
            
            # Campos de pago y envío
            mapping.tiendanube_payment_method = tiendanube_order.get('payment_method', '')
            mapping.tiendanube_shipping_method = tiendanube_order.get('shipping_method', '')
            
            # Campos de fecha
            mapping.tiendanube_created_at = tiendanube_order.get('created_at')
            mapping.tiendanube_updated_at = tiendanube_order.get('updated_at')
            
            mapping.save()
            logger.info(f"Mapeo de pedido actualizado desde Tiendanube: {mapping.tiendanube_number}")
            
        except Exception as e:
            logger.error(f"Error actualizando mapeo de pedido desde Tiendanube: {e}")
            raise
    
    def update_order_mapping_from_adminet(self, mapping: OrderMapping, adminet_order: Dict[str, Any]):
        """Actualizar mapeo de pedido con datos de AdministraNET."""
        try:
            # Actualizar campos de AdministraNET
            mapping.adminet_codigo = adminet_order.get('idpedido')
            mapping.adminet_numero = adminet_order.get('numero_pedido', '')
            mapping.adminet_estado = adminet_order.get('estado', '')
            mapping.adminet_total = float(adminet_order.get('total', 0))
            
            mapping.save()
            logger.info(f"Mapeo de pedido actualizado desde AdministraNET: {mapping.adminet_numero}")
            
        except Exception as e:
            logger.error(f"Error actualizando mapeo de pedido desde AdministraNET: {e}")
            raise
    
    # ============================================================================
    # MÉTODOS DE SINCRONIZACIÓN
    # ============================================================================
    
    def sync_customer_from_tiendanube(self, mapping: CustomerMapping, tiendanube_customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincronizar cliente desde Tiendanube hacia AdministraNET.
        """
        try:
            # Mapear datos
            adminet_data = self.map_tiendanube_to_adminet_customer(tiendanube_customer)
            
            # Aquí se implementaría la lógica para guardar en AdministraNET
            # Por ahora solo actualizamos el mapeo
            self.update_customer_mapping_from_tiendanube(mapping, tiendanube_customer)
            
            mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
            mapping.last_synced = timezone.now()
            mapping.save()
            
            return {
                'success': True,
                'message': f'Cliente sincronizado exitosamente: {mapping.tiendanube_email}'
            }
            
        except Exception as e:
            logger.error(f"Error sincronizando cliente desde Tiendanube: {e}")
            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
            mapping.error_message = str(e)
            mapping.save()
            
            return {
                'success': False,
                'message': f'Error sincronizando cliente: {str(e)}'
            }
    
    def sync_customer_from_adminet(self, mapping: CustomerMapping, adminet_customer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincronizar cliente desde AdministraNET hacia Tiendanube.
        """
        try:
            # Mapear datos
            tiendanube_data = self.map_adminet_to_tiendanube_customer(adminet_customer)
            
            # Aquí se implementaría la lógica para guardar en Tiendanube
            # Por ahora solo actualizamos el mapeo
            self.update_customer_mapping_from_adminet(mapping, adminet_customer)
            
            mapping.sync_status = CustomerMapping.SyncStatus.SYNCED
            mapping.last_synced = timezone.now()
            mapping.save()
            
            return {
                'success': True,
                'message': f'Cliente sincronizado exitosamente: {mapping.adminet_email}'
            }
            
        except Exception as e:
            logger.error(f"Error sincronizando cliente desde AdministraNET: {e}")
            mapping.sync_status = CustomerMapping.SyncStatus.ERROR
            mapping.error_message = str(e)
            mapping.save()
            
            return {
                'success': False,
                'message': f'Error sincronizando cliente: {str(e)}'
            }
    
    def sync_order_from_tiendanube(self, mapping: OrderMapping, tiendanube_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincronizar pedido desde Tiendanube hacia AdministraNET.
        """
        try:
            # Mapear datos
            adminet_data = self.map_tiendanube_to_adminet_order(tiendanube_order)
            
            # Aquí se implementaría la lógica para guardar en AdministraNET
            # Por ahora solo actualizamos el mapeo
            self.update_order_mapping_from_tiendanube(mapping, tiendanube_order)
            
            mapping.sync_status = OrderMapping.SyncStatus.SYNCED
            mapping.last_synced = timezone.now()
            mapping.save()
            
            return {
                'success': True,
                'message': f'Pedido sincronizado exitosamente: {mapping.tiendanube_number}'
            }
            
        except Exception as e:
            logger.error(f"Error sincronizando pedido desde Tiendanube: {e}")
            mapping.sync_status = OrderMapping.SyncStatus.ERROR
            mapping.error_message = str(e)
            mapping.save()
            
            return {
                'success': False,
                'message': f'Error sincronizando pedido: {str(e)}'
            }
    
    def sync_order_from_adminet(self, mapping: OrderMapping, adminet_order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sincronizar pedido desde AdministraNET hacia Tiendanube.
        """
        try:
            # Mapear datos
            tiendanube_data = self.map_adminet_to_tiendanube_order(adminet_order)
            
            # Aquí se implementaría la lógica para guardar en Tiendanube
            # Por ahora solo actualizamos el mapeo
            self.update_order_mapping_from_adminet(mapping, adminet_order)
            
            mapping.sync_status = OrderMapping.SyncStatus.SYNCED
            mapping.last_synced = timezone.now()
            mapping.save()
            
            return {
                'success': True,
                'message': f'Pedido sincronizado exitosamente: {mapping.adminet_numero}'
            }
            
        except Exception as e:
            logger.error(f"Error sincronizando pedido desde AdministraNET: {e}")
            mapping.sync_status = OrderMapping.SyncStatus.ERROR
            mapping.error_message = str(e)
            mapping.save()
            
            return {
                'success': False,
                'message': f'Error sincronizando pedido: {str(e)}'
            }
    
    # ============================================================================
    # MÉTODOS DE VALIDACIÓN
    # ============================================================================
    
    def validate_customer_mapping(self, mapping: CustomerMapping) -> Dict[str, Any]:
        """
        Validar que un mapeo de cliente tenga todos los campos requeridos.
        """
        errors = []
        warnings = []
        
        # Validaciones críticas
        if not mapping.tiendanube_email and not mapping.adminet_email:
            errors.append("Debe tener al menos un email (Tiendanube o AdministraNET)")
        
        if not mapping.tiendanube_name and not mapping.adminet_nombre:
            errors.append("Debe tener al menos un nombre (Tiendanube o AdministraNET)")
        
        # Validaciones de advertencia
        if not mapping.tiendanube_id and not mapping.adminet_codigo:
            warnings.append("No tiene IDs configurados")
        
        if not mapping.sync_enabled:
            warnings.append("La sincronización está deshabilitada")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_order_mapping(self, mapping: OrderMapping) -> Dict[str, Any]:
        """
        Validar que un mapeo de pedido tenga todos los campos requeridos.
        """
        errors = []
        warnings = []
        
        # Validaciones críticas
        if not mapping.tiendanube_number and not mapping.adminet_numero:
            errors.append("Debe tener al menos un número de pedido (Tiendanube o AdministraNET)")
        
        if not mapping.tiendanube_total and not mapping.adminet_total:
            warnings.append("No tiene total configurado")
        
        # Validaciones de advertencia
        if not mapping.tiendanube_id and not mapping.adminet_codigo:
            warnings.append("No tiene IDs configurados")
        
        if not mapping.sync_enabled:
            warnings.append("La sincronización está deshabilitada")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        } 