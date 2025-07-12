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

# --- SERVICIOS PARA PUNTO DE VENTA (TPV) ---

import time
from django.conf import settings
from django.db import models, transaction
from django.utils.translation import gettext as _
from django.apps import apps

class POSService:
    """
    Servicio principal para operaciones de punto de venta
    """
    
    def __init__(self, user, branch, terminal):
        self.user = user
        self.branch = branch
        self.terminal = terminal
        self.current_session = None
    
    def open_session(self, opening_amount=0):
        """Abrir sesión de TPV"""
        # Verificar si ya hay una sesión abierta
        existing_session = POSSession.objects.filter(
            operator=self.user,
            branch=self.branch,
            pos_terminal=self.terminal,
            state='open'
        ).first()
        
        if existing_session:
            raise ValueError("Ya existe una sesión abierta para este operador")
        
        # Crear nueva sesión
        session_number = self._generate_session_number()
        self.current_session = POSSession.objects.create(
            number=session_number,
            operator=self.user,
            branch=self.branch,
            pos_terminal=self.terminal,
            opening_amount=opening_amount
        )
        
        # Crear log de apertura
        POSSessionLog.objects.create(
            session=self.current_session,
            user=self.user,
            action='open',
            amount=opening_amount,
            notes="Sesión abierta"
        )
        
        return self.current_session
    
    def close_session(self, closing_amount):
        """Cerrar sesión de TPV"""
        if not self.current_session:
            raise ValueError("No hay sesión abierta")
        
        self.current_session.close_session(closing_amount, self.user)
        return self.current_session
    
    def _generate_session_number(self):
        """Generar número de sesión único"""
        prefix = f"SES{self.branch.code}{self.terminal.code}"
        last_session = POSSession.objects.filter(
            branch=self.branch,
            pos_terminal=self.terminal
        ).order_by('-number').first()
        
        if last_session:
            last_number = int(last_session.number.replace(prefix, ''))
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:06d}"

class POSProductService:
    """
    Servicio para búsqueda y gestión de productos en TPV
    Integrado con el módulo de inventory cuando está activado
    """
    
    def __init__(self, price_list):
        self.price_list = price_list
        # Verificar si el módulo de inventory está disponible
        self.inventory_available = apps.is_installed('inventory')
    
    def search_product(self, search_term, search_type='barcode'):
        """
        Buscar producto por diferentes criterios
        
        Args:
            search_term: Término de búsqueda
            search_type: Tipo de búsqueda ('barcode', 'code', 'name', 'ean13')
        """
        if search_type == 'barcode':
            # Búsqueda por código de barras
            return self._search_by_barcode(search_term)
        elif search_type == 'code':
            # Búsqueda por código interno
            return self._search_by_code(search_term)
        elif search_type == 'name':
            # Búsqueda por nombre
            return self._search_by_name(search_term)
        elif search_type == 'ean13':
            # Búsqueda por EAN13 (especial para balanzas)
            return self._search_by_ean13(search_term)
        else:
            raise ValueError(f"Tipo de búsqueda no válido: {search_type}")
    
    def _search_by_barcode(self, barcode):
        """Búsqueda por código de barras"""
        if self.inventory_available:
            from inventory.models import ProductVariant
            
            # Buscar por código de barras principal
            product = ProductVariant.objects.filter(
                barcode=barcode,
                is_active=True,
                product__is_active=True
            ).first()
            
            if product:
                return self._get_product_with_price(product)
            
            # Buscar por códigos de barras alternativos
            product = ProductVariant.objects.filter(
                alternative_barcodes__contains=barcode,
                is_active=True,
                product__is_active=True
            ).first()
            
            return self._get_product_with_price(product) if product else None
        else:
            # Si no hay módulo de inventory, buscar en productos básicos
            return self._search_basic_product(barcode)
    
    def _search_by_code(self, code):
        """Búsqueda por código interno"""
        if self.inventory_available:
            from inventory.models import ProductVariant
            
            product = ProductVariant.objects.filter(
                sku=code,
                is_active=True,
                product__is_active=True
            ).first()
            
            return self._get_product_with_price(product) if product else None
        else:
            return self._search_basic_product(code)
    
    def _search_by_name(self, name):
        """Búsqueda por nombre"""
        if self.inventory_available:
            from inventory.models import ProductVariant
            
            products = ProductVariant.objects.filter(
                product__name__icontains=name,
                is_active=True,
                product__is_active=True
            )[:10]  # Limitar resultados
            
            return [self._get_product_with_price(p) for p in products]
        else:
            return self._search_basic_products_by_name(name)
    
    def _search_by_ean13(self, ean13):
        """
        Búsqueda especial para EAN13 de balanzas
        Formato: 20XXXXXYYYYYYZ (20=pesable, XXXXX=código, YYYYYY=peso, Z=verificador)
        """
        if len(ean13) != 13 or not ean13.isdigit():
            return None
        
        prefix = ean13[:2]
        if prefix not in ['20', '21']:
            return None
        
        # Extraer código de producto y peso
        if prefix == '20':  # Producto pesable
            product_code = ean13[2:7]  # 5 dígitos para código
            weight_grams = int(ean13[7:13])  # 6 dígitos para peso en gramos
            weight_kg = weight_grams / 1000.0
        else:  # Producto unitario
            product_code = ean13[2:7]
            weight_kg = 1.0
        
        # Buscar producto
        if self.inventory_available:
            from inventory.models import ProductVariant
            product = ProductVariant.objects.filter(
                sku=product_code,
                is_active=True,
                product__is_active=True
            ).first()
            
            if product:
                product_data = self._get_product_with_price(product)
                product_data['weight'] = weight_kg
                product_data['is_weight_product'] = (prefix == '20')
                return product_data
        else:
            # Búsqueda básica sin inventory
            product_data = self._search_basic_product(product_code)
            if product_data:
                product_data['weight'] = weight_kg
                product_data['is_weight_product'] = (prefix == '20')
                return product_data
        
        return None
    
    def _get_product_with_price(self, product):
        """Obtener producto con precio de la lista de precios"""
        # Buscar precio en la lista de precios
        price_item = self.price_list.items.filter(
            product_variant=product
        ).first()
        
        price = price_item.price if price_item else product.price
        
        product_data = {
            'id': product.id,
            'name': product.product.name,
            'sku': product.sku,
            'barcode': product.barcode,
            'price': price,
            'unit': product.unit,
            'tax_percentage': product.tax_percentage or 0,
            'requires_lot': product.requires_lot,
            'is_weight_product': product.is_weight_product,
        }
        
        # Agregar información de stock solo si el módulo de inventory está disponible
        if self.inventory_available:
            product_data['stock'] = product.get_available_stock()
        else:
            product_data['stock'] = 999999  # Stock ilimitado cuando no hay inventory
        
        return product_data
    
    def _search_basic_product(self, search_term):
        """Búsqueda básica de productos cuando no hay módulo de inventory"""
        # Implementar búsqueda en productos básicos del core
        # Por ahora, retornar None
        return None
    
    def _search_basic_products_by_name(self, name):
        """Búsqueda básica por nombre cuando no hay módulo de inventory"""
        # Implementar búsqueda en productos básicos del core
        # Por ahora, retornar lista vacía
        return []
    
    def validate_stock(self, product_id, quantity, warehouse=None):
        """Validar stock disponible"""
        if not self.inventory_available:
            # Si no hay módulo de inventory, no validar stock
            return True, "Stock no validado (módulo inventory no activo)"
        
        from inventory.models import ProductVariant
        
        product = ProductVariant.objects.get(id=product_id)
        available_stock = product.get_available_stock(warehouse)
        
        if available_stock < quantity:
            return False, f"Stock insuficiente. Disponible: {available_stock}"
        
        return True, "Stock válido"
    
    def update_stock(self, product_id, quantity, operation='decrease', warehouse=None):
        """
        Actualizar stock del producto
        
        Args:
            product_id: ID del producto
            quantity: Cantidad a modificar
            operation: 'decrease' para ventas, 'increase' para devoluciones
            warehouse: Almacén específico (opcional)
        """
        if not self.inventory_available:
            # Si no hay módulo de inventory, no actualizar stock
            return True, "Stock no actualizado (módulo inventory no activo)"
        
        try:
            from inventory.models import ProductVariant
            from inventory.services.stock import StockService
            
            product = ProductVariant.objects.get(id=product_id)
            stock_service = StockService()
            
            if operation == 'decrease':
                success = stock_service.decrease_stock(
                    product=product,
                    quantity=quantity,
                    warehouse=warehouse,
                    reference=f"Venta TPV - {timezone.now().strftime('%Y%m%d%H%M%S')}",
                    user=self.user if hasattr(self, 'user') else None
                )
            else:  # increase
                success = stock_service.increase_stock(
                    product=product,
                    quantity=quantity,
                    warehouse=warehouse,
                    reference=f"Devolución TPV - {timezone.now().strftime('%Y%m%d%H%M%S')}",
                    user=self.user if hasattr(self, 'user') else None
                )
            
            if success:
                return True, "Stock actualizado correctamente"
            else:
                return False, "Error al actualizar stock"
                
        except Exception as e:
            return False, f"Error al actualizar stock: {str(e)}"

class POSSaleService:
    """
    Servicio para gestión de ventas en TPV
    Integrado con módulos de inventory y accounting cuando están activados
    """
    
    def __init__(self, session):
        self.session = session
        # Verificar módulos disponibles
        self.inventory_available = apps.is_installed('inventory')
        self.accounting_available = apps.is_installed('accounting')
    
    def create_sale(self, client=None, is_occasional=False, occasional_data=None):
        """Crear nueva venta"""
        sale = POSSale.objects.create(
            session=self.session,
            operator=self.session.operator,
            client=client,
            is_occasional_client=is_occasional,
            occasional_client_data=occasional_data or {},
            price_list=self.session.branch.default_price_list
        )
        
        return sale
    
    def add_product(self, sale, product_data, quantity=1, discount_percentage=0):
        """Agregar producto a la venta"""
        if self.inventory_available:
            from inventory.models import ProductVariant
            
            product = ProductVariant.objects.get(id=product_data['id'])
            
            # Validar stock
            stock_valid, message = POSProductService(sale.price_list).validate_stock(
                product.id, quantity
            )
            if not stock_valid:
                raise ValueError(message)
        else:
            # Si no hay módulo de inventory, usar datos básicos
            product = None
        
        # Crear línea de venta
        line = POSSaleLine.objects.create(
            sale=sale,
            product_variant=product,
            quantity=quantity,
            unit_price=product_data['price'],
            discount_percentage=discount_percentage,
            tax_percentage=product_data['tax_percentage'],
            barcode=product_data.get('barcode', ''),
            description=product_data['name']
        )
        
        # Recalcular totales
        sale.recalculate_totals()
        
        return line
    
    def remove_product(self, sale, line_id):
        """Remover producto de la venta"""
        line = POSSaleLine.objects.get(id=line_id, sale=sale)
        line.delete()
        
        # Recalcular totales
        sale.recalculate_totals()
        
        return True
    
    def apply_promotion(self, sale, promotion_code):
        """Aplicar promoción a la venta"""
        promotion = POSPromotion.objects.filter(
            code=promotion_code,
            is_active=True
        ).first()
        
        if not promotion:
            raise ValueError("Promoción no encontrada o inactiva")
        
        sale_data = {
            'subtotal': sale.subtotal,
            'total': sale.total,
            'lines': list(sale.lines.all())
        }
        
        if not promotion.is_valid(sale_data):
            raise ValueError("Promoción no válida para esta venta")
        
        discount = promotion.calculate_discount(sale_data)
        
        # Aplicar descuento a la venta
        sale.total_discount += discount
        sale.total = sale.subtotal - sale.total_discount + sale.total_tax
        sale.save()
        
        return discount
    
    @transaction.atomic
    def complete_sale(self, sale, payments_data):
        """Completar venta con pagos"""
        # Validar que el total pagado sea igual al total de la venta
        total_paid = sum(payment['amount'] for payment in payments_data)
        
        if abs(total_paid - sale.total) > 0.01:  # Tolerancia para redondeo
            raise ValueError("El monto pagado no coincide con el total de la venta")
        
        # Actualizar stock si el módulo de inventory está disponible
        if self.inventory_available:
            self._update_stock_for_sale(sale)
        
        # Crear asientos contables si el módulo de accounting está disponible
        if self.accounting_available:
            self._create_accounting_entries(sale, payments_data)
        
        # Completar venta
        sale.complete_sale(payments_data)
        
        # Generar comprobante fiscal si es necesario
        if sale.session.pos_terminal.electronic_invoice:
            self._generate_fiscal_document(sale)
        
        return sale
    
    def _update_stock_for_sale(self, sale):
        """Actualizar stock para todos los productos de la venta"""
        if not self.inventory_available:
            return
        
        product_service = POSProductService(sale.price_list)
        
        for line in sale.lines.all():
            if line.product_variant:
                success, message = product_service.update_stock(
                    product_id=line.product_variant.id,
                    quantity=line.quantity,
                    operation='decrease',
                    warehouse=sale.session.branch.default_warehouse if hasattr(sale.session.branch, 'default_warehouse') else None
                )
                
                if not success:
                    raise ValueError(f"Error al actualizar stock: {message}")
    
    def _create_accounting_entries(self, sale, payments_data):
        """Crear asientos contables para la venta"""
        if not self.accounting_available:
            return
        
        try:
            from accounting.services.sales_accounting import SalesAccountingService
            
            accounting_service = SalesAccountingService()
            
            # Crear asiento de venta
            accounting_service.create_sale_entry(
                sale=sale,
                total_amount=sale.total,
                tax_amount=sale.total_tax,
                client=sale.client
            )
            
            # Crear asientos de pago
            for payment_data in payments_data:
                accounting_service.create_payment_entry(
                    sale=sale,
                    payment_method=payment_data['method'],
                    amount=payment_data['amount'],
                    reference=payment_data.get('reference', '')
                )
                
        except Exception as e:
            # Log del error pero no fallar la venta
            print(f"Error al crear asientos contables: {str(e)}")
    
    def _generate_fiscal_document(self, sale):
        """Generar comprobante fiscal"""
        # Aquí se integraría con el sistema fiscal
        # Por ahora, solo actualizar datos básicos
        sale.invoice_type = 'FA'  # Factura A
        sale.invoice_number = self._generate_invoice_number(sale)
        sale.save()
    
    def _generate_invoice_number(self, sale):
        """Generar número de factura"""
        # Implementar lógica de numeración fiscal
        return f"FA{self.session.branch.code}{sale.invoice_number}"

class POSPaymentService:
    """
    Servicio para gestión de pagos en TPV
    """
    
    @staticmethod
    def validate_payment_method(method, amount, reference=None):
        """Validar método de pago"""
        if method not in dict(POSPayment.PAYMENT_METHODS):
            raise ValueError("Método de pago no válido")
        
        if amount <= 0:
            raise ValueError("El monto debe ser mayor a 0")
        
        # Validaciones específicas por método
        if method == 'credit_card' and not reference:
            raise ValueError("Se requiere número de tarjeta para pagos con tarjeta")
        
        if method == 'check' and not reference:
            raise ValueError("Se requiere número de cheque")
        
        return True
    
    @staticmethod
    def calculate_change(total_amount, paid_amount):
        """Calcular vuelto"""
        if paid_amount < total_amount:
            return 0
        
        return paid_amount - total_amount
    
    @staticmethod
    def process_card_payment(amount, card_data):
        """Procesar pago con tarjeta"""
        # Aquí se integraría con el procesador de pagos
        # Por ahora, simular procesamiento exitoso
        return {
            'success': True,
            'transaction_id': f"TXN{int(time.time())}",
            'authorization_code': f"AUTH{int(time.time())}",
            'amount': amount
        }

class POSReportService:
    """
    Servicio para reportes de TPV
    """
    
    def __init__(self, session):
        self.session = session
    
    def get_session_summary(self):
        """Obtener resumen de la sesión"""
        sales = self.session.sales.filter(state='completed')
        
        return {
            'total_sales': sales.count(),
            'total_amount': sales.aggregate(total=models.Sum('total'))['total'] or 0,
            'total_payments': sales.aggregate(total=models.Sum('total_paid'))['total'] or 0,
            'payment_methods': self._get_payment_methods_summary(),
            'products_sold': self._get_products_summary(),
        }
    
    def _get_payment_methods_summary(self):
        """Obtener resumen por método de pago"""
        payments = POSPayment.objects.filter(sale__session=self.session)
        
        summary = {}
        for method, _ in POSPayment.PAYMENT_METHODS:
            amount = payments.filter(payment_method=method).aggregate(
                total=models.Sum('amount')
            )['total'] or 0
            summary[method] = amount
        
        return summary
    
    def _get_products_summary(self):
        """Obtener resumen de productos vendidos"""
        lines = POSSaleLine.objects.filter(sale__session=self.session)
        
        return lines.values('product_variant__product__name').annotate(
            total_quantity=models.Sum('quantity'),
            total_amount=models.Sum('subtotal')
        ).order_by('-total_amount')

class POSIntegrationService:
    """
    Servicio para integraciones del TPV
    """
    
    def __init__(self, terminal):
        self.terminal = terminal
    
    def print_receipt(self, sale):
        """Imprimir ticket de venta"""
        # Integración con impresora de tickets
        receipt_data = self._generate_receipt_data(sale)
        
        # Aquí se enviaría a la impresora
        # Por ahora, solo retornar datos
        return receipt_data
    
    def print_fiscal_receipt(self, sale):
        """Imprimir comprobante fiscal"""
        if not self.terminal.fiscal_printer:
            raise ValueError("No hay impresora fiscal configurada")
        
        fiscal_data = self._generate_fiscal_data(sale)
        
        # Integración con impresora fiscal
        return fiscal_data
    
    def send_to_scale(self, command):
        """Enviar comando a balanza"""
        if not self.terminal.scale_integration:
            raise ValueError("No hay balanza configurada")
        
        # Integración con balanza
        # Por ahora, simular respuesta
        return {
            'weight': 1.250,
            'unit': 'kg',
            'stable': True
        }
    
    def _generate_receipt_data(self, sale):
        """Generar datos del ticket"""
        return {
            'header': {
                'company_name': sale.session.branch.company.name,
                'branch_name': sale.session.branch.name,
                'terminal': sale.session.pos_terminal.name,
                'sale_number': sale.number,
                'date': sale.sale_date.strftime('%d/%m/%Y %H:%M'),
                'operator': sale.operator.get_full_name(),
            },
            'lines': [
                {
                    'description': line.description,
                    'quantity': line.quantity,
                    'unit_price': line.unit_price,
                    'subtotal': line.subtotal,
                }
                for line in sale.lines.all()
            ],
            'totals': {
                'subtotal': sale.subtotal,
                'discount': sale.total_discount,
                'tax': sale.total_tax,
                'total': sale.total,
            },
            'payments': [
                {
                    'method': payment.get_payment_method_display(),
                    'amount': payment.amount,
                }
                for payment in sale.payments.all()
            ]
        }
    
    def _generate_fiscal_data(self, sale):
        """Generar datos fiscales"""
        return {
            'invoice_type': sale.invoice_type,
            'invoice_number': sale.invoice_number,
            'client_data': self._get_client_fiscal_data(sale),
            'items': [
                {
                    'description': line.description,
                    'quantity': line.quantity,
                    'unit_price': line.unit_price,
                    'tax_percentage': line.tax_percentage,
                    'subtotal': line.subtotal,
                }
                for line in sale.lines.all()
            ],
            'totals': {
                'subtotal': sale.subtotal,
                'tax': sale.total_tax,
                'total': sale.total,
            }
        }
    
    def _get_client_fiscal_data(self, sale):
        """Obtener datos fiscales del cliente"""
        if sale.client:
            return {
                'name': sale.client.name,
                'tax_id': sale.client.tax_id,
                'fiscal_condition': sale.client.fiscal_conditions,
            }
        else:
            return {
                'name': sale.occasional_client_data.get('name', 'Consumidor Final'),
                'tax_id': sale.occasional_client_data.get('tax_id', ''),
                'fiscal_condition': 'Consumidor Final',
            } 