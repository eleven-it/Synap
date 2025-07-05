from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from typing import List, Dict, Optional

from .models import SalesOrder, SalesOrderLine, SalesOrderStates, Invoice, InvoiceLine
from inventory.models import (
    StockMove, StockQuant, StockReservation, Location, 
    Product, ProductVariant, Warehouse
)
from core.models import Empresa, Branch
from accounting.services import TaxCalculationService


class SalesInventoryService:
    """Servicio para integración entre ventas e inventario"""
    
    @staticmethod
    def validate_stock_availability(sales_order: SalesOrder) -> Dict[str, List[str]]:
        """
        Validar disponibilidad de stock para un pedido
        Retorna: {'errors': [], 'warnings': []}
        """
        errors = []
        warnings = []
        
        for line in sales_order.lines.all():
            product = line.product_variant.product
            
            # Obtener stock disponible en la sucursal del pedido
            stock_quants = StockQuant.objects.filter(
                product=product,
                location__branch=sales_order.branch,
                location__warehouse__isnull=False  # Solo ubicaciones de almacén
            )
            
            total_available = sum(quant.available_quantity for quant in stock_quants)
            
            if total_available < line.quantity:
                errors.append(
                    f"Producto {product.sku}: Stock insuficiente. "
                    f"Disponible: {total_available}, Solicitado: {line.quantity}"
                )
            elif total_available < line.quantity * Decimal('1.2'):  # 20% de margen
                warnings.append(
                    f"Producto {product.sku}: Stock bajo. "
                    f"Disponible: {total_available}, Solicitado: {line.quantity}"
                )
        
        return {'errors': errors, 'warnings': warnings}
    
    @staticmethod
    def reserve_stock_for_order(sales_order: SalesOrder, user) -> List[StockReservation]:
        """
        Reservar stock para un pedido confirmado
        """
        reservations = []
        
        with transaction.atomic():
            for line in sales_order.lines.all():
                product = line.product_variant.product
                
                # Buscar ubicaciones con stock disponible
                stock_quants = list(StockQuant.objects.filter(
                    product=product,
                    location__branch=sales_order.branch,
                    location__warehouse__isnull=False
                ))
                # Ordenar en Python por available_quantity descendente
                stock_quants.sort(key=lambda q: q.available_quantity, reverse=True)
                
                remaining_quantity = line.quantity
                
                for quant in stock_quants:
                    if remaining_quantity <= 0:
                        break
                    
                    available = quant.available_quantity
                    if available <= 0:
                        continue
                    
                    # Calcular cantidad a reservar
                    reserve_qty = min(remaining_quantity, available)
                    
                    # Crear reserva
                    reservation = StockReservation.objects.create(
                        empresa=sales_order.branch.empresa,
                        branch=sales_order.branch,
                        product=product,
                        location=quant.location,
                        quantity=reserve_qty,
                        reserved_for=f"SO-{sales_order.number}",
                        status='active'
                    )
                    reservations.append(reservation)
                    
                    # Actualizar cantidad reservada en StockQuant
                    quant.reserved_quantity += reserve_qty
                    quant.save()
                    
                    remaining_quantity -= reserve_qty
                
                if remaining_quantity > 0:
                    raise ValidationError(
                        f"Stock insuficiente para producto {product.sku}. "
                        f"Faltan {remaining_quantity} unidades"
                    )
        
        return reservations
    
    @staticmethod
    def release_stock_reservations(sales_order: SalesOrder, user) -> int:
        """
        Liberar reservas de stock para un pedido cancelado
        """
        released_count = 0
        
        with transaction.atomic():
            reservations = StockReservation.objects.filter(
                reserved_for=f"SO-{sales_order.number}",
                status='active'
            )
            
            for reservation in reservations:
                # Actualizar StockQuant
                try:
                    quant = StockQuant.objects.get(
                        product=reservation.product,
                        location=reservation.location
                    )
                    quant.reserved_quantity -= reservation.quantity
                    quant.save()
                    
                    # Marcar reserva como cancelada
                    reservation.status = 'cancelled'
                    reservation.save()
                    
                    released_count += 1
                except StockQuant.DoesNotExist:
                    # Si no existe el quant, solo cancelar la reserva
                    reservation.status = 'cancelled'
                    reservation.save()
        
        return released_count
    
    @staticmethod
    def create_stock_moves_for_delivery(sales_order: SalesOrder, user) -> List[StockMove]:
        """
        Crear movimientos de stock para la entrega de un pedido
        """
        stock_moves = []
        
        with transaction.atomic():
            # Obtener ubicación de cliente (o crear si no existe)
            customer_location, created = Location.objects.get_or_create(
                empresa=sales_order.branch.empresa,
                branch=sales_order.branch,
                name=f"Cliente: {sales_order.client.name}",
                location_type='customer',
                defaults={
                    'is_active': True,
                    'allow_operations': True
                }
            )
            
            for line in sales_order.lines.all():
                product = line.product_variant.product
                
                # Obtener reservas activas para esta línea
                reservations = StockReservation.objects.filter(
                    reserved_for=f"SO-{sales_order.number}",
                    product=product,
                    status='active'
                )
                
                remaining_quantity = line.quantity
                
                for reservation in reservations:
                    if remaining_quantity <= 0:
                        break
                    
                    # Calcular cantidad a mover
                    move_qty = min(remaining_quantity, reservation.quantity)
                    
                    # Crear movimiento de stock
                    stock_move = StockMove.objects.create(
                        empresa=sales_order.branch.empresa,
                        branch=sales_order.branch,
                        product=product,
                        quantity=move_qty,
                        from_location=reservation.location,
                        to_location=customer_location,
                        move_type='outgoing',
                        reference=f"SO-{sales_order.number}",
                        origin='sales_delivery',
                        state='confirmed',
                        created_by=user
                    )
                    stock_moves.append(stock_move)
                    
                    # Marcar reserva como usada
                    reservation.status = 'used'
                    reservation.save()
                    
                    # Actualizar StockQuant
                    quant = StockQuant.objects.get(
                        product=product,
                        location=reservation.location
                    )
                    quant.quantity -= move_qty
                    quant.reserved_quantity -= move_qty
                    quant.save()
                    
                    remaining_quantity -= move_qty
                
                if remaining_quantity > 0:
                    raise ValidationError(
                        f"Error al procesar entrega: faltan {remaining_quantity} "
                        f"unidades del producto {product.sku}"
                    )
        
        return stock_moves
    
    @staticmethod
    def process_return_delivery(return_delivery, user) -> List[StockMove]:
        """
        Procesar devolución y crear movimientos de stock de retorno
        """
        stock_moves = []
        
        with transaction.atomic():
            # Obtener ubicación de almacén para retorno
            warehouse_location = Location.objects.filter(
                empresa=return_delivery.warehouse.empresa,
                branch=return_delivery.warehouse.branch,
                warehouse=return_delivery.warehouse,
                location_type='internal'
            ).first()
            
            if not warehouse_location:
                raise ValidationError("No se encontró ubicación de almacén para retorno")
            
            for line in return_delivery.lines.all():
                product = line.product_variant.product
                
                # Crear movimiento de stock de retorno
                stock_move = StockMove.objects.create(
                    empresa=return_delivery.warehouse.empresa,
                    branch=return_delivery.warehouse.branch,
                    product=product,
                    quantity=line.quantity,
                    from_location=warehouse_location,  # Desde cliente (ubicación temporal)
                    to_location=warehouse_location,    # Hacia almacén
                    move_type='incoming',
                    reference=f"RD-{return_delivery.number}",
                    origin='sales_return',
                    state='confirmed',
                    created_by=user
                )
                stock_moves.append(stock_move)
                
                # Actualizar StockQuant
                quant, created = StockQuant.objects.get_or_create(
                    product=product,
                    location=warehouse_location,
                    defaults={'quantity': 0, 'reserved_quantity': 0}
                )
                quant.quantity += line.quantity
                quant.save()
        
        return stock_moves


class SalesInventoryValidator:
    """Validador para integración sales-inventory"""
    
    @staticmethod
    def can_confirm_order(sales_order: SalesOrder) -> bool:
        """Verificar si se puede confirmar el pedido"""
        validation = SalesInventoryService.validate_stock_availability(sales_order)
        return len(validation['errors']) == 0
    
    @staticmethod
    def can_deliver_order(sales_order: SalesOrder) -> bool:
        """Verificar si se puede entregar el pedido"""
        # Verificar que tenga reservas activas
        active_reservations = StockReservation.objects.filter(
            reserved_for=f"SO-{sales_order.number}",
            status='active'
        )
        return active_reservations.exists()
    
    @staticmethod
    def get_stock_summary(sales_order: SalesOrder) -> Dict:
        """Obtener resumen de stock para el pedido"""
        summary = {
            'order_number': sales_order.number,
            'lines': [],
            'total_available': 0,
            'total_reserved': 0,
            'can_confirm': True,
            'can_deliver': True
        }
        
        for line in sales_order.lines.all():
            product = line.product_variant.product
            
            # Obtener stock disponible
            stock_quants = StockQuant.objects.filter(
                product=product,
                location__branch=sales_order.branch,
                location__warehouse__isnull=False
            )
            
            available = sum(quant.available_quantity for quant in stock_quants)
            reserved = sum(quant.reserved_quantity for quant in stock_quants)
            
            line_summary = {
                'product_sku': product.sku,
                'product_name': product.name,
                'requested_quantity': line.quantity,
                'available_quantity': available,
                'reserved_quantity': reserved,
                'has_stock': available >= line.quantity,
                'stock_status': 'sufficient' if available >= line.quantity else 'insufficient'
            }
            
            summary['lines'].append(line_summary)
            summary['total_available'] += available
            summary['total_reserved'] += reserved
            
            if not line_summary['has_stock']:
                summary['can_confirm'] = False
        
        # Verificar si se puede entregar
        summary['can_deliver'] = SalesInventoryValidator.can_deliver_order(sales_order)
        
        return summary 


class SalesTaxService:
    """Servicio para integración de impuestos en ventas"""
    
    def __init__(self, empresa):
        self.empresa = empresa
    
    def calculate_order_taxes(self, order):
        """Calcular impuestos para un pedido completo"""
        tax_service = TaxCalculationService(
            empresa=self.empresa,
            partner=order.client
        )
        
        total_tax_amount = Decimal('0')
        all_tax_lines = []
        
        # Calcular impuestos por línea
        for line in order.lines.all():
            tax_result = tax_service.calculate_line_taxes(line, save_tax_lines=True)
            total_tax_amount += tax_result['total_tax_amount']
            all_tax_lines.extend(tax_result['tax_lines'])
            
            # Actualizar línea con totales
            line.tax_amount = tax_result['total_tax_amount']
            line.save(update_fields=['tax_amount'])
        
        # Actualizar totales del pedido
        order.total_tax = total_tax_amount
        order.save(update_fields=['total_tax'])
        
        return {
            'total_tax_amount': total_tax_amount,
            'tax_lines': all_tax_lines
        }
    
    def calculate_invoice_taxes(self, invoice):
        """Calcular impuestos para una factura"""
        tax_service = TaxCalculationService(
            empresa=self.empresa,
            partner=invoice.client
        )
        
        total_tax_amount = Decimal('0')
        all_tax_lines = []
        
        # Calcular impuestos por línea
        for line in invoice.lines.all():
            tax_result = tax_service.calculate_line_taxes(line, save_tax_lines=True)
            total_tax_amount += tax_result['total_tax_amount']
            all_tax_lines.extend(tax_result['tax_lines'])
        
        # Actualizar totales de la factura
        invoice.total_tax = total_tax_amount
        invoice.save(update_fields=['total_tax'])
        
        return {
            'total_tax_amount': total_tax_amount,
            'tax_lines': all_tax_lines
        }
    
    def create_invoice_from_order(self, order, user):
        """Crear factura desde pedido con impuestos"""
        from accounting.models import JournalEntry, JournalEntryLine
        
        # Crear factura
        invoice = Invoice.objects.create(
            client=order.client,
            sales_order=order,
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            payment_term=order.payment_term,
            currency=order.currency,
            notes=f'Factura generada desde pedido {order.number}',
            status='draft'
        )
        
        # Crear líneas de factura
        for line in order.lines.all():
            invoice_line = InvoiceLine.objects.create(
                invoice=invoice,
                product_variant=line.product_variant,
                quantity=line.quantity,
                unit_price=line.unit_price,
                discount=line.discount,
                subtotal=line.subtotal,
                description=line.description
            )
        
        # Calcular impuestos
        tax_result = self.calculate_invoice_taxes(invoice)
        
        # Crear asiento contable
        self._create_accounting_entry(invoice, tax_result['tax_lines'], user)
        
        return invoice
    
    def _create_accounting_entry(self, invoice, tax_lines, user):
        """Crear asiento contable para la factura"""
        from accounting.models import JournalEntry, JournalEntryLine, Journal
        
        # Obtener diario de ventas
        journal = Journal.objects.filter(
            empresa=invoice.client.empresa,
            journal_type='sale',
            is_active=True
        ).first()
        
        if not journal:
            return
        
        # Crear asiento
        entry = JournalEntry.objects.create(
            empresa=invoice.client.empresa,
            journal=journal,
            number=f"INV-{invoice.number}",
            date=invoice.invoice_date,
            reference=f"Factura {invoice.number}",
            narration=f"Facturación de venta {invoice.number}",
            state='draft',
            created_by=user,
            origin_model='sales.Invoice',
            origin_id=invoice.id
        )
        
        # Línea de cuenta por cobrar
        JournalEntryLine.objects.create(
            entry=entry,
            account=journal.default_account,
            partner=invoice.client,
            debit=invoice.total,
            name=f"Cuenta por cobrar - {invoice.client.name}"
        )
        
        # Línea de ingresos
        revenue_account = journal.default_account  # Ajustar según configuración
        JournalEntryLine.objects.create(
            entry=entry,
            account=revenue_account,
            credit=invoice.total - sum(tl.tax_amount for tl in tax_lines),
            name=f"Ingresos por venta - {invoice.number}"
        )
        
        # Líneas de impuestos
        for tax_line in tax_lines:
            JournalEntryLine.objects.create(
                entry=entry,
                account=tax_line.tax.account_id,
                credit=tax_line.tax_amount,
                name=f"{tax_line.tax.name} - {invoice.number}",
                tax_line=tax_line
            )
        
        # Publicar asiento
        entry.post(user)


class SalesValidationService:
    """Servicio para validación de ventas"""
    
    def __init__(self, empresa):
        self.empresa = empresa
    
    def validate_order_taxes(self, order):
        """Validar impuestos de un pedido"""
        errors = []
        warnings = []
        
        # Verificar que todas las líneas tengan impuestos calculados
        for line in order.lines.all():
            if line.tax_amount == 0 and line.subtotal > 0:
                warnings.append(f"Línea {line.id} no tiene impuestos calculados")
        
        # Verificar consistencia de totales
        calculated_total = sum(line.subtotal + line.tax_amount for line in order.lines.all())
        if abs(calculated_total - order.total) > Decimal('0.01'):
            errors.append(f"Total del pedido ({order.total}) no coincide con cálculo ({calculated_total})")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }
    
    def validate_invoice_taxes(self, invoice):
        """Validar impuestos de una factura"""
        errors = []
        warnings = []
        
        # Verificar que todas las líneas tengan impuestos calculados
        for line in invoice.lines.all():
            if line.tax_amount == 0 and line.subtotal > 0:
                warnings.append(f"Línea {line.id} no tiene impuestos calculados")
        
        # Verificar consistencia con pedido original
        if invoice.sales_order:
            order_total = invoice.sales_order.total
            if abs(invoice.total - order_total) > Decimal('0.01'):
                warnings.append(f"Total de factura ({invoice.total}) difiere del pedido ({order_total})")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        } 