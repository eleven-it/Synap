from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    PurchaseRequest, PurchaseOrder, PurchaseQuotation, 
    PurchaseReceipt, SupplierRating, ApprovalRecord
)


@receiver(post_save, sender=PurchaseRequest)
def purchase_request_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una solicitud de compra
    """
    if created:
        # Lógica para solicitudes nuevas
        pass
    
    # Actualizar totales si es necesario
    if hasattr(instance, 'calculate_totals'):
        instance.calculate_totals()


@receiver(post_save, sender=PurchaseOrder)
def purchase_order_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una orden de compra
    """
    if created:
        # Lógica para órdenes nuevas
        pass
    
    # Evitar recursión infinita: no calcular totales si solo se están actualizando campos de totales
    if kwargs.get('update_fields') and set(kwargs['update_fields']).issubset({
        'subtotal', 'tax_amount', 'discount_amount', 'shipping_amount', 'total_amount'
    }):
        return
    
    # Actualizar totales si es necesario
    if hasattr(instance, 'calculate_totals'):
        instance.calculate_totals()


@receiver(post_save, sender=PurchaseQuotation)
def purchase_quotation_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una cotización
    """
    if created:
        # Lógica para cotizaciones nuevas
        pass
    
    # Evitar recursión infinita: no calcular totales si solo se están actualizando campos de totales
    if kwargs.get('update_fields') and set(kwargs['update_fields']).issubset({
        'subtotal', 'tax_amount', 'discount_amount', 'total_amount'
    }):
        return
    
    # Actualizar totales si es necesario
    if hasattr(instance, 'calculate_totals'):
        instance.calculate_totals()


@receiver(post_save, sender=PurchaseReceipt)
def purchase_receipt_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una recepción
    """
    if created:
        # Lógica para recepciones nuevas
        pass


@receiver(post_save, sender=SupplierRating)
def supplier_rating_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una evaluación de proveedor
    """
    if created:
        # Lógica para evaluaciones nuevas
        pass


@receiver(post_save, sender=ApprovalRecord)
def approval_record_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un registro de aprobación
    """
    if created:
        # Lógica para registros de aprobación nuevos
        pass


# Señales para actualización de stock
@receiver(post_save, sender=PurchaseReceipt)
def update_stock_on_receipt(sender, instance, **kwargs):
    """
    Actualiza el stock cuando se aprueba una recepción
    """
    if instance.status == 'approved' and instance.quality_score:
        # La actualización de stock se maneja en el método approve() del modelo
        pass


# Señales para notificaciones
@receiver(post_save, sender=PurchaseRequest)
def notify_purchase_request_created(sender, instance, created, **kwargs):
    """
    Notifica cuando se crea una nueva solicitud de compra
    """
    if created:
        # Aquí se pueden agregar notificaciones por email, etc.
        pass


@receiver(post_save, sender=PurchaseOrder)
def notify_purchase_order_status_change(sender, instance, **kwargs):
    """
    Notifica cambios de estado en órdenes de compra
    """
    # Aquí se pueden agregar notificaciones por email, etc.
    pass


@receiver(post_save, sender=PurchaseReceipt)
def notify_receipt_status_change(sender, instance, **kwargs):
    """
    Notifica cambios de estado en recepciones
    """
    # Aquí se pueden agregar notificaciones por email, etc.
    pass 