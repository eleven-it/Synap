from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import SalesOrder, SalesOrderLine, ApprovalLog
from .services import SalesInventoryService, SalesInventoryValidator


@receiver(post_save, sender=SalesOrderLine)
def recalculate_order_totals_on_line_save(sender, instance, created, **kwargs):
    """
    Recalcular totales del pedido cuando se guarda una línea
    """
    if instance.sales_order:
        # Usar transaction.on_commit para evitar problemas de concurrencia
        transaction.on_commit(
            lambda: instance.sales_order.recalculate_totals()
        )


@receiver(post_delete, sender=SalesOrderLine)
def recalculate_order_totals_on_line_delete(sender, instance, **kwargs):
    """
    Recalcular totales del pedido cuando se elimina una línea
    """
    if instance.sales_order:
        transaction.on_commit(
            lambda: instance.sales_order.recalculate_totals()
        )


@receiver(pre_save, sender=SalesOrderLine)
def validate_line_before_save(sender, instance, **kwargs):
    """
    Validar línea antes de guardar
    """
    # Validar que la cantidad sea positiva
    if instance.quantity <= 0:
        from django.core.exceptions import ValidationError
        raise ValidationError('Quantity must be greater than 0')
    
    # Validar que el precio unitario sea positivo
    if instance.unit_price <= 0:
        from django.core.exceptions import ValidationError
        raise ValidationError('Unit price must be greater than 0')
    
    # Validar descuento
    if instance.discount < 0 or instance.discount > 100:
        from django.core.exceptions import ValidationError
        raise ValidationError('Discount must be between 0 and 100')


@receiver(post_save, sender=SalesOrder)
def update_line_states_on_order_state_change(sender, instance, **kwargs):
    """
    Actualizar estados de las líneas cuando cambia el estado del pedido
    """
    from .models import SalesOrderStates, SalesOrderLineStates
    
    # Solo procesar si el estado cambió
    if kwargs.get('update_fields') and 'state' not in kwargs['update_fields']:
        return
    
    # Obtener el estado anterior (esto requiere tracking manual)
    # Por ahora, actualizaremos las líneas según el estado actual
    
    if instance.state == SalesOrderStates.CONFIRMED:
        # Marcar líneas como confirmadas
        instance.lines.filter(state=SalesOrderLineStates.DRAFT).update(
            state=SalesOrderLineStates.CONFIRMED
        )
    
    elif instance.state == SalesOrderStates.IN_PROCESS:
        # Marcar líneas como en proceso
        instance.lines.filter(state=SalesOrderLineStates.CONFIRMED).update(
            state=SalesOrderLineStates.IN_PROCESS
        )
    
    elif instance.state == SalesOrderStates.READY_TO_DELIVER:
        # Mantener líneas en proceso (listas para entregar)
        pass
    
    elif instance.state == SalesOrderStates.DELIVERED:
        # Marcar todas las líneas como entregadas
        instance.lines.exclude(state=SalesOrderLineStates.CANCELLED).update(
            state=SalesOrderLineStates.DELIVERED
        )
    
    elif instance.state == SalesOrderStates.CANCELLED:
        # Marcar todas las líneas como canceladas
        instance.lines.exclude(state=SalesOrderLineStates.CANCELLED).update(
            state=SalesOrderLineStates.CANCELLED
        )


@receiver(post_save, sender=ApprovalLog)
def log_state_change_notification(sender, instance, created, **kwargs):
    """
    Enviar notificaciones cuando se registra un cambio de estado
    """
    if created and instance.action.startswith('state_changed'):
        # TODO: Implementar notificaciones por email, webhook, etc.
        # Por ejemplo:
        # - Notificar al cliente cuando se envía cotización
        # - Notificar al vendedor cuando se confirma pedido
        # - Notificar al almacén cuando está listo para entregar
        pass


@receiver(pre_save, sender=SalesOrder)
def validate_order_before_save(sender, instance, **kwargs):
    """
    Validaciones adicionales del pedido antes de guardar
    """
    # Validar que el pedido tenga al menos una línea
    if instance.pk:  # Solo para pedidos existentes
        if not instance.lines.exists():
            from django.core.exceptions import ValidationError
            raise ValidationError('Sales order must have at least one line')
    
    # Validar límite de crédito
    if instance.client and not instance.manual_credit_override:
        if instance.total > instance.client.credit_limit:
            from django.core.exceptions import ValidationError
            raise ValidationError(
                f'Order total ({instance.total}) exceeds client credit limit ({instance.client.credit_limit})'
            )


@receiver(post_save, sender=SalesOrder)
def create_initial_log_on_creation(sender, instance, created, **kwargs):
    """
    Crear log inicial cuando se crea un pedido
    """
    if created:
        ApprovalLog.objects.create(
            sales_order=instance,
            user=instance.seller,
            action='order_created',
            reason='Sales order created'
        )


# Señales para integración con inventario
@receiver(post_save, sender=SalesOrder)
def update_inventory_reservations(sender, instance, **kwargs):
    """
    Actualizar reservas de inventario según el estado del pedido
    """
    from .models import SalesOrderStates
    
    # Solo procesar si el estado cambió
    if kwargs.get('update_fields') and 'state' not in kwargs['update_fields']:
        return
    
    # Obtener el usuario que realizó el cambio (desde el contexto)
    user = getattr(instance, '_current_user', None)
    if not user:
        # Si no hay usuario en contexto, usar el vendedor del pedido
        user = instance.seller
    
    if instance.state == SalesOrderStates.CONFIRMED:
        # Reservar stock para el pedido
        try:
            reservations = SalesInventoryService.reserve_stock_for_order(instance, user)
            # Crear log de reserva
            ApprovalLog.objects.create(
                sales_order=instance,
                user=user,
                action='stock_reserved',
                reason=f'Stock reserved for {len(reservations)} items'
            )
        except Exception as e:
            # Si falla la reserva, revertir el estado del pedido
            instance.state = SalesOrderStates.DRAFT
            instance.save(update_fields=['state'])
            raise ValidationError(f'Failed to reserve stock: {str(e)}')
    
    elif instance.state in [SalesOrderStates.CANCELLED, SalesOrderStates.COMPLETED]:
        # Liberar reservas de stock
        try:
            released_count = SalesInventoryService.release_stock_reservations(instance, user)
            if released_count > 0:
                ApprovalLog.objects.create(
                    sales_order=instance,
                    user=user,
                    action='stock_released',
                    reason=f'Stock reservations released: {released_count} items'
                )
        except Exception as e:
            # Log el error pero no revertir el estado del pedido
            ApprovalLog.objects.create(
                sales_order=instance,
                user=user,
                action='stock_release_error',
                reason=f'Error releasing stock: {str(e)}'
            )


@receiver(post_save, sender=SalesOrder)
def create_stock_moves_on_delivery(sender, instance, **kwargs):
    """
    Crear movimientos de stock cuando se entrega un pedido
    """
    from .models import SalesOrderStates
    
    # Solo procesar si el estado cambió
    if kwargs.get('update_fields') and 'state' not in kwargs['update_fields']:
        return
    
    # Obtener el usuario que realizó el cambio
    user = getattr(instance, '_current_user', None)
    if not user:
        user = instance.seller
    
    if instance.state == SalesOrderStates.DELIVERED:
        # Crear movimientos de stock para la entrega
        try:
            stock_moves = SalesInventoryService.create_stock_moves_for_delivery(instance, user)
            if stock_moves:
                ApprovalLog.objects.create(
                    sales_order=instance,
                    user=user,
                    action='stock_moves_created',
                    reason=f'Stock moves created for delivery: {len(stock_moves)} moves'
                )
        except Exception as e:
            # Si falla la creación de movimientos, revertir el estado
            instance.state = SalesOrderStates.READY_TO_DELIVER
            instance.save(update_fields=['state'])
            raise ValidationError(f'Failed to create stock moves: {str(e)}')


# Señales para integración con facturación (futuro)
@receiver(post_save, sender=SalesOrder)
def auto_create_invoice_when_ready(sender, instance, **kwargs):
    """
    Crear factura automáticamente cuando el pedido está listo
    """
    from .models import SalesOrderStates
    
    if instance.state == SalesOrderStates.DELIVERED:
        # TODO: Crear factura automáticamente si está configurado
        pass 