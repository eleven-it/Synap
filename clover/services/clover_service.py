import requests
import json
import uuid
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from ..models import CloverDevice, CloverTransaction, CloverConfiguration


class CloverService:
    """
    Servicio principal para integración con Clover
    """
    
    def __init__(self, device=None, empresa=None):
        self.device = device
        self.empresa = empresa
        self.config = None
        
        if empresa:
            self.config, _ = CloverConfiguration.objects.get_or_create(empresa=empresa)
    
    def _get_headers(self, device=None):
        """Obtener headers para las peticiones a la API de Clover"""
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified for Clover API request"))
        
        return {
            'Authorization': f'Bearer {target_device.api_token}',
            'Content-Type': 'application/json',
            'X-Clover-Device-ID': target_device.device_id,
        }
    
    def _make_request(self, method, endpoint, data=None, device=None):
        """Realizar petición a la API de Clover"""
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified for Clover API request"))
        
        # Construir URL base
        if self.config:
            base_url = self.config.get_api_url()
        else:
            base_url = "https://api.clover.com/v3"
        
        url = f"{base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers(target_device)
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise ValidationError(f"Clover API error: {str(e)}")
    
    def get_device_info(self, device=None):
        """Obtener información del dispositivo"""
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified"))
        
        endpoint = f"merchants/{target_device.merchant_id}/devices/{target_device.device_id}"
        return self._make_request('GET', endpoint, device=target_device)
    
    def create_payment(self, amount, payment_data, device=None):
        """
        Crear un pago en Clover
        
        Args:
            amount: Monto del pago
            payment_data: Datos del pago (tip, tax, etc.)
            device: Dispositivo a usar (opcional)
        """
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified for payment"))
        
        # Generar ID único para la transacción
        transaction_id = f"CLV-{uuid.uuid4().hex[:8].upper()}"
        
        # Preparar datos del pago
        payment_request = {
            'amount': int(amount * 100),  # Clover usa centavos
            'currency': 'ARS',
            'externalPaymentId': transaction_id,
        }
        
        # Agregar propina si existe
        if payment_data.get('tip_amount'):
            payment_request['tipAmount'] = int(payment_data['tip_amount'] * 100)
        
        # Agregar impuestos si existen
        if payment_data.get('tax_amount'):
            payment_request['taxAmount'] = int(payment_data['tax_amount'] * 100)
        
        # Agregar información del cliente si existe
        if payment_data.get('customer_name'):
            payment_request['note'] = f"Customer: {payment_data['customer_name']}"
        
        # Realizar pago
        endpoint = f"merchants/{target_device.merchant_id}/payments"
        response = self._make_request('POST', endpoint, payment_request, target_device)
        
        # Crear registro de transacción
        transaction = CloverTransaction.objects.create(
            transaction_id=transaction_id,
            clover_transaction_id=response.get('id'),
            empresa=target_device.empresa,
            branch=target_device.branch,
            device=target_device,
            operator=payment_data.get('operator'),
            transaction_type='sale',
            status='pending',
            amount=amount,
            tip_amount=payment_data.get('tip_amount', Decimal('0.00')),
            tax_amount=payment_data.get('tax_amount', Decimal('0.00')),
            total_amount=amount + payment_data.get('tip_amount', Decimal('0.00')) + payment_data.get('tax_amount', Decimal('0.00')),
            customer_name=payment_data.get('customer_name', ''),
            customer_email=payment_data.get('customer_email', ''),
            clover_response=response,
            external_reference=payment_data.get('external_reference', ''),
        )
        
        return transaction
    
    def process_payment(self, payment_id, device=None):
        """
        Procesar un pago pendiente
        """
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified for payment processing"))
        
        endpoint = f"merchants/{target_device.merchant_id}/payments/{payment_id}/process"
        response = self._make_request('POST', endpoint, device=target_device)
        
        # Actualizar transacción
        try:
            transaction = CloverTransaction.objects.get(clover_transaction_id=payment_id)
            transaction.status = 'approved' if response.get('status') == 'PAID' else 'declined'
            transaction.clover_response = response
            transaction.save()
            
            return transaction
            
        except CloverTransaction.DoesNotExist:
            raise ValidationError(_("Transaction not found"))
    
    def refund_payment(self, original_transaction, refund_amount=None, device=None):
        """
        Reembolsar un pago
        
        Args:
            original_transaction: Transacción original a reembolsar
            refund_amount: Monto a reembolsar (si no se especifica, se reembolsa todo)
            device: Dispositivo a usar (opcional)
        """
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified for refund"))
        
        if not original_transaction.can_be_refunded:
            raise ValidationError(_("Transaction cannot be refunded"))
        
        # Monto a reembolsar
        refund_amount = refund_amount or original_transaction.total_amount
        
        # Preparar datos del reembolso
        refund_request = {
            'amount': int(refund_amount * 100),
            'reason': 'Customer request',
        }
        
        # Realizar reembolso
        endpoint = f"merchants/{target_device.merchant_id}/payments/{original_transaction.clover_transaction_id}/refunds"
        response = self._make_request('POST', endpoint, refund_request, target_device)
        
        # Crear transacción de reembolso
        refund_transaction = CloverTransaction.objects.create(
            transaction_id=f"REF-{uuid.uuid4().hex[:8].upper()}",
            clover_transaction_id=response.get('id'),
            empresa=target_device.empresa,
            branch=target_device.branch,
            device=target_device,
            operator=original_transaction.operator,
            transaction_type='refund',
            status='approved',
            amount=refund_amount,
            total_amount=refund_amount,
            clover_response=response,
            external_reference=f"Refund of {original_transaction.transaction_id}",
        )
        
        return refund_transaction
    
    def void_payment(self, transaction, device=None):
        """
        Anular un pago
        
        Args:
            transaction: Transacción a anular
            device: Dispositivo a usar (opcional)
        """
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified for void"))
        
        if transaction.status != 'approved':
            raise ValidationError(_("Only approved transactions can be voided"))
        
        # Anular pago
        endpoint = f"merchants/{target_device.merchant_id}/payments/{transaction.clover_transaction_id}/void"
        response = self._make_request('POST', endpoint, device=target_device)
        
        # Actualizar transacción
        transaction.status = 'voided'
        transaction.clover_response = response
        transaction.save()
        
        return transaction
    
    def get_transaction_status(self, transaction, device=None):
        """
        Obtener estado actual de una transacción
        """
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified"))
        
        endpoint = f"merchants/{target_device.merchant_id}/payments/{transaction.clover_transaction_id}"
        response = self._make_request('GET', endpoint, device=target_device)
        
        # Actualizar estado local
        transaction.status = self._map_clover_status(response.get('status'))
        transaction.clover_response = response
        transaction.save()
        
        return transaction
    
    def _map_clover_status(self, clover_status):
        """Mapear estado de Clover a estado interno"""
        status_mapping = {
            'PENDING': 'pending',
            'PAID': 'approved',
            'DECLINED': 'declined',
            'VOIDED': 'voided',
            'REFUNDED': 'refunded',
            'ERROR': 'error',
        }
        
        return status_mapping.get(clover_status, 'pending')
    
    def test_connection(self, device=None):
        """
        Probar conexión con Clover
        """
        target_device = device or self.device
        
        if not target_device:
            raise ValidationError(_("No device specified for connection test"))
        
        try:
            # Intentar obtener información del dispositivo
            device_info = self.get_device_info(target_device)
            return {
                'success': True,
                'device_info': device_info,
                'message': _("Connection successful")
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': _("Connection failed")
            } 