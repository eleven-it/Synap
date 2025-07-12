import json
import logging
import hashlib
import hmac
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from mercadopago.models import MercadoPagoTransaction, MercadoPagoConfig
from mercadopago.services.payment_service import MercadoPagoPaymentService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_handler(request):
    """
    Webhook principal para recibir notificaciones de MercadoPago
    """
    try:
        # Verificar firma del webhook si está configurada
        if hasattr(settings, 'MERCADOPAGO_WEBHOOK_SECRET') and settings.MERCADOPAGO_WEBHOOK_SECRET:
            signature = request.headers.get('X-Signature')
            if not verify_webhook_signature(request.body, signature, settings.MERCADOPAGO_WEBHOOK_SECRET):
                logger.warning("Invalid webhook signature")
                return JsonResponse({'error': 'Invalid signature'}, status=400)
        
        # Parsear datos del webhook
        data = json.loads(request.body)
        logger.info(f"Webhook received: {data}")
        
        # Procesar notificación
        if data.get('type') == 'payment':
            payment_id = data.get('data', {}).get('id')
            if payment_id:
                process_payment_notification(payment_id)
        
        return JsonResponse({'status': 'ok'})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return JsonResponse({'error': 'Internal error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def smartpos_webhook_handler(request):
    """
    Webhook específico para dispositivos SmartPOS
    """
    try:
        data = json.loads(request.body)
        logger.info(f"SmartPOS webhook received: {data}")
        
        # Procesar notificación de SmartPOS
        if data.get('type') == 'device_status':
            device_id = data.get('data', {}).get('device_id')
            if device_id:
                process_device_status_notification(device_id, data.get('data', {}))
        
        elif data.get('type') == 'payment':
            payment_id = data.get('data', {}).get('id')
            if payment_id:
                process_smartpos_payment_notification(payment_id, data.get('data', {}))
        
        return JsonResponse({'status': 'ok'})
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in SmartPOS webhook")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"SmartPOS webhook error: {str(e)}")
        return JsonResponse({'error': 'Internal error'}, status=500)


def process_payment_notification(payment_id):
    """
    Procesar notificación de pago
    """
    try:
        # Buscar transacción
        transaction = MercadoPagoTransaction.objects.filter(mercadopago_id=payment_id).first()
        if not transaction:
            logger.warning(f"Transaction not found for payment_id: {payment_id}")
            return
        
        # Obtener información actualizada del pago
        service = MercadoPagoPaymentService(transaction.empresa)
        payment_info = service.get_payment_status(payment_id)
        
        if 'error' not in payment_info:
            # Actualizar estado de la transacción
            old_status = transaction.status
            transaction.status = payment_info.get('status', transaction.status)
            transaction.status_detail = payment_info.get('status_detail', transaction.status_detail)
            transaction.save(update_fields=['status', 'status_detail'])
            
            logger.info(f"Transaction {payment_id} status updated: {old_status} -> {transaction.status}")
            
            # Procesar acciones adicionales según el estado
            if transaction.status == 'approved':
                process_approved_payment(transaction)
            elif transaction.status == 'rejected':
                process_rejected_payment(transaction)
            elif transaction.status == 'refunded':
                process_refunded_payment(transaction)
        
    except Exception as e:
        logger.error(f"Error processing payment notification: {str(e)}")


def process_device_status_notification(device_id, data):
    """
    Procesar notificación de cambio de estado de dispositivo
    """
    try:
        from mercadopago.models import MercadoPagoDevice
        from mercadopago.services.smartpos_service import MercadoPagoSmartPOSService
        
        device = MercadoPagoDevice.objects.filter(device_id=device_id).first()
        if not device:
            logger.warning(f"Device not found for device_id: {device_id}")
            return
        
        # Actualizar estado del dispositivo
        status = data.get('status', device.status)
        connection_status = data.get('connection_status', device.connection_status)
        
        device.status = status
        device.connection_status = connection_status
        device.save(update_fields=['status', 'connection_status'])
        
        logger.info(f"Device {device_id} status updated: {status}, connection: {connection_status}")
        
    except Exception as e:
        logger.error(f"Error processing device status notification: {str(e)}")


def process_smartpos_payment_notification(payment_id, data):
    """
    Procesar notificación de pago de SmartPOS
    """
    try:
        # Buscar transacción por device_transaction_id
        device_transaction_id = data.get('device_transaction_id')
        if device_transaction_id:
            transaction = MercadoPagoTransaction.objects.filter(
                device_transaction_id=device_transaction_id
            ).first()
            
            if transaction:
                # Actualizar información del dispositivo
                transaction.device_response = data
                transaction.save(update_fields=['device_response'])
                
                # Procesar como notificación de pago normal
                process_payment_notification(payment_id)
        
    except Exception as e:
        logger.error(f"Error processing SmartPOS payment notification: {str(e)}")


def process_approved_payment(transaction):
    """
    Procesar pago aprobado
    """
    try:
        logger.info(f"Processing approved payment: {transaction.mercadopago_id}")
        
        # Aquí se pueden agregar acciones adicionales como:
        # - Enviar email de confirmación
        # - Actualizar inventario
        # - Generar factura automática
        # - Notificar al cliente
        
    except Exception as e:
        logger.error(f"Error processing approved payment: {str(e)}")


def process_rejected_payment(transaction):
    """
    Procesar pago rechazado
    """
    try:
        logger.info(f"Processing rejected payment: {transaction.mercadopago_id}")
        
        # Aquí se pueden agregar acciones adicionales como:
        # - Enviar email de notificación
        # - Revertir cambios en inventario
        # - Notificar al cliente
        
    except Exception as e:
        logger.error(f"Error processing rejected payment: {str(e)}")


def process_refunded_payment(transaction):
    """
    Procesar pago reembolsado
    """
    try:
        logger.info(f"Processing refunded payment: {transaction.mercadopago_id}")
        
        # Aquí se pueden agregar acciones adicionales como:
        # - Actualizar inventario
        # - Generar nota de crédito
        # - Notificar al cliente
        
    except Exception as e:
        logger.error(f"Error processing refunded payment: {str(e)}")


def verify_webhook_signature(payload, signature, secret):
    """
    Verificar firma del webhook
    """
    try:
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False


# URLs para webhooks
webhook_urls = [
    ('webhook/', webhook_handler, 'webhook'),
    ('smartpos-webhook/', smartpos_webhook_handler, 'smartpos_webhook'),
] 