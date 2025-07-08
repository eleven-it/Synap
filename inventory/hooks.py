"""
Configuración de hooks para el módulo de inventario
"""

from core.module_events import ModuleEvents, EventDataBuilder


def on_product_created(event_data):
    """Hook que se ejecuta cuando se crea un producto"""
    product_id = event_data.get('product_id')
    details = event_data.get('details', {})
    
    # Crear ubicaciones por defecto
    create_default_locations(product_id, details)
    
    # Crear entrada contable para producto
    create_product_accounting_entry(product_id, details)
    
    # Asignar código de barras si no existe
    assign_barcode_if_needed(product_id, details)
    
    return f"Product {product_id} created successfully"


def on_product_updated(event_data):
    """Hook que se ejecuta cuando se actualiza un producto"""
    product_id = event_data.get('product_id')
    details = event_data.get('details', {})
    
    # Actualizar entrada contable si cambió el costo
    if details.get('cost_changed'):
        update_product_accounting_entry(product_id, details)
    
    # Actualizar ubicaciones si cambió la categoría
    if details.get('category_changed'):
        update_product_locations(product_id, details)
    
    return f"Product {product_id} updated successfully"


def on_stock_movement(event_data):
    """Hook que se ejecuta cuando hay movimiento de inventario"""
    product_id = event_data.get('product_id')
    quantity = event_data.get('quantity', 0)
    action = event_data.get('action', '')
    details = event_data.get('details', {})
    
    # Actualizar stock disponible
    update_available_stock(product_id, quantity, action)
    
    # Actualizar costos promedio si es entrada
    if action == 'in':
        update_average_cost(product_id, quantity, details.get('unit_cost', 0))
    
    # Crear entrada contable para movimiento
    create_stock_movement_accounting_entry(product_id, quantity, action, details)
    
    # Verificar stock mínimo
    check_minimum_stock(product_id)
    
    return f"Stock movement processed for product {product_id}: {action} {quantity}"


def on_stock_low(event_data):
    """Hook que se ejecuta cuando el stock está bajo"""
    product_id = event_data.get('product_id')
    details = event_data.get('details', {})
    current_stock = details.get('current_stock', 0)
    minimum_stock = details.get('minimum_stock', 0)
    
    # Enviar alerta a compras
    send_purchase_alert(product_id, current_stock, minimum_stock)
    
    # Crear orden de compra automática si está configurado
    if details.get('auto_purchase', False):
        create_auto_purchase_order(product_id, current_stock, minimum_stock)
    
    # Notificar al administrador
    notify_stock_alert(product_id, current_stock, minimum_stock)
    
    return f"Low stock alert processed for product {product_id}"


def on_stock_out(event_data):
    """Hook que se ejecuta cuando el stock se agota"""
    product_id = event_data.get('product_id')
    details = event_data.get('details', {})
    
    # Pausar ventas del producto
    pause_product_sales(product_id)
    
    # Crear orden de compra urgente
    create_urgent_purchase_order(product_id, details)
    
    # Notificar a todos los stakeholders
    notify_stock_out(product_id, details)
    
    return f"Stock out alert processed for product {product_id}"


def on_warehouse_created(event_data):
    """Hook que se ejecuta cuando se crea un almacén"""
    warehouse_id = event_data.get('warehouse_id')
    details = event_data.get('details', {})
    
    # Crear ubicaciones por defecto
    create_default_warehouse_locations(warehouse_id, details)
    
    # Crear entrada contable para almacén
    create_warehouse_accounting_entry(warehouse_id, details)
    
    # Asignar administrador si se especifica
    if details.get('manager_id'):
        assign_warehouse_manager(warehouse_id, details.get('manager_id'))
    
    return f"Warehouse {warehouse_id} created successfully"


def on_location_created(event_data):
    """Hook que se ejecuta cuando se crea una ubicación"""
    location_id = event_data.get('location_id')
    details = event_data.get('details', {})
    
    # Validar ubicación única
    validate_unique_location(location_id, details)
    
    # Crear entrada contable para ubicación
    create_location_accounting_entry(location_id, details)
    
    # Asignar productos si se especifica
    if details.get('product_ids'):
        assign_products_to_location(location_id, details.get('product_ids'))
    
    return f"Location {location_id} created successfully"


def on_inventory_count(event_data):
    """Hook que se ejecuta cuando se realiza un conteo de inventario"""
    count_id = event_data.get('count_id')
    details = event_data.get('details', {})
    
    # Calcular diferencias
    calculate_inventory_differences(count_id, details)
    
    # Crear ajustes automáticos si están habilitados
    if details.get('auto_adjust', False):
        create_auto_adjustments(count_id, details)
    
    # Crear entrada contable para ajustes
    create_inventory_adjustment_accounting_entry(count_id, details)
    
    # Generar reporte de conteo
    generate_inventory_count_report(count_id, details)
    
    return f"Inventory count {count_id} processed successfully"


# Funciones auxiliares (simuladas)
def create_default_locations(product_id, details):
    """Crea ubicaciones por defecto para un producto"""
    print(f"Creating default locations for product {product_id}")
    # Aquí iría la lógica real de creación de ubicaciones


def create_product_accounting_entry(product_id, details):
    """Crea entrada contable para producto"""
    print(f"Creating accounting entry for product {product_id}")
    # Aquí iría la lógica real de creación de entrada contable


def assign_barcode_if_needed(product_id, details):
    """Asigna código de barras si no existe"""
    if not details.get('barcode'):
        print(f"Assigning barcode for product {product_id}")
    # Aquí iría la lógica real de asignación de código de barras


def update_product_accounting_entry(product_id, details):
    """Actualiza entrada contable de producto"""
    print(f"Updating accounting entry for product {product_id}")
    # Aquí iría la lógica real de actualización de entrada contable


def update_product_locations(product_id, details):
    """Actualiza ubicaciones de producto"""
    print(f"Updating locations for product {product_id}")
    # Aquí iría la lógica real de actualización de ubicaciones


def update_available_stock(product_id, quantity, action):
    """Actualiza stock disponible"""
    print(f"Updating available stock for product {product_id}: {action} {quantity}")
    # Aquí iría la lógica real de actualización de stock


def update_average_cost(product_id, quantity, unit_cost):
    """Actualiza costo promedio"""
    print(f"Updating average cost for product {product_id}: {quantity} units at ${unit_cost}")
    # Aquí iría la lógica real de actualización de costo promedio


def create_stock_movement_accounting_entry(product_id, quantity, action, details):
    """Crea entrada contable para movimiento de stock"""
    print(f"Creating stock movement accounting entry for product {product_id}")
    # Aquí iría la lógica real de creación de entrada contable


def check_minimum_stock(product_id):
    """Verifica stock mínimo"""
    print(f"Checking minimum stock for product {product_id}")
    # Aquí iría la lógica real de verificación de stock mínimo


def send_purchase_alert(product_id, current_stock, minimum_stock):
    """Envía alerta de compra"""
    print(f"Sending purchase alert for product {product_id}: {current_stock}/{minimum_stock}")
    # Aquí iría la lógica real de envío de alerta


def create_auto_purchase_order(product_id, current_stock, minimum_stock):
    """Crea orden de compra automática"""
    print(f"Creating auto purchase order for product {product_id}")
    # Aquí iría la lógica real de creación de orden de compra


def notify_stock_alert(product_id, current_stock, minimum_stock):
    """Notifica alerta de stock"""
    print(f"Notifying stock alert for product {product_id}: {current_stock}/{minimum_stock}")
    # Aquí iría la lógica real de notificación


def pause_product_sales(product_id):
    """Pausa ventas del producto"""
    print(f"Pausing sales for product {product_id}")
    # Aquí iría la lógica real de pausa de ventas


def create_urgent_purchase_order(product_id, details):
    """Crea orden de compra urgente"""
    print(f"Creating urgent purchase order for product {product_id}")
    # Aquí iría la lógica real de creación de orden urgente


def notify_stock_out(product_id, details):
    """Notifica agotamiento de stock"""
    print(f"Notifying stock out for product {product_id}")
    # Aquí iría la lógica real de notificación


def create_default_warehouse_locations(warehouse_id, details):
    """Crea ubicaciones por defecto para almacén"""
    print(f"Creating default locations for warehouse {warehouse_id}")
    # Aquí iría la lógica real de creación de ubicaciones


def create_warehouse_accounting_entry(warehouse_id, details):
    """Crea entrada contable para almacén"""
    print(f"Creating accounting entry for warehouse {warehouse_id}")
    # Aquí iría la lógica real de creación de entrada contable


def assign_warehouse_manager(warehouse_id, manager_id):
    """Asigna administrador al almacén"""
    print(f"Assigning manager {manager_id} to warehouse {warehouse_id}")
    # Aquí iría la lógica real de asignación de administrador


def validate_unique_location(location_id, details):
    """Valida ubicación única"""
    print(f"Validating unique location {location_id}")
    # Aquí iría la lógica real de validación


def create_location_accounting_entry(location_id, details):
    """Crea entrada contable para ubicación"""
    print(f"Creating accounting entry for location {location_id}")
    # Aquí iría la lógica real de creación de entrada contable


def assign_products_to_location(location_id, product_ids):
    """Asigna productos a ubicación"""
    print(f"Assigning products {product_ids} to location {location_id}")
    # Aquí iría la lógica real de asignación


def calculate_inventory_differences(count_id, details):
    """Calcula diferencias de inventario"""
    print(f"Calculating inventory differences for count {count_id}")
    # Aquí iría la lógica real de cálculo de diferencias


def create_auto_adjustments(count_id, details):
    """Crea ajustes automáticos"""
    print(f"Creating auto adjustments for count {count_id}")
    # Aquí iría la lógica real de creación de ajustes


def create_inventory_adjustment_accounting_entry(count_id, details):
    """Crea entrada contable para ajuste de inventario"""
    print(f"Creating inventory adjustment accounting entry for count {count_id}")
    # Aquí iría la lógica real de creación de entrada contable


def generate_inventory_count_report(count_id, details):
    """Genera reporte de conteo de inventario"""
    print(f"Generating inventory count report for {count_id}")
    # Aquí iría la lógica real de generación de reporte


# Configuración de hooks
HOOKS = {
    'event_product.created': {
        'callback': on_product_created,
        'description': 'Hook que se ejecuta cuando se crea un producto',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'inventory',
            'type': 'creation'
        }
    },
    'event_product.updated': {
        'callback': on_product_updated,
        'description': 'Hook que se ejecuta cuando se actualiza un producto',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'inventory',
            'type': 'update'
        }
    },
    'event_stock.movement': {
        'callback': on_stock_movement,
        'description': 'Hook que se ejecuta cuando hay movimiento de inventario',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'inventory',
            'type': 'movement'
        }
    },
    'event_stock.low': {
        'callback': on_stock_low,
        'description': 'Hook que se ejecuta cuando el stock está bajo',
        'priority': 10,
        'dependencies': ['purchases'],
        'metadata': {
            'category': 'inventory',
            'type': 'alert'
        }
    },
    'event_stock.out': {
        'callback': on_stock_out,
        'description': 'Hook que se ejecuta cuando el stock se agota',
        'priority': 10,
        'dependencies': ['purchases', 'sales'],
        'metadata': {
            'category': 'inventory',
            'type': 'critical_alert'
        }
    },
    'event_warehouse.created': {
        'callback': on_warehouse_created,
        'description': 'Hook que se ejecuta cuando se crea un almacén',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'inventory',
            'type': 'warehouse_creation'
        }
    },
    'event_location.created': {
        'callback': on_location_created,
        'description': 'Hook que se ejecuta cuando se crea una ubicación',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'inventory',
            'type': 'location_creation'
        }
    },
    'event_inventory.count': {
        'callback': on_inventory_count,
        'description': 'Hook que se ejecuta cuando se realiza un conteo de inventario',
        'priority': 10,
        'dependencies': ['accounting'],
        'metadata': {
            'category': 'inventory',
            'type': 'count'
        }
    }
} 