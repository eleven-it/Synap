"""
Ejemplos de uso del sistema de hooks de Synap
Demuestra cómo implementar hooks en diferentes módulos
"""

from core.hook_manager import hook_manager
from core.event_dispatcher import event_dispatcher
from core.module_events import ModuleEvents, EventDataBuilder, EventPriority


# ============================================================================
# EJEMPLOS DE HOOKS PARA MÓDULO DE VENTAS
# ============================================================================

def sales_order_created_hook(event_data):
    """Hook que se ejecuta cuando se crea una orden de venta"""
    order_id = event_data.get('sale_id')
    print(f"Sales hook: Order {order_id} created")
    
    # Ejemplo: Actualizar inventario
    # update_inventory_for_sale(order_id)
    
    # Ejemplo: Enviar notificación
    # send_sales_notification(order_id)
    
    return f"Sales hook processed for order {order_id}"


def sales_payment_received_hook(event_data):
    """Hook que se ejecuta cuando se recibe un pago"""
    payment_data = event_data.get('details', {})
    amount = payment_data.get('amount', 0)
    
    print(f"Sales hook: Payment received - ${amount}")
    
    # Ejemplo: Actualizar estado de la orden
    # update_order_status(payment_data.get('order_id'), 'paid')
    
    # Ejemplo: Generar factura automática
    # generate_invoice(payment_data.get('order_id'))
    
    return f"Payment hook processed - ${amount}"


def sales_invoice_created_hook(event_data):
    """Hook que se ejecuta cuando se crea una factura"""
    invoice_id = event_data.get('sale_id')
    
    print(f"Sales hook: Invoice {invoice_id} created")
    
    # Ejemplo: Enviar factura por email
    # send_invoice_email(invoice_id)
    
    # Ejemplo: Actualizar contabilidad
    # create_accounting_entry(invoice_id)
    
    return f"Invoice hook processed for {invoice_id}"


# ============================================================================
# EJEMPLOS DE HOOKS PARA MÓDULO DE COMPRAS
# ============================================================================

def purchase_order_created_hook(event_data):
    """Hook que se ejecuta cuando se crea una orden de compra"""
    purchase_id = event_data.get('purchase_id')
    
    print(f"Purchase hook: Order {purchase_id} created")
    
    # Ejemplo: Enviar solicitud de cotización
    # send_quote_request(purchase_id)
    
    # Ejemplo: Notificar aprobadores
    # notify_approvers(purchase_id)
    
    return f"Purchase hook processed for order {purchase_id}"


def purchase_receipt_created_hook(event_data):
    """Hook que se ejecuta cuando se crea un recibo de compra"""
    receipt_id = event_data.get('purchase_id')
    
    print(f"Purchase hook: Receipt {receipt_id} created")
    
    # Ejemplo: Actualizar inventario
    # update_inventory_from_receipt(receipt_id)
    
    # Ejemplo: Crear entrada contable
    # create_accounting_entry(receipt_id)
    
    return f"Receipt hook processed for {receipt_id}"


# ============================================================================
# EJEMPLOS DE HOOKS PARA MÓDULO DE INVENTARIO
# ============================================================================

def inventory_stock_movement_hook(event_data):
    """Hook que se ejecuta cuando hay movimiento de inventario"""
    product_id = event_data.get('product_id')
    quantity = event_data.get('quantity', 0)
    action = event_data.get('action', '')
    
    print(f"Inventory hook: Stock movement - Product {product_id}, {action} {quantity}")
    
    # Ejemplo: Verificar stock mínimo
    # check_minimum_stock(product_id)
    
    # Ejemplo: Actualizar costos promedio
    # update_average_cost(product_id)
    
    return f"Stock movement processed for product {product_id}"


def inventory_low_stock_hook(event_data):
    """Hook que se ejecuta cuando el stock está bajo"""
    product_id = event_data.get('product_id')
    current_stock = event_data.get('details', {}).get('current_stock', 0)
    
    print(f"Inventory hook: Low stock alert - Product {product_id}, Stock: {current_stock}")
    
    # Ejemplo: Enviar alerta a compras
    # send_purchase_alert(product_id, current_stock)
    
    # Ejemplo: Crear orden de compra automática
    # create_auto_purchase_order(product_id)
    
    return f"Low stock alert processed for product {product_id}"


# ============================================================================
# EJEMPLOS DE HOOKS PARA MÓDULO DE CONTABILIDAD
# ============================================================================

def accounting_journal_entry_hook(event_data):
    """Hook que se ejecuta cuando se crea una entrada contable"""
    entry_id = event_data.get('journal_entry_id')
    
    print(f"Accounting hook: Journal entry {entry_id} created")
    
    # Ejemplo: Validar balance
    # validate_accounting_balance(entry_id)
    
    # Ejemplo: Generar reportes
    # generate_financial_reports()
    
    return f"Journal entry hook processed for {entry_id}"


def accounting_tax_calculated_hook(event_data):
    """Hook que se ejecuta cuando se calculan impuestos"""
    tax_data = event_data.get('details', {})
    amount = tax_data.get('amount', 0)
    tax_type = tax_data.get('tax_type', '')
    
    print(f"Accounting hook: Tax calculated - {tax_type}: ${amount}")
    
    # Ejemplo: Validar cálculo de impuestos
    # validate_tax_calculation(tax_data)
    
    # Ejemplo: Actualizar reportes fiscales
    # update_tax_reports(tax_data)
    
    return f"Tax calculation processed for {tax_type}"


# ============================================================================
# EJEMPLOS DE HOOKS PARA MÓDULO DE USUARIOS
# ============================================================================

def user_created_hook(event_data):
    """Hook que se ejecuta cuando se crea un usuario"""
    user_id = event_data.get('user_id')
    
    print(f"User hook: User {user_id} created")
    
    # Ejemplo: Enviar email de bienvenida
    # send_welcome_email(user_id)
    
    # Ejemplo: Asignar permisos por defecto
    # assign_default_permissions(user_id)
    
    return f"User creation hook processed for {user_id}"


def user_login_hook(event_data):
    """Hook que se ejecuta cuando un usuario inicia sesión"""
    user_id = event_data.get('user_id')
    
    print(f"User hook: User {user_id} logged in")
    
    # Ejemplo: Registrar actividad
    # log_user_activity(user_id, 'login')
    
    # Ejemplo: Actualizar última sesión
    # update_last_login(user_id)
    
    return f"User login hook processed for {user_id}"


# ============================================================================
# EJEMPLOS DE HOOKS PARA MÓDULO DE EMPRESAS
# ============================================================================

def company_created_hook(event_data):
    """Hook que se ejecuta cuando se crea una empresa"""
    company_id = event_data.get('company_id')
    
    print(f"Company hook: Company {company_id} created")
    
    # Ejemplo: Crear configuración por defecto
    # create_default_company_config(company_id)
    
    # Ejemplo: Asignar administrador
    # assign_company_admin(company_id)
    
    return f"Company creation hook processed for {company_id}"


def branch_created_hook(event_data):
    """Hook que se ejecuta cuando se crea una sucursal"""
    branch_id = event_data.get('branch_id')
    company_id = event_data.get('company_id')
    
    print(f"Company hook: Branch {branch_id} created for company {company_id}")
    
    # Ejemplo: Crear inventario inicial
    # create_initial_inventory(branch_id)
    
    # Ejemplo: Configurar ubicaciones
    # setup_branch_locations(branch_id)
    
    return f"Branch creation hook processed for {branch_id}"


# ============================================================================
# FUNCIÓN PARA REGISTRAR TODOS LOS EJEMPLOS
# ============================================================================

def register_hook_examples():
    """Registra todos los ejemplos de hooks"""
    
    # Hooks de Ventas
    hook_manager.register_hook('event_sale.created', sales_order_created_hook, 'sales', 10)
    hook_manager.register_hook('event_payment.received', sales_payment_received_hook, 'sales', 10)
    hook_manager.register_hook('event_invoice.created', sales_invoice_created_hook, 'sales', 10)
    
    # Hooks de Compras
    hook_manager.register_hook('event_purchase.created', purchase_order_created_hook, 'purchases', 10)
    hook_manager.register_hook('event_receipt.created', purchase_receipt_created_hook, 'purchases', 10)
    
    # Hooks de Inventario
    hook_manager.register_hook('event_stock.movement', inventory_stock_movement_hook, 'inventory', 10)
    hook_manager.register_hook('event_stock.low', inventory_low_stock_hook, 'inventory', 10)
    
    # Hooks de Contabilidad
    hook_manager.register_hook('event_journal_entry.created', accounting_journal_entry_hook, 'accounting', 10)
    hook_manager.register_hook('event_tax.calculated', accounting_tax_calculated_hook, 'accounting', 10)
    
    # Hooks de Usuarios
    hook_manager.register_hook('event_user.created', user_created_hook, 'core', 10)
    hook_manager.register_hook('event_user.login', user_login_hook, 'core', 10)
    
    # Hooks de Empresas
    hook_manager.register_hook('event_company.created', company_created_hook, 'core', 10)
    hook_manager.register_hook('event_branch.created', branch_created_hook, 'core', 10)
    
    print("Hook examples registered successfully")


def unregister_hook_examples():
    """Desregistra todos los ejemplos de hooks"""
    
    # Lista de hooks a desregistrar
    hooks_to_remove = [
        ('event_sale.created', sales_order_created_hook),
        ('event_payment.received', sales_payment_received_hook),
        ('event_invoice.created', sales_invoice_created_hook),
        ('event_purchase.created', purchase_order_created_hook),
        ('event_receipt.created', purchase_receipt_created_hook),
        ('event_stock.movement', inventory_stock_movement_hook),
        ('event_stock.low', inventory_low_stock_hook),
        ('event_journal_entry.created', accounting_journal_entry_hook),
        ('event_tax.calculated', accounting_tax_calculated_hook),
        ('event_user.created', user_created_hook),
        ('event_user.login', user_login_hook),
        ('event_company.created', company_created_hook),
        ('event_branch.created', branch_created_hook),
    ]
    
    for hook_name, callback in hooks_to_remove:
        hook_manager.unregister_hook(hook_name, callback)
    
    print("Hook examples unregistered successfully")


# ============================================================================
# EJEMPLOS DE USO DE EVENT DISPATCHER
# ============================================================================

def demonstrate_event_dispatching():
    """Demuestra el uso del event dispatcher"""
    
    # Ejemplo: Crear una orden de venta
    sale_data = EventDataBuilder.sale_event(
        sale_id=12345,
        action='created',
        details={
            'customer_id': 67890,
            'total_amount': 1500.00,
            'items_count': 3
        }
    )
    
    event_dispatcher.dispatch_event(
        ModuleEvents.SALE_CREATED,
        sale_data,
        source_module='sales',
        priority=EventPriority.HIGH.value
    )
    
    # Ejemplo: Recibir un pago
    payment_data = EventDataBuilder.sale_event(
        sale_id=12345,
        action='payment_received',
        details={
            'payment_method': 'credit_card',
            'amount': 1500.00,
            'transaction_id': 'TXN123456'
        }
    )
    
    event_dispatcher.dispatch_event(
        ModuleEvents.PAYMENT_RECEIVED,
        payment_data,
        source_module='sales',
        priority=EventPriority.NORMAL.value
    )
    
    print("Event dispatching demonstration completed")


if __name__ == "__main__":
    # Registrar ejemplos
    register_hook_examples()
    
    # Demostrar event dispatching
    demonstrate_event_dispatching() 