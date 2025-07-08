"""
Configuración de hooks para el módulo de compras
"""

from core.module_events import ModuleEvents, EventDataBuilder


def on_purchase_created(event_data):
    """Hook que se ejecuta cuando se crea una orden de compra"""
    purchase_id = event_data.get('purchase_id')
    details = event_data.get('details', {})
    
    # Enviar solicitud de cotización
    send_quote_request(purchase_id, details)
    
    # Notificar aprobadores
    notify_approvers(purchase_id, details)
    
    # Crear entrada contable preliminar
    create_purchase_accounting_entry(purchase_id, details, 'draft')
    
    return f"Purchase {purchase_id} created successfully"


def on_purchase_updated(event_data):
    """Hook que se ejecuta cuando se actualiza una orden de compra"""
    purchase_id = event_data.get('purchase_id')
    details = event_data.get('details', {})
    
    # Actualizar entrada contable si cambió
    if details.get('amount_changed'):
        update_purchase_accounting_entry(purchase_id, details)
    
    # Re-notificar si cambió el monto
    if details.get('amount_changed'):
        notify_approvers(purchase_id, details)
    
    return f"Purchase {purchase_id} updated successfully"


def on_purchase_approved(event_data):
    """Hook que se ejecuta cuando se aprueba una orden de compra"""
    purchase_id = event_data.get('purchase_id')
    details = event_data.get('details', {})
    
    # Confirmar entrada contable
    confirm_purchase_accounting_entry(purchase_id, details)
    
    # Enviar orden al proveedor
    send_order_to_supplier(purchase_id, details)
    
    # Notificar al solicitante
    notify_requester(purchase_id, 'approved')
    
    return f"Purchase {purchase_id} approved successfully"


def on_purchase_rejected(event_data):
    """Hook que se ejecuta cuando se rechaza una orden de compra"""
    purchase_id = event_data.get('purchase_id')
    details = event_data.get('details', {})
    
    # Cancelar entrada contable
    cancel_purchase_accounting_entry(purchase_id, details)
    
    # Notificar al solicitante
    notify_requester(purchase_id, 'rejected', details.get('rejection_reason'))
    
    return f"Purchase {purchase_id} rejected successfully"


def on_receipt_created(event_data):
    """Hook que se ejecuta cuando se crea un recibo de compra"""
    receipt_id = event_data.get('purchase_id')  # En este contexto, purchase_id es receipt_id
    details = event_data.get('details', {})
    
    # Actualizar inventario
    update_inventory_from_receipt(receipt_id, details)
    
    # Crear entrada contable para recibo
    create_receipt_accounting_entry(receipt_id, details)
    
    # Actualizar estado de la orden de compra
    update_purchase_status(receipt_id, 'received')
    
    # Calificar al proveedor
    rate_supplier(receipt_id, details)
    
    return f"Receipt {receipt_id} created successfully"


def on_supplier_created(event_data):
    """Hook que se ejecuta cuando se crea un proveedor"""
    supplier_id = event_data.get('supplier_id')
    details = event_data.get('details', {})
    
    # Crear cuenta contable para proveedor
    create_supplier_account(supplier_id, details)
    
    # Enviar email de bienvenida
    send_supplier_welcome_email(supplier_id, details.get('email'))
    
    # Asignar categoría por defecto
    assign_default_supplier_category(supplier_id, details)
    
    return f"Supplier {supplier_id} created successfully"


def on_supplier_rated(event_data):
    """Hook que se ejecuta cuando se califica un proveedor"""
    supplier_id = event_data.get('supplier_id')
    details = event_data.get('details', {})
    rating = details.get('rating', 0)
    
    # Actualizar calificación promedio
    update_supplier_rating(supplier_id, rating)
    
    # Notificar si la calificación es baja
    if rating < 3:
        notify_low_supplier_rating(supplier_id, rating)
    
    # Actualizar categoría si es necesario
    update_supplier_category(supplier_id, rating)
    
    return f"Supplier {supplier_id} rated with {rating} stars"


# Funciones auxiliares (simuladas)
def send_quote_request(purchase_id, details):
    """Envía solicitud de cotización"""
    print(f"Sending quote request for purchase {purchase_id}")
    # Aquí iría la lógica real de envío de cotización


def notify_approvers(purchase_id, details):
    """Notifica a los aprobadores"""
    print(f"Notifying approvers for purchase {purchase_id}")
    # Aquí iría la lógica real de notificación


def create_purchase_accounting_entry(purchase_id, details, status):
    """Crea entrada contable para compra"""
    print(f"Creating {status} accounting entry for purchase {purchase_id}")
    # Aquí iría la lógica real de creación de entrada contable


def update_purchase_accounting_entry(purchase_id, details):
    """Actualiza entrada contable de compra"""
    print(f"Updating accounting entry for purchase {purchase_id}")
    # Aquí iría la lógica real de actualización de entrada contable


def confirm_purchase_accounting_entry(purchase_id, details):
    """Confirma entrada contable de compra"""
    print(f"Confirming accounting entry for purchase {purchase_id}")
    # Aquí iría la lógica real de confirmación de entrada contable


def send_order_to_supplier(purchase_id, details):
    """Envía orden al proveedor"""
    print(f"Sending order to supplier for purchase {purchase_id}")
    # Aquí iría la lógica real de envío de orden


def notify_requester(purchase_id, status, reason=None):
    """Notifica al solicitante"""
    print(f"Notifying requester for purchase {purchase_id} - {status}")
    if reason:
        print(f"Reason: {reason}")
    # Aquí iría la lógica real de notificación


def cancel_purchase_accounting_entry(purchase_id, details):
    """Cancela entrada contable de compra"""
    print(f"Cancelling accounting entry for purchase {purchase_id}")
    # Aquí iría la lógica real de cancelación de entrada contable


def update_inventory_from_receipt(receipt_id, details):
    """Actualiza inventario desde recibo"""
    print(f"Updating inventory from receipt {receipt_id}")
    # Aquí iría la lógica real de actualización de inventario


def create_receipt_accounting_entry(receipt_id, details):
    """Crea entrada contable para recibo"""
    print(f"Creating accounting entry for receipt {receipt_id}")
    # Aquí iría la lógica real de creación de entrada contable


def update_purchase_status(receipt_id, status):
    """Actualiza estado de la orden de compra"""
    print(f"Updating purchase status to {status} for receipt {receipt_id}")
    # Aquí iría la lógica real de actualización de estado


def rate_supplier(receipt_id, details):
    """Califica al proveedor"""
    print(f"Rating supplier for receipt {receipt_id}")
    # Aquí iría la lógica real de calificación


def create_supplier_account(supplier_id, details):
    """Crea cuenta contable para proveedor"""
    print(f"Creating accounting account for supplier {supplier_id}")
    # Aquí iría la lógica real de creación de cuenta


def send_supplier_welcome_email(supplier_id, email):
    """Envía email de bienvenida al proveedor"""
    print(f"Sending welcome email to supplier {supplier_id} at {email}")
    # Aquí iría la lógica real de envío de email


def assign_default_supplier_category(supplier_id, details):
    """Asigna categoría por defecto al proveedor"""
    print(f"Assigning default category to supplier {supplier_id}")
    # Aquí iría la lógica real de asignación de categoría


def update_supplier_rating(supplier_id, rating):
    """Actualiza calificación promedio del proveedor"""
    print(f"Updating average rating for supplier {supplier_id} to {rating}")
    # Aquí iría la lógica real de actualización de calificación


def notify_low_supplier_rating(supplier_id, rating):
    """Notifica calificación baja del proveedor"""
    print(f"Notifying low rating for supplier {supplier_id}: {rating}")
    # Aquí iría la lógica real de notificación


def update_supplier_category(supplier_id, rating):
    """Actualiza categoría del proveedor basada en calificación"""
    print(f"Updating category for supplier {supplier_id} based on rating {rating}")
    # Aquí iría la lógica real de actualización de categoría


# Configuración de hooks
HOOKS = {
    'event_purchase.created': {
        'callback': on_purchase_created,
        'description': 'Hook que se ejecuta cuando se crea una orden de compra',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'purchases',
            'type': 'creation'
        }
    },
    'event_purchase.updated': {
        'callback': on_purchase_updated,
        'description': 'Hook que se ejecuta cuando se actualiza una orden de compra',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'purchases',
            'type': 'update'
        }
    },
    'event_purchase.approved': {
        'callback': on_purchase_approved,
        'description': 'Hook que se ejecuta cuando se aprueba una orden de compra',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'purchases',
            'type': 'approval'
        }
    },
    'event_purchase.rejected': {
        'callback': on_purchase_rejected,
        'description': 'Hook que se ejecuta cuando se rechaza una orden de compra',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'purchases',
            'type': 'rejection'
        }
    },
    'event_receipt.created': {
        'callback': on_receipt_created,
        'description': 'Hook que se ejecuta cuando se crea un recibo de compra',
        'priority': 10,
        'dependencies': ['inventory', 'accounting'],
        'metadata': {
            'category': 'purchases',
            'type': 'receipt'
        }
    },
    'event_supplier.created': {
        'callback': on_supplier_created,
        'description': 'Hook que se ejecuta cuando se crea un proveedor',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'purchases',
            'type': 'supplier_creation'
        }
    },
    'event_supplier.rated': {
        'callback': on_supplier_rated,
        'description': 'Hook que se ejecuta cuando se califica un proveedor',
        'priority': 10,
        'dependencies': [],
        'metadata': {
            'category': 'purchases',
            'type': 'rating'
        }
    }
} 