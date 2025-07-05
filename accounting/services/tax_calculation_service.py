from decimal import Decimal
from django.db.models import Q
from typing import Dict, List, Optional, Tuple

from ..models import Tax, TaxGroup, FiscalPosition, TaxLine
from sales.models import SalesOrder, SalesOrderLine
from inventory.models import ProductVariant


class TaxCalculationService:
    """Servicio para cálculo automático de impuestos en órdenes de venta"""
    
    @staticmethod
    def get_default_taxes_for_product(product_variant: ProductVariant, empresa) -> List[Tax]:
        """Obtener impuestos por defecto para un producto"""
        # Buscar impuestos asociados al producto o su categoría
        taxes = Tax.objects.filter(
            empresa=empresa,
            is_active=True
        )
        
        # Si el producto tiene impuestos específicos, usarlos
        if hasattr(product_variant.product, 'taxes') and product_variant.product.taxes.exists():
            return list(product_variant.product.taxes.filter(is_active=True))
        
        # Si no, buscar por grupo de impuestos por defecto
        default_tax_group = TaxGroup.objects.filter(
            empresa=empresa,
            is_active=True,
            is_default=True
        ).first()
        
        if default_tax_group:
            return list(default_tax_group.taxes.filter(is_active=True))
        
        # Si no hay grupo por defecto, devolver impuestos activos
        return list(taxes[:3])  # Máximo 3 impuestos por defecto
    
    @staticmethod
    def get_fiscal_position_for_order(order: SalesOrder) -> Optional[FiscalPosition]:
        """Determinar posición fiscal para una orden"""
        # Buscar posición fiscal basada en cliente y empresa
        fiscal_position = FiscalPosition.objects.filter(
            empresa=order.branch.empresa,
            is_active=True,
            client=order.client
        ).first()
        
        if not fiscal_position:
            # Buscar posición fiscal por defecto
            fiscal_position = FiscalPosition.objects.filter(
                empresa=order.branch.empresa,
                is_active=True,
                is_default=True
            ).first()
        
        return fiscal_position
    
    @staticmethod
    def apply_fiscal_position_taxes(taxes: List[Tax], fiscal_position: FiscalPosition) -> List[Tax]:
        """Aplicar mapeos de posición fiscal a los impuestos"""
        if not fiscal_position:
            return taxes
        
        mapped_taxes = []
        
        for tax in taxes:
            # Buscar mapeo específico para este impuesto
            mapping = fiscal_position.tax_mappings.filter(
                source_tax=tax
            ).first()
            
            if mapping and mapping.target_tax:
                mapped_taxes.append(mapping.target_tax)
            else:
                mapped_taxes.append(tax)
        
        return mapped_taxes
    
    @staticmethod
    def calculate_line_taxes(
        line: SalesOrderLine,
        taxes: List[Tax],
        base_amount: Decimal
    ) -> Tuple[Decimal, List[Dict]]:
        """
        Calcular impuestos para una línea de orden
        
        Returns:
            Tuple[total_tax_amount, list_of_tax_details]
        """
        total_tax_amount = Decimal('0.00')
        tax_details = []
        
        for tax in taxes:
            if tax.amount_type == 'percent':
                tax_amount = base_amount * (tax.amount / Decimal('100'))
            else:
                tax_amount = tax.amount * line.quantity
            
            total_tax_amount += tax_amount
            
            tax_details.append({
                'tax': tax,
                'amount': tax_amount,
                'base': base_amount,
                'rate': tax.amount,
                'type': tax.amount_type
            })
        
        return total_tax_amount, tax_details
    
    @staticmethod
    def apply_automatic_taxes_to_order_line(line: SalesOrderLine) -> Dict:
        """Aplicar impuestos automáticos a una línea de orden"""
        empresa = line.sales_order.branch.empresa
        
        # 1. Obtener impuestos por defecto del producto
        default_taxes = TaxCalculationService.get_default_taxes_for_product(
            line.product_variant, 
            empresa
        )
        
        # 2. Obtener posición fiscal
        fiscal_position = TaxCalculationService.get_fiscal_position_for_order(line.sales_order)
        
        # 3. Aplicar mapeos de posición fiscal
        final_taxes = TaxCalculationService.apply_fiscal_position_taxes(
            default_taxes, 
            fiscal_position
        )
        
        # 4. Calcular impuestos
        base_amount = line.subtotal
        total_tax_amount, tax_details = TaxCalculationService.calculate_line_taxes(
            line, 
            final_taxes, 
            base_amount
        )
        
        # 5. Actualizar línea
        line.taxes.set(final_taxes)
        line.fiscal_position = fiscal_position
        line.tax_amount = total_tax_amount
        
        # Mantener compatibilidad con campo legacy
        if final_taxes:
            # Usar el primer impuesto para el porcentaje legacy
            first_tax = final_taxes[0]
            if first_tax.amount_type == 'percent':
                line.tax_percentage = first_tax.amount
            else:
                line.tax_percentage = Decimal('0.00')
        else:
            line.tax_percentage = Decimal('0.00')
        
        line.save()
        
        return {
            'taxes': final_taxes,
            'fiscal_position': fiscal_position,
            'total_tax_amount': total_tax_amount,
            'tax_details': tax_details,
            'base_amount': base_amount
        }
    
    @staticmethod
    def recalculate_order_totals(order: SalesOrder) -> Dict:
        """Recalcular totales de impuestos de toda la orden"""
        total_tax = Decimal('0.00')
        total_subtotal = Decimal('0.00')
        total_discount = Decimal('0.00')
        
        for line in order.lines.all():
            # Recalcular subtotal de la línea
            line.recalculate_subtotal()
            
            # Aplicar impuestos automáticos si no tiene impuestos manuales
            if not line.taxes.exists():
                TaxCalculationService.apply_automatic_taxes_to_order_line(line)
            
            total_subtotal += line.subtotal
            total_discount += (line.quantity * line.unit_price) - line.subtotal
            total_tax += line.tax_amount
        
        # Actualizar totales de la orden
        order.total = total_subtotal + total_tax
        order.total_discount = total_discount
        order.total_tax = total_tax
        order.save(update_fields=['total', 'total_discount', 'total_tax'])
        
        return {
            'total': order.total,
            'total_subtotal': total_subtotal,
            'total_discount': total_discount,
            'total_tax': total_tax
        }
    
    @staticmethod
    def get_tax_summary_for_order(order: SalesOrder) -> List[Dict]:
        """Obtener resumen de impuestos agrupados por tipo"""
        tax_summary = {}
        
        for line in order.lines.all():
            for tax in line.taxes.all():
                tax_key = f"{tax.id}_{tax.amount_type}"
                
                if tax_key not in tax_summary:
                    tax_summary[tax_key] = {
                        'tax': tax,
                        'base_amount': Decimal('0.00'),
                        'tax_amount': Decimal('0.00'),
                        'lines_count': 0
                    }
                
                summary = tax_summary[tax_key]
                summary['base_amount'] += line.subtotal
                summary['tax_amount'] += line.tax_amount
                summary['lines_count'] += 1
        
        return list(tax_summary.values())
    
    @staticmethod
    def validate_tax_configuration(order: SalesOrder) -> List[str]:
        """Validar configuración de impuestos de una orden"""
        errors = []
        empresa = order.branch.empresa
        
        # Verificar que existan impuestos configurados
        if not Tax.objects.filter(empresa=empresa, is_active=True).exists():
            errors.append("No hay impuestos configurados para esta empresa")
        
        # Verificar que existan posiciones fiscales
        if not FiscalPosition.objects.filter(empresa=empresa, is_active=True).exists():
            errors.append("No hay posiciones fiscales configuradas")
        
        # Verificar que los productos tengan impuestos asignados
        for line in order.lines.all():
            if not line.taxes.exists():
                errors.append(f"El producto {line.product_variant} no tiene impuestos asignados")
        
        return errors


class TaxLineService:
    """Servicio para gestión de líneas de impuestos"""
    
    @staticmethod
    def create_tax_lines_from_order_line(line: SalesOrderLine) -> List[TaxLine]:
        """Crear líneas de impuestos desde una línea de orden"""
        tax_lines = []
        
        for tax in line.taxes.all():
            if tax.amount_type == 'percent':
                amount = line.subtotal * (tax.amount / Decimal('100'))
            else:
                amount = tax.amount * line.quantity
            
            tax_line = TaxLine.objects.create(
                empresa=line.sales_order.branch.empresa,
                tax_id=tax,
                base=line.subtotal,
                amount=amount,
                description=f"Impuesto {tax.name} - {line.product_variant}",
                reference_model='sales.SalesOrderLine',
                reference_id=line.id
            )
            tax_lines.append(tax_line)
        
        # Asociar líneas de impuestos a la línea de orden
        line.tax_lines.set(tax_lines)
        
        return tax_lines
    
    @staticmethod
    def create_tax_lines_from_order(order: SalesOrder) -> List[TaxLine]:
        """Crear líneas de impuestos para toda la orden"""
        all_tax_lines = []
        
        for line in order.lines.all():
            tax_lines = TaxLineService.create_tax_lines_from_order_line(line)
            all_tax_lines.extend(tax_lines)
        
        return all_tax_lines 