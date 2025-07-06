from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class InventoryIntegrationService:
    """Servicio para integrar compras con el módulo de inventario"""
    
    def __init__(self):
        self.inventory_app = 'inventory'
    
    def process_receipt_to_inventory(self, receipt):
        """Procesar recepción y actualizar inventario"""
        try:
            with transaction.atomic():
                # Validar que la recepción esté aprobada
                if receipt.status != 'approved':
                    raise ValidationError(_("Receipt must be approved before updating inventory"))
                
                # Obtener información del producto
                product_variant = receipt.purchase_order_line.product_variant
                quantity = receipt.quantity
                unit_cost = receipt.unit_cost or receipt.purchase_order_line.unit_price
                
                # Actualizar stock
                self._update_stock_level(product_variant, quantity, unit_cost, receipt)
                
                # Actualizar costo promedio
                self._update_average_cost(product_variant, quantity, unit_cost)
                
                # Crear movimiento de inventario
                self._create_inventory_movement(receipt)
                
                # Actualizar estado de la línea de orden
                self._update_order_line_status(receipt.purchase_order_line)
                
                logger.info(f"Inventory updated for receipt {receipt.receipt_number}")
                
        except Exception as e:
            logger.error(f"Error updating inventory for receipt {receipt.receipt_number}: {str(e)}")
            raise
    
    def _update_stock_level(self, product_variant, quantity, unit_cost, receipt):
        """Actualizar nivel de stock del producto"""
        try:
            # Importar modelos de inventario
            from inventory.models import ProductVariant, StockMovement
            
            # Obtener o crear registro de stock
            stock, created = ProductVariant.objects.get_or_create(
                id=product_variant.id,
                defaults={
                    'current_stock': 0,
                    'reserved_stock': 0,
                    'available_stock': 0,
                    'last_updated': timezone.now()
                }
            )
            
            # Actualizar stock
            old_stock = stock.current_stock
            stock.current_stock += quantity
            stock.available_stock += quantity
            stock.last_updated = timezone.now()
            stock.save()
            
            logger.info(f"Stock updated for {product_variant.name}: {old_stock} -> {stock.current_stock}")
            
        except Exception as e:
            logger.error(f"Error updating stock for product {product_variant.name}: {str(e)}")
            raise
    
    def _update_average_cost(self, product_variant, quantity, unit_cost):
        """Actualizar costo promedio del producto"""
        try:
            from inventory.models import ProductVariant
            
            stock = ProductVariant.objects.get(id=product_variant.id)
            
            # Calcular nuevo costo promedio
            current_value = stock.current_stock * stock.average_cost
            new_value = quantity * unit_cost
            total_quantity = stock.current_stock + quantity
            
            if total_quantity > 0:
                new_average_cost = (current_value + new_value) / total_quantity
                stock.average_cost = new_average_cost
                stock.save()
                
                logger.info(f"Average cost updated for {product_variant.name}: {new_average_cost}")
            
        except Exception as e:
            logger.error(f"Error updating average cost for product {product_variant.name}: {str(e)}")
            raise
    
    def _create_inventory_movement(self, receipt):
        """Crear movimiento de inventario"""
        try:
            from inventory.models import StockMovement
            
            movement = StockMovement.objects.create(
                product_variant=receipt.purchase_order_line.product_variant,
                movement_type='purchase_receipt',
                quantity=receipt.quantity,
                unit_cost=receipt.unit_cost or receipt.purchase_order_line.unit_price,
                reference_number=receipt.receipt_number,
                reference_type='purchase_receipt',
                reference_id=receipt.id,
                movement_date=receipt.receipt_date,
                notes=f"Purchase receipt: {receipt.receipt_number}",
                empresa=receipt.empresa,
                sucursal=receipt.sucursal
            )
            
            logger.info(f"Inventory movement created: {movement.id}")
            
        except Exception as e:
            logger.error(f"Error creating inventory movement: {str(e)}")
            raise
    
    def _update_order_line_status(self, order_line):
        """Actualizar estado de la línea de orden"""
        try:
            # Calcular cantidad restante
            total_received = order_line.receipts.filter(status='approved').aggregate(
                total=Sum('quantity')
            )['total'] or 0
            
            remaining = order_line.quantity - total_received
            
            if remaining <= 0:
                order_line.status = 'received'
            elif total_received > 0:
                order_line.status = 'partially_received'
            
            order_line.received_quantity = total_received
            order_line.remaining_quantity = remaining
            order_line.save()
            
            # Verificar si toda la orden está recibida
            self._check_order_completion(order_line.purchase_order)
            
        except Exception as e:
            logger.error(f"Error updating order line status: {str(e)}")
            raise
    
    def _check_order_completion(self, order):
        """Verificar si la orden está completamente recibida"""
        try:
            all_lines_received = all(
                line.status == 'received' 
                for line in order.lines.all()
            )
            
            if all_lines_received and order.status != 'received':
                order.status = 'received'
                order.last_receipt_date = timezone.now().date()
                order.save()
                
                logger.info(f"Order {order.order_number} marked as fully received")
                
        except Exception as e:
            logger.error(f"Error checking order completion: {str(e)}")
            raise
    
    def reserve_stock_for_order(self, order):
        """Reservar stock para una orden de compra"""
        try:
            with transaction.atomic():
                for line in order.lines.all():
                    self._reserve_stock_for_line(line)
                    
        except Exception as e:
            logger.error(f"Error reserving stock for order {order.order_number}: {str(e)}")
            raise
    
    def _reserve_stock_for_line(self, order_line):
        """Reservar stock para una línea de orden"""
        try:
            from inventory.models import ProductVariant
            
            product_variant = order_line.product_variant
            
            # Obtener stock actual
            stock = ProductVariant.objects.get(id=product_variant.id)
            
            # Verificar stock disponible
            if stock.available_stock < order_line.quantity:
                raise ValidationError(
                    _("Insufficient stock for product {product}. Available: {available}, Required: {required}").format(
                        product=product_variant.name,
                        available=stock.available_stock,
                        required=order_line.quantity
                    )
                )
            
            # Reservar stock
            stock.reserved_stock += order_line.quantity
            stock.available_stock -= order_line.quantity
            stock.save()
            
            logger.info(f"Stock reserved for {product_variant.name}: {order_line.quantity}")
            
        except Exception as e:
            logger.error(f"Error reserving stock for line: {str(e)}")
            raise
    
    def release_reserved_stock(self, order):
        """Liberar stock reservado para una orden"""
        try:
            with transaction.atomic():
                for line in order.lines.all():
                    self._release_stock_for_line(line)
                    
        except Exception as e:
            logger.error(f"Error releasing stock for order {order.order_number}: {str(e)}")
            raise
    
    def _release_stock_for_line(self, order_line):
        """Liberar stock reservado para una línea"""
        try:
            from inventory.models import ProductVariant
            
            product_variant = order_line.product_variant
            stock = ProductVariant.objects.get(id=product_variant.id)
            
            # Liberar stock reservado
            stock.reserved_stock -= order_line.quantity
            stock.available_stock += order_line.quantity
            stock.save()
            
            logger.info(f"Stock released for {product_variant.name}: {order_line.quantity}")
            
        except Exception as e:
            logger.error(f"Error releasing stock for line: {str(e)}")
            raise
    
    def get_stock_levels(self, product_variants):
        """Obtener niveles de stock para productos"""
        try:
            from inventory.models import ProductVariant
            
            stock_levels = {}
            
            for variant in product_variants:
                try:
                    stock = ProductVariant.objects.get(id=variant.id)
                    stock_levels[variant.id] = {
                        'current_stock': stock.current_stock,
                        'reserved_stock': stock.reserved_stock,
                        'available_stock': stock.available_stock,
                        'average_cost': stock.average_cost,
                        'last_updated': stock.last_updated
                    }
                except ProductVariant.DoesNotExist:
                    stock_levels[variant.id] = {
                        'current_stock': 0,
                        'reserved_stock': 0,
                        'available_stock': 0,
                        'average_cost': Decimal('0'),
                        'last_updated': None
                    }
            
            return stock_levels
            
        except Exception as e:
            logger.error(f"Error getting stock levels: {str(e)}")
            raise
    
    def check_stock_availability(self, product_variant, quantity):
        """Verificar disponibilidad de stock"""
        try:
            from inventory.models import ProductVariant
            
            stock = ProductVariant.objects.get(id=product_variant.id)
            
            return {
                'available': stock.available_stock >= quantity,
                'current_stock': stock.current_stock,
                'reserved_stock': stock.reserved_stock,
                'available_stock': stock.available_stock,
                'shortage': max(0, quantity - stock.available_stock)
            }
            
        except ProductVariant.DoesNotExist:
            return {
                'available': False,
                'current_stock': 0,
                'reserved_stock': 0,
                'available_stock': 0,
                'shortage': quantity
            }
        except Exception as e:
            logger.error(f"Error checking stock availability: {str(e)}")
            raise
    
    def create_stock_alert(self, product_variant, alert_type='low_stock'):
        """Crear alerta de stock"""
        try:
            from inventory.models import StockAlert
            
            alert = StockAlert.objects.create(
                product_variant=product_variant,
                alert_type=alert_type,
                threshold_value=product_variant.reorder_point or 10,
                current_value=product_variant.current_stock,
                is_active=True,
                created_at=timezone.now(),
                empresa=product_variant.empresa,
                sucursal=product_variant.sucursal
            )
            
            logger.info(f"Stock alert created for {product_variant.name}: {alert_type}")
            return alert
            
        except Exception as e:
            logger.error(f"Error creating stock alert: {str(e)}")
            raise
    
    def process_return_to_inventory(self, receipt, return_quantity, reason):
        """Procesar devolución y actualizar inventario"""
        try:
            with transaction.atomic():
                # Validar cantidad de devolución
                if return_quantity > receipt.quantity:
                    raise ValidationError(_("Return quantity cannot exceed received quantity"))
                
                # Actualizar stock (reducir)
                self._update_stock_level(
                    receipt.purchase_order_line.product_variant,
                    -return_quantity,
                    receipt.unit_cost or receipt.purchase_order_line.unit_price,
                    receipt
                )
                
                # Crear movimiento de devolución
                self._create_return_movement(receipt, return_quantity, reason)
                
                # Actualizar recepción
                receipt.returned_quantity = (receipt.returned_quantity or 0) + return_quantity
                receipt.save()
                
                logger.info(f"Return processed for receipt {receipt.receipt_number}: {return_quantity}")
                
        except Exception as e:
            logger.error(f"Error processing return: {str(e)}")
            raise
    
    def _create_return_movement(self, receipt, quantity, reason):
        """Crear movimiento de devolución"""
        try:
            from inventory.models import StockMovement
            
            movement = StockMovement.objects.create(
                product_variant=receipt.purchase_order_line.product_variant,
                movement_type='purchase_return',
                quantity=-quantity,  # Negativo para devoluciones
                unit_cost=receipt.unit_cost or receipt.purchase_order_line.unit_price,
                reference_number=receipt.receipt_number,
                reference_type='purchase_receipt',
                reference_id=receipt.id,
                movement_date=timezone.now().date(),
                notes=f"Purchase return: {reason}",
                empresa=receipt.empresa,
                sucursal=receipt.sucursal
            )
            
            logger.info(f"Return movement created: {movement.id}")
            
        except Exception as e:
            logger.error(f"Error creating return movement: {str(e)}")
            raise


# Instancia global del servicio
inventory_service = InventoryIntegrationService() 