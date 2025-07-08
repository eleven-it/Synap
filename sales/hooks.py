"""
Configuración de hooks para el módulo de ventas
"""

from core.module_events import ModuleEvents, EventDataBuilder


def on_sale_created(event_data):
    """Hook que se ejecuta cuando se crea una venta"""
    sale_id = event_data.get('sale_id')
    details = event_data.get('details', {})
    
    # Actualizar inventario
    update_inventory_for_sale(sale_id, details)
    
    # Crear entrada contable
    create_sales_accounting_entry(sale_id, details)
    
    # Enviar notificación
    send_sales_notification(sale_id, 'created')
    
    return f"Sale {sale_id} processed successfully"


def on_sale_updated(event_data):
    """Hook que se ejecuta cuando se actualiza una venta"""
    sale_id = event_data.get('sale_id')
    details = event_data.get('details', {})
    
    # Actualizar inventario si cambió
    if details.get('inventory_changed'):
        update_inventory_for_sale(sale_id, details)
    
    # Actualizar entrada contable
    update_sales_accounting_entry(sale_id, details)
    
    return f"Sale {sale_id} updated successfully"


def on_sale_cancelled(event_data):
    """Hook que se ejecuta cuando se cancela una venta"""
    sale_id = event_data.get('sale_id')
    
    # Revertir inventario
    revert_inventory_for_sale(sale_id)
    
    # Cancelar entrada contable
    cancel_sales_accounting_entry(sale_id)
    
    # Enviar notificación de cancelación
    send_sales_notification(sale_id, 'cancelled')
    
    return f"Sale {sale_id} cancelled successfully"


def on_invoice_created(event_data):
    """Hook que se ejecuta cuando se crea una factura"""
    invoice_id = event_data.get('sale_id')  # En este contexto, sale_id es invoice_id
    details = event_data.get('details', {})
    
    # Crear entrada contable para factura
    create_invoice_accounting_entry(invoice_id, details)
    
    # Enviar factura por email
    send_invoice_email(invoice_id, details.get('customer_email'))
    
    # Actualizar estado de la venta
    update_sale_status(invoice_id, 'invoiced')
    
    return f"Invoice {invoice_id} created successfully"


def on_payment_received(event_data):
    """Hook que se ejecuta cuando se recibe un pago"""
    payment_data = event_data.get('details', {})
    sale_id = payment_data.get('sale_id')
    amount = payment_data.get('amount', 0)
    
    # Crear entrada contable para pago
    create_payment_accounting_entry(sale_id, amount, payment_data)
    
    # Actualizar estado de la venta
    update_sale_status(sale_id, 'paid')
    
    # Enviar confirmación de pago
    send_payment_confirmation(sale_id, amount)
    
    return f"Payment for sale {sale_id} processed successfully"


def on_delivery_created(event_data):
    """Hook que se ejecuta cuando se crea una entrega"""
    delivery_id = event_data.get('sale_id')  # En este contexto, sale_id es delivery_id
    details = event_data.get('details', {})
    
    # Actualizar inventario para entrega
    update_inventory_for_delivery(delivery_id, details)
    
    # Crear entrada contable para entrega
    create_delivery_accounting_entry(delivery_id, details)
    
    # Enviar notificación de entrega
    send_delivery_notification(delivery_id, details.get('customer_email'))
    
    return f"Delivery {delivery_id} created successfully"


# Funciones auxiliares (simuladas)
def update_inventory_for_sale(sale_id, details):
    """Actualiza el inventario cuando se crea una venta"""
    print(f"Updating inventory for sale {sale_id}")
    # Aquí iría la lógica real de actualización de inventario


def create_sales_accounting_entry(sale_id, details):
    """Crea entrada contable para una venta"""
    print(f"Creating accounting entry for sale {sale_id}")
    # Aquí iría la lógica real de creación de entrada contable


def send_sales_notification(sale_id, action):
    """Envía notificación de venta"""
    print(f"Sending {action} notification for sale {sale_id}")
    # Aquí iría la lógica real de envío de notificaciones


def revert_inventory_for_sale(sale_id):
    """Revierte el inventario cuando se cancela una venta"""
    print(f"Reverting inventory for cancelled sale {sale_id}")
    # Aquí iría la lógica real de reversión de inventario


def cancel_sales_accounting_entry(sale_id):
    """Cancela entrada contable de una venta"""
    print(f"Cancelling accounting entry for sale {sale_id}")
    # Aquí iría la lógica real de cancelación de entrada contable


def create_invoice_accounting_entry(invoice_id, details):
    """Crea entrada contable para una factura"""
    print(f"Creating accounting entry for invoice {invoice_id}")
    # Aquí iría la lógica real de creación de entrada contable


def send_invoice_email(invoice_id, customer_email):
    """Envía factura por email"""
    print(f"Sending invoice {invoice_id} to {customer_email}")
    # Aquí iría la lógica real de envío de email


def update_sale_status(sale_id, status):
    """Actualiza el estado de una venta"""
    print(f"Updating sale {sale_id} status to {status}")
    # Aquí iría la lógica real de actualización de estado


def create_payment_accounting_entry(sale_id, amount, payment_data):
    """Crea entrada contable para un pago"""
    print(f"Creating payment accounting entry for sale {sale_id}, amount: ${amount}")
    # Aquí iría la lógica real de creación de entrada contable


def send_payment_confirmation(sale_id, amount):
    """Envía confirmación de pago"""
    print(f"Sending payment confirmation for sale {sale_id}, amount: ${amount}")
    # Aquí iría la lógica real de envío de confirmación


def update_inventory_for_delivery(delivery_id, details):
    """Actualiza inventario para entrega"""
    print(f"Updating inventory for delivery {delivery_id}")
    # Aquí iría la lógica real de actualización de inventario


def create_delivery_accounting_entry(delivery_id, details):
    """Crea entrada contable para entrega"""
    print(f"Creating accounting entry for delivery {delivery_id}")
    # Aquí iría la lógica real de creación de entrada contable


def send_delivery_notification(delivery_id, customer_email):
    """Envía notificación de entrega"""
    print(f"Sending delivery notification for {delivery_id} to {customer_email}")
    # Aquí iría la lógica real de envío de notificación


# Configuración de hooks
HOOKS = {
    'event_sale.created': {
        'callback': on_sale_created,
        'description': 'Hook que se ejecuta cuando se crea una venta',
        'priority': 10,
        'dependencies': ['inventory', 'accounting'],
        'metadata': {
            'category': 'sales',
            'type': 'creation'
        }
    },
    'event_sale.updated': {
        'callback': on_sale_updated,
        'description': 'Hook que se ejecuta cuando se actualiza una venta',
        'priority': 10,
        'dependencies': ['inventory', 'accounting'],
        'metadata': {
            'category': 'sales',
            'type': 'update'
        }
    },
    'event_sale.cancelled': {
        'callback': on_sale_cancelled,
        'description': 'Hook que se ejecuta cuando se cancela una venta',
        'priority': 10,
        'dependencies': ['inventory', 'accounting'],
        'metadata': {
            'category': 'sales',
            'type': 'cancellation'
        }
    },
    'event_invoice.created': {
        'callback': on_invoice_created,
        'description': 'Hook que se ejecuta cuando se crea una factura',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'sales',
            'type': 'invoice'
        }
    },
    'event_payment.received': {
        'callback': on_payment_received,
        'description': 'Hook que se ejecuta cuando se recibe un pago',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'sales',
            'type': 'payment'
        }
    },
    'event_delivery.created': {
        'callback': on_delivery_created,
        'description': 'Hook que se ejecuta cuando se crea una entrega',
        'priority': 10,
        'dependencies': ['inventory', 'accounting'],
        'metadata': {
            'category': 'sales',
            'type': 'delivery'
        }
    }
} 