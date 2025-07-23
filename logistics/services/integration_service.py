import logging
from django.utils import timezone
from django.db import transaction
from logistics.models import DeliveryStop, DeliveryRoute, DeliveryEvent
from logistics.services.notification_service import NotificationService
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class IntegrationService:
    """
    Servicio para integrar el módulo de logística con otros módulos del sistema.
    Maneja reservas de stock, actualización de pedidos, costos y facturación automática.
    """
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def reserve_stock_for_delivery(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Reserva automáticamente el stock necesario para una entrega.
        """
        try:
            with transaction.atomic():
                # Verificar si ya hay stock reservado
                if delivery_stop.stock_reserved:
                    return {
                        'success': True,
                        'message': 'Stock already reserved',
                        'reserved': True
                    }
                
                # Obtener productos de la entrega
                products = self._get_delivery_products(delivery_stop)
                if not products:
                    return {
                        'success': False,
                        'error': 'No products found for delivery'
                    }
                
                # Intentar reservar stock para cada producto
                reserved_items = []
                failed_items = []
                
                for product_data in products:
                    reservation_result = self._reserve_product_stock(
                        product_data['product_id'],
                        product_data['quantity'],
                        delivery_stop
                    )
                    
                    if reservation_result['success']:
                        reserved_items.append(reservation_result)
                    else:
                        failed_items.append(reservation_result)
                
                # Si todos los productos se reservaron exitosamente
                if not failed_items:
                    delivery_stop.stock_reserved = True
                    delivery_stop.stock_reserved_at = timezone.now()
                    delivery_stop.save()
                    
                    # Crear evento de reserva
                    DeliveryEvent.objects.create(
                        stop=delivery_stop,
                        event_type='stock_reserved',
                        description=f'Stock reserved for {len(reserved_items)} products',
                        metadata={'reserved_items': reserved_items}
                    )
                    
                    return {
                        'success': True,
                        'message': f'Stock reserved for {len(reserved_items)} products',
                        'reserved_items': reserved_items,
                        'reserved': True
                    }
                else:
                    # Revertir reservas parciales
                    self._release_partial_reservations(reserved_items)
                    
                    return {
                        'success': False,
                        'error': f'Failed to reserve stock for {len(failed_items)} products',
                        'failed_items': failed_items,
                        'reserved_items': reserved_items
                    }
                    
        except Exception as e:
            logger.error(f"Error reserving stock for delivery: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_order_status(self, delivery_stop: DeliveryStop, new_status: str) -> Dict:
        """
        Actualiza el estado del pedido en el módulo de ventas.
        """
        try:
            # Obtener el pedido asociado
            order = self._get_associated_order(delivery_stop)
            if not order:
                return {
                    'success': False,
                    'error': 'No associated order found'
                }
            
            # Mapear estados de logística a estados de ventas
            status_mapping = {
                'in_progress': 'shipped',
                'delivered': 'delivered',
                'failed': 'failed',
                'returned': 'returned'
            }
            
            sales_status = status_mapping.get(new_status, new_status)
            
            # Actualizar estado en el módulo de ventas
            update_result = self._update_sales_order_status(order, sales_status)
            
            if update_result['success']:
                # Crear evento de actualización
                DeliveryEvent.objects.create(
                    stop=delivery_stop,
                    event_type='order_status_updated',
                    description=f'Order status updated to {sales_status}',
                    metadata={'previous_status': delivery_stop.state, 'new_status': sales_status}
                )
                
                # Notificar cambio de estado
                self._notify_order_status_change(delivery_stop, sales_status)
            
            return update_result
            
        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_logistics_costs(self, delivery_route: DeliveryRoute) -> Dict:
        """
        Calcula los costos logísticos de una ruta de entrega.
        """
        try:
            costs = {
                'fuel_cost': 0.0,
                'driver_cost': 0.0,
                'vehicle_cost': 0.0,
                'toll_cost': 0.0,
                'other_costs': 0.0,
                'total_cost': 0.0
            }
            
            # Calcular costo de combustible
            if delivery_route.vehicle:
                fuel_cost = self._calculate_fuel_cost(delivery_route)
                costs['fuel_cost'] = fuel_cost
            
            # Calcular costo del conductor
            if delivery_route.driver:
                driver_cost = self._calculate_driver_cost(delivery_route)
                costs['driver_cost'] = driver_cost
            
            # Calcular costo del vehículo
            if delivery_route.vehicle:
                vehicle_cost = self._calculate_vehicle_cost(delivery_route)
                costs['vehicle_cost'] = vehicle_cost
            
            # Calcular peajes
            toll_cost = self._calculate_toll_cost(delivery_route)
            costs['toll_cost'] = toll_cost
            
            # Calcular otros costos
            other_costs = self._calculate_other_costs(delivery_route)
            costs['other_costs'] = other_costs
            
            # Calcular total
            costs['total_cost'] = sum([
                costs['fuel_cost'],
                costs['driver_cost'],
                costs['vehicle_cost'],
                costs['toll_cost'],
                costs['other_costs']
            ])
            
            # Guardar costos en la ruta
            delivery_route.logistics_cost = costs['total_cost']
            delivery_route.cost_breakdown = costs
            delivery_route.save()
            
            return {
                'success': True,
                'costs': costs,
                'route_id': delivery_route.id
            }
            
        except Exception as e:
            logger.error(f"Error calculating logistics costs: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_invoice_for_delivery(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Crea automáticamente una factura para una entrega completada.
        """
        try:
            with transaction.atomic():
                # Verificar que la entrega esté completada
                if delivery_stop.state != 'delivered':
                    return {
                        'success': False,
                        'error': 'Delivery must be completed before creating invoice'
                    }
                
                # Verificar si ya existe una factura
                if self._invoice_exists(delivery_stop):
                    return {
                        'success': True,
                        'message': 'Invoice already exists for this delivery',
                        'invoice_exists': True
                    }
                
                # Obtener datos del cliente y productos
                client_data = self._get_client_data(delivery_stop)
                products_data = self._get_delivery_products(delivery_stop)
                
                if not client_data or not products_data:
                    return {
                        'success': False,
                        'error': 'Missing client or product data'
                    }
                
                # Crear factura en el módulo de contabilidad
                invoice_data = {
                    'client_id': client_data['id'],
                    'client_name': client_data['name'],
                    'client_tax_id': client_data.get('tax_id'),
                    'delivery_stop_id': delivery_stop.id,
                    'products': products_data,
                    'subtotal': sum(item['total'] for item in products_data),
                    'tax_rate': client_data.get('tax_rate', 0.21),  # IVA por defecto
                    'delivery_cost': delivery_stop.route.logistics_cost or 0.0,
                    'invoice_date': timezone.now().date(),
                    'due_date': timezone.now().date() + timezone.timedelta(days=30)
                }
                
                # Calcular totales
                subtotal = invoice_data['subtotal']
                tax_amount = subtotal * invoice_data['tax_rate']
                delivery_cost = invoice_data['delivery_cost']
                total = subtotal + tax_amount + delivery_cost
                
                invoice_data['tax_amount'] = tax_amount
                invoice_data['total'] = total
                
                # Crear factura
                invoice_result = self._create_accounting_invoice(invoice_data)
                
                if invoice_result['success']:
                    # Marcar entrega como facturada
                    delivery_stop.invoiced = True
                    delivery_stop.invoice_id = invoice_result['invoice_id']
                    delivery_stop.save()
                    
                    # Crear evento de facturación
                    DeliveryEvent.objects.create(
                        stop=delivery_stop,
                        event_type='invoice_created',
                        description=f'Invoice created: {invoice_result["invoice_number"]}',
                        metadata={'invoice_data': invoice_data}
                    )
                    
                    return {
                        'success': True,
                        'message': 'Invoice created successfully',
                        'invoice_id': invoice_result['invoice_id'],
                        'invoice_number': invoice_result['invoice_number'],
                        'total': total
                    }
                else:
                    return invoice_result
                    
        except Exception as e:
            logger.error(f"Error creating invoice: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_with_inventory(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Sincroniza el estado de la entrega con el inventario.
        """
        try:
            # Obtener productos de la entrega
            products = self._get_delivery_products(delivery_stop)
            
            if not products:
                return {
                    'success': False,
                    'error': 'No products found for delivery'
                }
            
            sync_results = []
            
            for product_data in products:
                if delivery_stop.state == 'delivered':
                    # Reducir stock cuando se entrega
                    sync_result = self._reduce_inventory_stock(
                        product_data['product_id'],
                        product_data['quantity']
                    )
                elif delivery_stop.state == 'returned':
                    # Aumentar stock cuando se devuelve
                    sync_result = self._increase_inventory_stock(
                        product_data['product_id'],
                        product_data['quantity']
                    )
                else:
                    sync_result = {'success': True, 'message': 'No stock adjustment needed'}
                
                sync_results.append({
                    'product_id': product_data['product_id'],
                    'result': sync_result
                })
            
            return {
                'success': True,
                'message': 'Inventory synchronized successfully',
                'sync_results': sync_results
            }
            
        except Exception as e:
            logger.error(f"Error syncing with inventory: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_delivery_products(self, delivery_stop: DeliveryStop) -> List[Dict]:
        """
        Obtiene los productos asociados a una entrega.
        """
        # TODO: Implementar obtención real de productos desde el módulo de ventas
        # Por ahora retorna datos de ejemplo
        return [
            {
                'product_id': 1,
                'name': 'Producto de ejemplo',
                'quantity': 2,
                'unit_price': 100.0,
                'total': 200.0
            }
        ]
    
    def _reserve_product_stock(self, product_id: int, quantity: int, delivery_stop: DeliveryStop) -> Dict:
        """
        Reserva stock para un producto específico.
        """
        # TODO: Implementar reserva real en el módulo de inventario
        # Por ahora simula la reserva
        return {
            'success': True,
            'product_id': product_id,
            'quantity': quantity,
            'reserved_at': timezone.now()
        }
    
    def _release_partial_reservations(self, reserved_items: List[Dict]) -> None:
        """
        Libera reservas parciales en caso de error.
        """
        # TODO: Implementar liberación real de reservas
        for item in reserved_items:
            logger.info(f"Releasing reservation for product {item['product_id']}")
    
    def _get_associated_order(self, delivery_stop: DeliveryStop):
        """
        Obtiene el pedido asociado a una entrega.
        """
        # TODO: Implementar obtención real del pedido desde el módulo de ventas
        return {'id': 1, 'number': 'ORD-001'}
    
    def _update_sales_order_status(self, order, new_status: str) -> Dict:
        """
        Actualiza el estado del pedido en el módulo de ventas.
        """
        # TODO: Implementar actualización real en el módulo de ventas
        return {
            'success': True,
            'order_id': order['id'],
            'new_status': new_status
        }
    
    def _notify_order_status_change(self, delivery_stop: DeliveryStop, new_status: str) -> None:
        """
        Notifica el cambio de estado del pedido.
        """
        # Enviar notificación al cliente
        self.notification_service.send_notification(
            event_type='order_status_changed',
            data={
                'order_id': delivery_stop.id,
                'new_status': new_status,
                'client_name': delivery_stop.client.name if delivery_stop.client else 'Unknown'
            },
            recipients=[delivery_stop.client.email] if delivery_stop.client and delivery_stop.client.email else []
        )
    
    def _calculate_fuel_cost(self, delivery_route: DeliveryRoute) -> float:
        """
        Calcula el costo de combustible para una ruta.
        """
        # TODO: Implementar cálculo real basado en distancia y consumo
        distance = delivery_route.total_distance or 100  # km
        fuel_consumption = 0.1  # L/km
        fuel_price = 1.5  # USD/L
        return distance * fuel_consumption * fuel_price
    
    def _calculate_driver_cost(self, delivery_route: DeliveryRoute) -> float:
        """
        Calcula el costo del conductor para una ruta.
        """
        # TODO: Implementar cálculo real basado en tiempo y salario
        duration = delivery_route.estimated_duration or 8  # horas
        hourly_rate = 15.0  # USD/hora
        return duration * hourly_rate
    
    def _calculate_vehicle_cost(self, delivery_route: DeliveryRoute) -> float:
        """
        Calcula el costo del vehículo para una ruta.
        """
        # TODO: Implementar cálculo real basado en depreciación y mantenimiento
        distance = delivery_route.total_distance or 100  # km
        cost_per_km = 0.5  # USD/km
        return distance * cost_per_km
    
    def _calculate_toll_cost(self, delivery_route: DeliveryRoute) -> float:
        """
        Calcula el costo de peajes para una ruta.
        """
        # TODO: Implementar cálculo real basado en peajes en la ruta
        return 0.0
    
    def _calculate_other_costs(self, delivery_route: DeliveryRoute) -> float:
        """
        Calcula otros costos logísticos.
        """
        # TODO: Implementar cálculo de otros costos
        return 0.0
    
    def _invoice_exists(self, delivery_stop: DeliveryStop) -> bool:
        """
        Verifica si ya existe una factura para la entrega.
        """
        # TODO: Implementar verificación real en el módulo de contabilidad
        return delivery_stop.invoiced
    
    def _get_client_data(self, delivery_stop: DeliveryStop) -> Dict:
        """
        Obtiene los datos del cliente para la facturación.
        """
        if not delivery_stop.client:
            return None
        
        # TODO: Implementar obtención real de datos del cliente
        return {
            'id': delivery_stop.client.id,
            'name': delivery_stop.client.name,
            'tax_id': getattr(delivery_stop.client, 'tax_id', None),
            'tax_rate': 0.21  # IVA por defecto
        }
    
    def _create_accounting_invoice(self, invoice_data: Dict) -> Dict:
        """
        Crea una factura en el módulo de contabilidad.
        """
        # TODO: Implementar creación real en el módulo de contabilidad
        return {
            'success': True,
            'invoice_id': 1,
            'invoice_number': f'INV-{timezone.now().strftime("%Y%m%d")}-001'
        }
    
    def _reduce_inventory_stock(self, product_id: int, quantity: int) -> Dict:
        """
        Reduce el stock de un producto en inventario.
        """
        # TODO: Implementar reducción real en el módulo de inventario
        return {
            'success': True,
            'product_id': product_id,
            'quantity_reduced': quantity
        }
    
    def _increase_inventory_stock(self, product_id: int, quantity: int) -> Dict:
        """
        Aumenta el stock de un producto en inventario.
        """
        # TODO: Implementar aumento real en el módulo de inventario
        return {
            'success': True,
            'product_id': product_id,
            'quantity_increased': quantity
        } 