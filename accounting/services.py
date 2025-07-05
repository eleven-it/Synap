from decimal import Decimal
from django.utils import timezone
from .models import Tax, TaxLine, FiscalPosition, FiscalPositionTax


class TaxCalculationService:
    """Servicio para el cálculo de impuestos"""
    
    def __init__(self, empresa, partner=None, fiscal_position=None):
        self.empresa = empresa
        self.partner = partner
        self.fiscal_position = fiscal_position or self._get_fiscal_position()
    
    def _get_fiscal_position(self):
        """Obtener posición fiscal basada en el partner"""
        if not self.partner:
            return None
        
        # Buscar posición fiscal por país/estado del partner
        return FiscalPosition.objects.filter(
            empresa=self.empresa,
            is_active=True,
            country_id=self.partner.country if hasattr(self.partner, 'country') else '',
        ).first()
    
    def get_applicable_taxes(self, product=None, date=None):
        """Obtener impuestos aplicables para un producto"""
        if date is None:
            date = timezone.now().date()
        
        # Obtener impuestos del producto
        product_taxes = []
        if product:
            product_taxes = list(product.taxes.filter(is_active=True))
        
        # Si no hay impuestos en el producto, usar impuestos por defecto
        if not product_taxes:
            product_taxes = list(Tax.objects.filter(
                empresa=self.empresa,
                is_active=True
            ).order_by('tax_group', 'sequence'))
        
        # Aplicar posición fiscal si existe
        if self.fiscal_position:
            product_taxes = self._apply_fiscal_position(product_taxes)
        
        # Filtrar por aplicabilidad
        applicable_taxes = []
        for tax in product_taxes:
            if tax.is_applicable(product, self.partner, date):
                applicable_taxes.append(tax)
        
        return applicable_taxes
    
    def _apply_fiscal_position(self, taxes):
        """Aplicar mapeo de posición fiscal"""
        if not self.fiscal_position:
            return taxes
        
        mapped_taxes = []
        for tax in taxes:
            # Buscar mapeo en posición fiscal
            mapping = FiscalPositionTax.objects.filter(
                fiscal_position=self.fiscal_position,
                tax_src_id=tax
            ).first()
            
            if mapping:
                mapped_taxes.append(mapping.tax_dest_id)
            else:
                mapped_taxes.append(tax)
        
        return mapped_taxes
    
    def calculate_taxes(self, base_amount, product=None, quantity=1, price_unit=None, date=None):
        """Calcular impuestos para una línea"""
        if date is None:
            date = timezone.now().date()
        
        applicable_taxes = self.get_applicable_taxes(product, date)
        tax_lines = []
        total_tax_amount = Decimal('0')
        
        for tax in applicable_taxes:
            # Calcular monto del impuesto
            tax_amount = tax.compute_amount(base_amount, price_unit, quantity, product, self.partner)
            
            # Crear línea de impuesto
            tax_line = TaxLine(
                tax=tax,
                base_amount=base_amount,
                tax_amount=tax_amount,
                total_amount=base_amount + tax_amount,
                origin_model='sales.SalesOrderLine',
                origin_id=0,  # Se actualizará al guardar
                origin_line_id=0  # Se actualizará al guardar
            )
            
            tax_lines.append(tax_line)
            total_tax_amount += tax_amount
            
            # Si el impuesto afecta la base para otros impuestos
            if tax.include_base_amount and tax.is_base_affected:
                base_amount += tax_amount
        
        return {
            'tax_lines': tax_lines,
            'total_tax_amount': total_tax_amount,
            'total_amount': base_amount + total_tax_amount
        }
    
    def calculate_line_taxes(self, line, save_tax_lines=True):
        """Calcular impuestos para una línea de pedido/factura"""
        # Calcular subtotal base
        base_amount = line.quantity * line.unit_price
        
        # Aplicar descuentos si existen
        if hasattr(line, 'discount') and line.discount:
            discount_amount = base_amount * (line.discount / Decimal('100'))
            base_amount -= discount_amount
        
        # Obtener producto
        product = None
        if hasattr(line, 'product_variant'):
            product = line.product_variant.product
        elif hasattr(line, 'product'):
            product = line.product
        
        # Calcular impuestos
        tax_result = self.calculate_taxes(
            base_amount=base_amount,
            product=product,
            quantity=line.quantity,
            price_unit=line.unit_price
        )
        
        # Guardar líneas de impuesto si se solicita
        if save_tax_lines:
            for tax_line in tax_result['tax_lines']:
                tax_line.origin_id = line.id
                tax_line.origin_line_id = line.id
                tax_line.save()
        
        return tax_result
    
    def calculate_document_taxes(self, document):
        """Calcular impuestos para todo un documento (pedido/factura)"""
        total_tax_amount = Decimal('0')
        all_tax_lines = []
        
        # Calcular impuestos por línea
        for line in document.lines.all():
            tax_result = self.calculate_line_taxes(line, save_tax_lines=False)
            total_tax_amount += tax_result['total_tax_amount']
            all_tax_lines.extend(tax_result['tax_lines'])
        
        return {
            'tax_lines': all_tax_lines,
            'total_tax_amount': total_tax_amount
        }


class TaxReportingService:
    """Servicio para reportes de impuestos"""
    
    def __init__(self, empresa):
        self.empresa = empresa
    
    def get_tax_summary(self, start_date, end_date, tax_group=None):
        """Obtener resumen de impuestos por período"""
        from django.db.models import Sum, Count
        
        filters = {
            'tax__empresa': self.empresa,
            'created_at__date__range': [start_date, end_date]
        }
        
        if tax_group:
            filters['tax__tax_group'] = tax_group
        
        summary = TaxLine.objects.filter(**filters).values(
            'tax__name',
            'tax__tax_group__name'
        ).annotate(
            total_base=Sum('base_amount'),
            total_tax=Sum('tax_amount'),
            line_count=Count('id')
        ).order_by('tax__tax_group__name', 'tax__name')
        
        return summary
    
    def get_tax_by_origin(self, start_date, end_date, origin_model=None):
        """Obtener impuestos agrupados por origen"""
        from django.db.models import Sum
        
        filters = {
            'tax__empresa': self.empresa,
            'created_at__date__range': [start_date, end_date]
        }
        
        if origin_model:
            filters['origin_model'] = origin_model
        
        return TaxLine.objects.filter(**filters).values(
            'origin_model'
        ).annotate(
            total_base=Sum('base_amount'),
            total_tax=Sum('tax_amount'),
            line_count=Count('id')
        ).order_by('origin_model')


class TaxValidationService:
    """Servicio para validación de impuestos"""
    
    def __init__(self, empresa):
        self.empresa = empresa
    
    def validate_tax_configuration(self):
        """Validar configuración de impuestos"""
        errors = []
        warnings = []
        
        # Verificar que existan grupos de impuestos
        tax_groups = TaxGroup.objects.filter(empresa=self.empresa, is_active=True)
        if not tax_groups.exists():
            errors.append("No hay grupos de impuestos configurados")
        
        # Verificar que existan impuestos
        taxes = Tax.objects.filter(empresa=self.empresa, is_active=True)
        if not taxes.exists():
            errors.append("No hay impuestos configurados")
        
        # Verificar cuentas contables
        for tax in taxes:
            if not tax.account_id:
                warnings.append(f"Impuesto '{tax.name}' no tiene cuenta de ventas configurada")
            if not tax.refund_account_id:
                warnings.append(f"Impuesto '{tax.name}' no tiene cuenta de compras configurada")
        
        # Verificar posiciones fiscales
        fiscal_positions = FiscalPosition.objects.filter(empresa=self.empresa, is_active=True)
        for position in fiscal_positions:
            if not position.tax_mappings.exists():
                warnings.append(f"Posición fiscal '{position.name}' no tiene mapeos de impuestos")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }
    
    def validate_tax_calculation(self, base_amount, taxes, expected_total):
        """Validar cálculo de impuestos"""
        errors = []
        
        # Calcular impuestos
        total_tax = Decimal('0')
        for tax in taxes:
            tax_amount = tax.compute_amount(base_amount)
            total_tax += tax_amount
        
        calculated_total = base_amount + total_tax
        
        # Comparar con total esperado
        if abs(calculated_total - expected_total) > Decimal('0.01'):
            errors.append(f"Total calculado ({calculated_total}) no coincide con esperado ({expected_total})")
        
        return {
            'errors': errors,
            'calculated_total': calculated_total,
            'total_tax': total_tax,
            'is_valid': len(errors) == 0
        } 