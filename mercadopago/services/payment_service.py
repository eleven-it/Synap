"""
Servicio principal de pagos para MercadoPago
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from mercadopago.services.api_client import MercadoPagoAPIClient
from mercadopago.models import MercadoPagoConfig, MercadoPagoTransaction, MercadoPagoDevice

logger = logging.getLogger(__name__)


class MercadoPagoPaymentService:
    """
    Servicio principal para procesar pagos con MercadoPago
    """
    
    def __init__(self, empresa):
        """
        Inicializar servicio con empresa
        
        Args:
            empresa: Instancia de Empresa
        """
        self.empresa = empresa
        self.config = self._get_config()
        self.api_client = MercadoPagoAPIClient(self.config) if self.config else None
    
    def _get_config(self) -> Optional[MercadoPagoConfig]:
        """
        Obtener configuración de MercadoPago para la empresa
        
        Returns:
            Configuración de MercadoPago o None si no existe
        """
        try:
            return MercadoPagoConfig.objects.get(empresa=self.empresa, is_active=True)
        except MercadoPagoConfig.DoesNotExist:
            logger.warning(f"No active MercadoPago configuration found for empresa: {self.empresa.name}")
            return None
    
    def _get_available_device(self, branch, amount: Decimal, payment_method: str) -> Optional[MercadoPagoDevice]:
        """
        Obtener dispositivo disponible para procesar el pago
        
        Args:
            branch: Sucursal donde procesar el pago
            amount: Monto del pago
            payment_method: Método de pago
            
        Returns:
            Dispositivo disponible o None
        """
        if not self.config or not self.config.smartpos_enabled:
            return None
        
        # Buscar dispositivos activos en la sucursal
        devices = MercadoPagoDevice.objects.filter(
            empresa=self.empresa,
            branch=branch,
            is_active=True,
            status='active'
        ).order_by('-is_default', 'name')
        
        for device in devices:
            if device.can_process_payment(amount, payment_method):
                return device
        
        return None
    
    def create_payment_preference(self, sale=None, invoice=None, amount: Decimal = None, 
                                description: str = "", items: List[Dict] = None) -> Dict[str, Any]:
        """
        Crear preferencia de pago
        
        Args:
            sale: Venta asociada (opcional)
            invoice: Factura asociada (opcional)
            amount: Monto del pago
            description: Descripción del pago
            items: Lista de items del pago
            
        Returns:
            Respuesta con la preferencia creada
        """
        if not self.api_client:
            return {'error': 'MercadoPago not configured', 'status_code': 400}
        
        # Generar referencia externa única
        external_reference = f"synap_{uuid.uuid4().hex[:16]}"
        
        # Preparar datos de la preferencia
        preference_data = {
            'external_reference': external_reference,
            'items': items or [{
                'title': description or 'Pago Synap',
                'quantity': 1,
                'unit_price': float(amount)
            }],
            'back_urls': {
                'success': f"{self.config.get_webhook_url()}success/",
                'failure': f"{self.config.get_webhook_url()}failure/",
                'pending': f"{self.config.get_webhook_url()}pending/"
            },
            'auto_return': 'approved',
            'notification_url': self.config.get_webhook_url(),
            'expires': True,
            'expiration_date_to': (timezone.now() + timezone.timedelta(hours=24)).isoformat(),
            'payment_methods': {
                'excluded_payment_types': [],
                'excluded_payment_methods': [],
                'installments': self.config.max_installments if self.config.installments_enabled else 1
            }
        }
        
        # Crear preferencia en MercadoPago
        result = self.api_client.create_preference(preference_data)
        
        if 'error' not in result:
            # Guardar transacción en base de datos
            transaction_data = {
                'external_reference': external_reference,
                'mercadopago_id': result.get('id'),
                'empresa': self.empresa,
                'amount': amount,
                'currency': 'ARS',
                'payment_method': 'preference',
                'payment_type': 'preference',
                'status': 'pending',
                'metadata': {
                    'sale_id': sale.id if sale else None,
                    'invoice_id': invoice.id if invoice else None,
                    'description': description,
                    'preference_data': result
                }
            }
            
            if sale:
                transaction_data['sale'] = sale
                transaction_data['branch'] = sale.branch
            
            if invoice:
                transaction_data['invoice'] = invoice
                transaction_data['branch'] = invoice.branch
            
            MercadoPagoTransaction.objects.create(**transaction_data)
            
            return {
                'success': True,
                'preference_id': result.get('id'),
                'external_reference': external_reference,
                'init_point': result.get('init_point'),
                'sandbox_init_point': result.get('sandbox_init_point')
            }
        
        return result
    
    def process_smartpos_payment(self, amount: Decimal, payment_method: str, 
                               branch=None, sale=None, invoice=None, 
                               description: str = "", installments: int = 1) -> Dict[str, Any]:
        """
        Procesar pago en dispositivo SmartPOS
        
        Args:
            amount: Monto del pago
            payment_method: Método de pago
            branch: Sucursal donde procesar
            sale: Venta asociada
            invoice: Factura asociada
            description: Descripción del pago
            installments: Número de cuotas
            
        Returns:
            Resultado del procesamiento del pago
        """
        if not self.api_client:
            return {'error': 'MercadoPago not configured', 'status_code': 400}
        
        # Obtener dispositivo disponible
        device = self._get_available_device(branch, amount, payment_method)
        if not device:
            return {'error': 'No available device for payment', 'status_code': 400}
        
        # Generar referencia externa única
        external_reference = f"synap_{uuid.uuid4().hex[:16]}"
        
        # Preparar datos del pago
        payment_data = {
            'device_id': device.device_id,
            'amount': float(amount),
            'payment_method': payment_method,
            'installments': installments,
            'description': description or 'Pago Synap',
            'external_reference': external_reference
        }
        
        # Procesar pago en el dispositivo
        result = self.api_client.process_smartpos_payment(payment_data)
        
        if 'error' not in result:
            # Guardar transacción en base de datos
            transaction_data = {
                'external_reference': external_reference,
                'mercadopago_id': result.get('id'),
                'empresa': self.empresa,
                'branch': branch,
                'device': device,
                'amount': amount,
                'currency': 'ARS',
                'payment_method': payment_method,
                'payment_type': 'smartpos',
                'installments': installments,
                'status': result.get('status', 'pending'),
                'status_detail': result.get('status_detail', ''),
                'device_transaction_id': result.get('device_transaction_id'),
                'device_response': result,
                'metadata': {
                    'sale_id': sale.id if sale else None,
                    'invoice_id': invoice.id if invoice else None,
                    'description': description
                }
            }
            
            if sale:
                transaction_data['sale'] = sale
            
            if invoice:
                transaction_data['invoice'] = invoice
            
            MercadoPagoTransaction.objects.create(**transaction_data)
            
            # Actualizar último uso del dispositivo
            device.last_transaction = timezone.now()
            device.save(update_fields=['last_transaction'])
            
            return {
                'success': True,
                'transaction_id': result.get('id'),
                'external_reference': external_reference,
                'status': result.get('status'),
                'device_id': device.device_id,
                'device_name': device.name
            }
        
        return result
    
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Obtener estado de un pago
        
        Args:
            payment_id: ID del pago en MercadoPago
            
        Returns:
            Estado del pago
        """
        if not self.api_client:
            return {'error': 'MercadoPago not configured', 'status_code': 400}
        
        result = self.api_client.get_payment(payment_id)
        
        if 'error' not in result:
            # Actualizar transacción en base de datos
            try:
                transaction = MercadoPagoTransaction.objects.get(mercadopago_id=payment_id)
                transaction.status = result.get('status', transaction.status)
                transaction.status_detail = result.get('status_detail', transaction.status_detail)
                transaction.save(update_fields=['status', 'status_detail'])
            except MercadoPagoTransaction.DoesNotExist:
                logger.warning(f"Transaction not found for payment_id: {payment_id}")
        
        return result
    
    def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """
        Reembolsar pago
        
        Args:
            payment_id: ID del pago
            amount: Monto a reembolsar (si no se especifica, se reembolsa todo)
            
        Returns:
            Resultado del reembolso
        """
        if not self.api_client:
            return {'error': 'MercadoPago not configured', 'status_code': 400}
        
        # Verificar que la transacción existe y puede ser reembolsada
        try:
            transaction = MercadoPagoTransaction.objects.get(mercadopago_id=payment_id)
            if not transaction.can_be_refunded():
                return {'error': 'Payment cannot be refunded', 'status_code': 400}
        except MercadoPagoTransaction.DoesNotExist:
            return {'error': 'Transaction not found', 'status_code': 404}
        
        # Procesar reembolso
        refund_amount = float(amount) if amount else None
        result = self.api_client.refund_payment(payment_id, refund_amount)
        
        if 'error' not in result:
            # Actualizar estado de la transacción
            transaction.status = 'refunded'
            transaction.save(update_fields=['status'])
        
        return result
    
    def get_payment_methods(self) -> Dict[str, Any]:
        """
        Obtener métodos de pago disponibles
        
        Returns:
            Lista de métodos de pago
        """
        if not self.api_client:
            return {'error': 'MercadoPago not configured', 'status_code': 400}
        
        return self.api_client.get_payment_methods()
    
    def get_transactions(self, branch=None, status=None, start_date=None, end_date=None, 
                        limit: int = 100) -> List[MercadoPagoTransaction]:
        """
        Obtener transacciones filtradas
        
        Args:
            branch: Filtrar por sucursal
            status: Filtrar por estado
            start_date: Fecha de inicio
            end_date: Fecha de fin
            limit: Límite de resultados
            
        Returns:
            Lista de transacciones
        """
        queryset = MercadoPagoTransaction.objects.filter(empresa=self.empresa)
        
        if branch:
            queryset = queryset.filter(branch=branch)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.order_by('-created_at')[:limit]
    
    def get_transaction_summary(self, branch=None, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Obtener resumen de transacciones
        
        Args:
            branch: Filtrar por sucursal
            start_date: Fecha de inicio
            end_date: Fecha de fin
            
        Returns:
            Resumen de transacciones
        """
        queryset = MercadoPagoTransaction.objects.filter(empresa=self.empresa)
        
        if branch:
            queryset = queryset.filter(branch=branch)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Calcular estadísticas
        total_transactions = queryset.count()
        approved_transactions = queryset.filter(status='approved').count()
        total_amount = queryset.filter(status='approved').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
        
        # Agrupar por método de pago
        payment_methods = queryset.values('payment_method').annotate(
            count=models.Count('id'),
            total=models.Sum('amount')
        )
        
        # Agrupar por estado
        status_summary = queryset.values('status').annotate(
            count=models.Count('id')
        )
        
        return {
            'total_transactions': total_transactions,
            'approved_transactions': approved_transactions,
            'total_amount': total_amount,
            'payment_methods': list(payment_methods),
            'status_summary': list(status_summary)
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Probar conexión con MercadoPago
        
        Returns:
            Resultado de la prueba
        """
        if not self.api_client:
            return {'error': 'MercadoPago not configured', 'status_code': 400}
        
        return self.api_client.test_connection()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validar configuración de MercadoPago
        
        Returns:
            Resultado de la validación
        """
        if not self.config:
            return {
                'valid': False,
                'error': 'No configuration found'
            }
        
        if not self.api_client:
            return {
                'valid': False,
                'error': 'API client not available'
            }
        
        return self.api_client.validate_credentials() 