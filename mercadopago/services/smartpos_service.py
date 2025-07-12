"""
Servicio específico para dispositivos SmartPOS de MercadoPago
"""

import logging
import time
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db import transaction

from mercadopago.services.api_client import MercadoPagoAPIClient
from mercadopago.models import MercadoPagoDevice, MercadoPagoConfig

logger = logging.getLogger(__name__)


class MercadoPagoSmartPOSService:
    """
    Servicio para gestionar dispositivos SmartPOS
    """
    
    def __init__(self, device: MercadoPagoDevice):
        """
        Inicializar servicio con dispositivo
        
        Args:
            device: Instancia de MercadoPagoDevice
        """
        self.device = device
        self.config = device.config
        self.api_client = MercadoPagoAPIClient(self.config)
    
    def register_device(self) -> Dict[str, Any]:
        """
        Registrar dispositivo en MercadoPago
        
        Returns:
            Resultado del registro
        """
        device_data = {
            'name': self.device.name,
            'device_type': self.device.device_type,
            'serial_number': self.device.serial_number,
            'location': {
                'branch_id': str(self.device.branch.id),
                'description': self.device.location_description
            },
            'config': self.device.device_config,
            'supported_payment_methods': self.device.supported_payment_methods
        }
        
        result = self.api_client.register_smartpos_device(device_data)
        
        if 'error' not in result:
            # Actualizar dispositivo con ID de MercadoPago
            self.device.device_id = result.get('id')
            self.device.status = 'active'
            self.device.connection_status = 'connected'
            self.device.last_sync = timezone.now()
            self.device.save(update_fields=[
                'device_id', 'status', 'connection_status', 'last_sync'
            ])
            
            logger.info(f"Device {self.device.name} registered successfully with ID: {self.device.device_id}")
        
        return result
    
    def sync_device_status(self) -> Dict[str, Any]:
        """
        Sincronizar estado del dispositivo
        
        Returns:
            Estado actualizado del dispositivo
        """
        if not self.device.device_id:
            return {'error': 'Device not registered', 'status_code': 400}
        
        result = self.api_client.get_smartpos_device_status(self.device.device_id)
        
        if 'error' not in result:
            # Actualizar estado del dispositivo
            status = result.get('status', 'unknown')
            connection_status = result.get('connection_status', 'unknown')
            
            self.device.status = status
            self.device.connection_status = connection_status
            self.device.last_sync = timezone.now()
            self.device.save(update_fields=[
                'status', 'connection_status', 'last_sync'
            ])
            
            logger.debug(f"Device {self.device.name} status synced: {status}")
        
        return result
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Obtener información completa del dispositivo
        
        Returns:
            Información del dispositivo
        """
        if not self.device.device_id:
            return {'error': 'Device not registered', 'status_code': 400}
        
        return self.api_client.get_smartpos_device(self.device.device_id)
    
    def update_device_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Actualizar configuración del dispositivo
        
        Args:
            config_data: Nueva configuración
            
        Returns:
            Resultado de la actualización
        """
        if not self.device.device_id:
            return {'error': 'Device not registered', 'status_code': 400}
        
        result = self.api_client.update_smartpos_device_config(
            self.device.device_id, 
            config_data
        )
        
        if 'error' not in result:
            # Actualizar configuración local
            self.device.device_config.update(config_data)
            self.device.save(update_fields=['device_config'])
            
            logger.info(f"Device {self.device.name} configuration updated")
        
        return result
    
    def process_payment(self, amount: float, payment_method: str, 
                       installments: int = 1, description: str = "") -> Dict[str, Any]:
        """
        Procesar pago en el dispositivo
        
        Args:
            amount: Monto del pago
            payment_method: Método de pago
            installments: Número de cuotas
            description: Descripción del pago
            
        Returns:
            Resultado del pago
        """
        if not self.device.device_id:
            return {'error': 'Device not registered', 'status_code': 400}
        
        if not self.device.can_process_payment(amount, payment_method):
            return {'error': 'Device cannot process this payment', 'status_code': 400}
        
        payment_data = {
            'device_id': self.device.device_id,
            'amount': amount,
            'payment_method': payment_method,
            'installments': installments,
            'description': description or 'Pago Synap'
        }
        
        result = self.api_client.process_smartpos_payment(payment_data)
        
        if 'error' not in result:
            # Actualizar último uso del dispositivo
            self.device.last_transaction = timezone.now()
            self.device.save(update_fields=['last_transaction'])
            
            logger.info(f"Payment processed on device {self.device.name}: {result.get('id')}")
        
        return result
    
    def delete_device(self) -> Dict[str, Any]:
        """
        Eliminar dispositivo de MercadoPago
        
        Returns:
            Resultado de la eliminación
        """
        if not self.device.device_id:
            return {'error': 'Device not registered', 'status_code': 400}
        
        result = self.api_client.delete_smartpos_device(self.device.device_id)
        
        if 'error' not in result:
            # Marcar dispositivo como inactivo
            self.device.is_active = False
            self.device.status = 'inactive'
            self.device.connection_status = 'disconnected'
            self.device.save(update_fields=[
                'is_active', 'status', 'connection_status'
            ])
            
            logger.info(f"Device {self.device.name} deleted successfully")
        
        return result
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Probar conexión con el dispositivo
        
        Returns:
            Resultado de la prueba
        """
        if not self.device.device_id:
            return {'error': 'Device not registered', 'status_code': 400}
        
        try:
            # Intentar obtener información del dispositivo
            result = self.get_device_info()
            if 'error' not in result:
                return {
                    'success': True,
                    'message': 'Device connection successful',
                    'device_info': result
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Connection failed')
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_device_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Obtener métricas del dispositivo
        
        Args:
            days: Número de días para calcular métricas
            
        Returns:
            Métricas del dispositivo
        """
        from mercadopago.models import MercadoPagoTransaction
        
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Obtener transacciones del dispositivo
        transactions = MercadoPagoTransaction.objects.filter(
            device=self.device,
            created_at__gte=start_date
        )
        
        # Calcular métricas
        total_transactions = transactions.count()
        approved_transactions = transactions.filter(status='approved').count()
        total_amount = transactions.filter(status='approved').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        
        # Métricas por método de pago
        payment_methods = transactions.values('payment_method').annotate(
            count=models.Count('id'),
            total=models.Sum('amount')
        )
        
        # Métricas por día
        daily_metrics = transactions.extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            count=models.Count('id'),
            total=models.Sum('amount')
        ).order_by('day')
        
        return {
            'device_id': self.device.device_id,
            'device_name': self.device.name,
            'period_days': days,
            'total_transactions': total_transactions,
            'approved_transactions': approved_transactions,
            'total_amount': total_amount,
            'payment_methods': list(payment_methods),
            'daily_metrics': list(daily_metrics),
            'last_transaction': self.device.last_transaction,
            'connection_status': self.device.connection_status
        }


class MercadoPagoDeviceManager:
    """
    Gestor de dispositivos SmartPOS
    """
    
    def __init__(self, empresa):
        """
        Inicializar gestor con empresa
        
        Args:
            empresa: Instancia de Empresa
        """
        self.empresa = empresa
    
    def get_all_devices(self, branch=None, status=None) -> List[MercadoPagoDevice]:
        """
        Obtener todos los dispositivos
        
        Args:
            branch: Filtrar por sucursal
            status: Filtrar por estado
            
        Returns:
            Lista de dispositivos
        """
        queryset = MercadoPagoDevice.objects.filter(empresa=self.empresa)
        
        if branch:
            queryset = queryset.filter(branch=branch)
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('branch__nombre', 'name')
    
    def sync_all_devices(self) -> Dict[str, Any]:
        """
        Sincronizar todos los dispositivos
        
        Returns:
            Resultado de la sincronización
        """
        devices = self.get_all_devices(status='active')
        results = {
            'total_devices': len(devices),
            'synced_devices': 0,
            'failed_devices': 0,
            'errors': []
        }
        
        for device in devices:
            try:
                service = MercadoPagoSmartPOSService(device)
                result = service.sync_device_status()
                
                if 'error' not in result:
                    results['synced_devices'] += 1
                else:
                    results['failed_devices'] += 1
                    results['errors'].append({
                        'device_id': device.id,
                        'device_name': device.name,
                        'error': result.get('error')
                    })
                    
            except Exception as e:
                results['failed_devices'] += 1
                results['errors'].append({
                    'device_id': device.id,
                    'device_name': device.name,
                    'error': str(e)
                })
        
        return results
    
    def get_device_summary(self) -> Dict[str, Any]:
        """
        Obtener resumen de dispositivos
        
        Returns:
            Resumen de dispositivos
        """
        devices = self.get_all_devices()
        
        # Estadísticas por estado
        status_summary = devices.values('status').annotate(
            count=models.Count('id')
        )
        
        # Estadísticas por tipo
        type_summary = devices.values('device_type').annotate(
            count=models.Count('id')
        )
        
        # Estadísticas por sucursal
        branch_summary = devices.values('branch__nombre').annotate(
            count=models.Count('id')
        )
        
        # Dispositivos activos
        active_devices = devices.filter(status='active').count()
        
        # Dispositivos conectados
        connected_devices = devices.filter(connection_status='connected').count()
        
        return {
            'total_devices': len(devices),
            'active_devices': active_devices,
            'connected_devices': connected_devices,
            'status_summary': list(status_summary),
            'type_summary': list(type_summary),
            'branch_summary': list(branch_summary)
        }
    
    def register_new_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Registrar nuevo dispositivo
        
        Args:
            device_data: Datos del dispositivo
            
        Returns:
            Resultado del registro
        """
        try:
            # Crear dispositivo en base de datos
            device = MercadoPagoDevice.objects.create(
                empresa=self.empresa,
                **device_data
            )
            
            # Registrar en MercadoPago
            service = MercadoPagoSmartPOSService(device)
            result = service.register_device()
            
            if 'error' not in result:
                return {
                    'success': True,
                    'device_id': device.id,
                    'mercadopago_device_id': device.device_id,
                    'message': 'Device registered successfully'
                }
            else:
                # Si falla el registro en MercadoPago, eliminar de base de datos
                device.delete()
                return result
                
        except Exception as e:
            return {
                'error': f'Failed to register device: {str(e)}',
                'status_code': 500
            } 