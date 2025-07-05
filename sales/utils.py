from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import SalesOrder, SalesOrderLine, SalesOrderStates, SalesOrderLineStates


class SalesOrderCalculator:
    """Clase para cálculos relacionados con pedidos de venta"""
    
    @staticmethod
    def calculate_line_subtotal(quantity, unit_price, discount_percent=0):
        """Calcular subtotal de una línea"""
        total = quantity * unit_price
        discount_amount = total * (Decimal(str(discount_percent)) / Decimal('100'))
        return total - discount_amount
    
    @staticmethod
    def calculate_order_totals(sales_order):
        """Calcular totales del pedido"""
        total = Decimal('0.00')
        total_discount = Decimal('0.00')
        total_tax = Decimal('0.00')
        
        for line in sales_order.lines.all():
            line_total = line.quantity * line.unit_price
            line_discount = line_total * (line.discount / Decimal('100'))
            
            total += line_total
            total_discount += line_discount
            # TODO: Calcular impuestos según configuración fiscal
        
        return {
            'total': total,
            'total_discount': total_discount,
            'total_tax': total_tax,
            'subtotal': total - total_discount,
            'grand_total': total - total_discount + total_tax
        }
    
    @staticmethod
    def calculate_delivery_progress(sales_order):
        """Calcular progreso de entrega"""
        if not sales_order.lines.exists():
            return 0
        
        delivered_lines = sales_order.lines.filter(
            state=SalesOrderLineStates.DELIVERED
        )
        return (delivered_lines.count() / sales_order.lines.count()) * 100
    
    @staticmethod
    def calculate_payment_progress(sales_order):
        """Calcular progreso de pago basado en el estado"""
        progress_map = {
            SalesOrderStates.DRAFT: 0,
            SalesOrderStates.QUOTATION_SENT: 10,
            SalesOrderStates.CONFIRMED: 25,
            SalesOrderStates.IN_PROCESS: 35,
            SalesOrderStates.READY_TO_DELIVER: 45,
            SalesOrderStates.PARTIALLY_DELIVERED: 60,
            SalesOrderStates.DELIVERED: 75,
            SalesOrderStates.INVOICED: 85,
            SalesOrderStates.PAID: 100,
            SalesOrderStates.COMPLETED: 100,
            SalesOrderStates.CANCELLED: 0,
        }
        return progress_map.get(sales_order.state, 0)


class SalesOrderValidator:
    """Clase para validaciones de pedidos de venta"""
    
    @staticmethod
    def validate_state_transition(current_state, new_state):
        """Validar transición de estado"""
        valid_transitions = SalesOrderStates.VALID_TRANSITIONS.get(current_state, [])
        if new_state not in valid_transitions:
            raise ValidationError(
                f'Invalid state transition from {current_state} to {new_state}'
            )
    
    @staticmethod
    def validate_order_for_confirmation(sales_order):
        """Validar pedido antes de confirmación"""
        errors = []
        
        # Verificar que tenga líneas
        if not sales_order.lines.exists():
            errors.append('Order must have at least one line')
        
        # Verificar que las líneas tengan productos válidos
        for line in sales_order.lines.all():
            if not line.product_variant.is_active:
                errors.append(f'Product {line.product_variant} is not active')
        
        # Verificar límite de crédito
        if not sales_order.manual_credit_override:
            totals = SalesOrderCalculator.calculate_order_totals(sales_order)
            if totals['grand_total'] > sales_order.client.credit_limit:
                errors.append(
                    f'Order total ({totals["grand_total"]}) exceeds client credit limit ({sales_order.client.credit_limit})'
                )
        
        if errors:
            raise ValidationError('; '.join(errors))
    
    @staticmethod
    def validate_order_for_delivery(sales_order):
        """Validar pedido antes de entrega"""
        errors = []
        
        # Verificar que esté confirmado
        if sales_order.state not in [
            SalesOrderStates.CONFIRMED,
            SalesOrderStates.IN_PROCESS,
            SalesOrderStates.READY_TO_DELIVER
        ]:
            errors.append('Order must be confirmed before delivery')
        
        # Verificar stock disponible (futuro)
        # TODO: Implementar validación de stock
        
        if errors:
            raise ValidationError('; '.join(errors))
    
    @staticmethod
    def validate_order_for_invoicing(sales_order):
        """Validar pedido antes de facturación"""
        errors = []
        
        # Verificar que esté entregado
        if sales_order.state not in [
            SalesOrderStates.DELIVERED,
            SalesOrderStates.INVOICED
        ]:
            errors.append('Order must be delivered before invoicing')
        
        # Verificar que no tenga factura previa
        if hasattr(sales_order, 'invoice') and sales_order.invoice:
            errors.append('Order already has an invoice')
        
        if errors:
            raise ValidationError('; '.join(errors))


class SalesOrderWorkflow:
    """Clase para manejar el flujo de trabajo de pedidos"""
    
    @staticmethod
    @transaction.atomic
    def send_quotation(sales_order, user, reason):
        """Enviar cotización al cliente"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.QUOTATION_SENT
        )
        
        if not reason:
            raise ValidationError('Reason is required for sending quotation')
        
        sales_order.send_quotation(user, reason)
        return sales_order
    
    @staticmethod
    @transaction.atomic
    def confirm_order(sales_order, user, reason):
        """Confirmar pedido por el cliente"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.CONFIRMED
        )
        SalesOrderValidator.validate_order_for_confirmation(sales_order)
        
        if not reason:
            raise ValidationError('Reason is required for order confirmation')
        
        sales_order.confirm_order(user, reason)
        return sales_order
    
    @staticmethod
    @transaction.atomic
    def start_processing(sales_order, user, reason):
        """Iniciar procesamiento del pedido"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.IN_PROCESS
        )
        
        if not reason:
            raise ValidationError('Reason is required for starting processing')
        
        sales_order.start_processing(user, reason)
        return sales_order
    
    @staticmethod
    @transaction.atomic
    def mark_ready_to_deliver(sales_order, user, reason):
        """Marcar como listo para entregar"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.READY_TO_DELIVER
        )
        
        if not reason:
            raise ValidationError('Reason is required for marking ready to deliver')
        
        sales_order.mark_ready_to_deliver(user, reason)
        return sales_order
    
    @staticmethod
    @transaction.atomic
    def mark_delivered(sales_order, user, reason):
        """Marcar como entregado"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.DELIVERED
        )
        SalesOrderValidator.validate_order_for_delivery(sales_order)
        
        if not reason:
            raise ValidationError('Reason is required for marking as delivered')
        
        sales_order.mark_delivered(user, reason)
        return sales_order
    
    @staticmethod
    @transaction.atomic
    def mark_invoiced(sales_order, user, reason):
        """Marcar como facturado"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.INVOICED
        )
        SalesOrderValidator.validate_order_for_invoicing(sales_order)
        
        if not reason:
            raise ValidationError('Reason is required for marking as invoiced')
        
        sales_order.mark_invoiced(user, reason)
        return sales_order
    
    @staticmethod
    @transaction.atomic
    def mark_paid(sales_order, user, reason):
        """Marcar como pagado"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.PAID
        )
        
        if not reason:
            raise ValidationError('Reason is required for marking as paid')
        
        sales_order.mark_paid(user, reason)
        return sales_order
    
    @staticmethod
    @transaction.atomic
    def cancel_order(sales_order, user, reason):
        """Cancelar pedido"""
        SalesOrderValidator.validate_state_transition(
            sales_order.state, 
            SalesOrderStates.CANCELLED
        )
        
        if not reason:
            raise ValidationError('Reason is required for cancelling order')
        
        sales_order.cancel_order(user, reason)
        return sales_order


class SalesOrderReporter:
    """Clase para reportes y estadísticas de pedidos"""
    
    @staticmethod
    def get_orders_by_state():
        """Obtener pedidos agrupados por estado"""
        from django.db.models import Count, Sum
        
        return SalesOrder.objects.values('state').annotate(
            count=Count('id'),
            total_amount=Sum('total')
        ).order_by('state')
    
    @staticmethod
    def get_monthly_sales(year=None, month=None):
        """Obtener ventas mensuales"""
        from django.db.models import Count, Sum
        
        if not year:
            year = timezone.now().year
        if not month:
            month = timezone.now().month
        
        return SalesOrder.objects.filter(
            order_date__year=year,
            order_date__month=month
        ).aggregate(
            total_orders=Count('id'),
            total_amount=Sum('total'),
            total_discount=Sum('total_discount'),
            total_tax=Sum('total_tax')
        )
    
    @staticmethod
    def get_top_clients(limit=10):
        """Obtener top clientes por volumen de ventas"""
        from django.db.models import Count, Sum
        
        return SalesOrder.objects.values(
            'client__name'
        ).annotate(
            total_orders=Count('id'),
            total_amount=Sum('total')
        ).order_by('-total_amount')[:limit]
    
    @staticmethod
    def get_sales_trend(days=30):
        """Obtener tendencia de ventas"""
        from django.db.models import Count, Sum
        from datetime import timedelta
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        return SalesOrder.objects.filter(
            order_date__range=[start_date, end_date]
        ).values('order_date').annotate(
            orders_count=Count('id'),
            total_amount=Sum('total')
        ).order_by('order_date')


class SalesOrderNotificationHelper:
    """Clase para manejar notificaciones de pedidos"""
    
    @staticmethod
    def notify_quotation_sent(sales_order):
        """Notificar envío de cotización"""
        # TODO: Implementar notificación por email al cliente
        pass
    
    @staticmethod
    def notify_order_confirmed(sales_order):
        """Notificar confirmación de pedido"""
        # TODO: Implementar notificación al vendedor y almacén
        pass
    
    @staticmethod
    def notify_ready_to_deliver(sales_order):
        """Notificar que está listo para entregar"""
        # TODO: Implementar notificación al almacén
        pass
    
    @staticmethod
    def notify_delivered(sales_order):
        """Notificar entrega completada"""
        # TODO: Implementar notificación al cliente y facturación
        pass 