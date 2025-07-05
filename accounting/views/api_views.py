from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from decimal import Decimal
import json

from ..models import Tax, TaxGroup, FiscalPosition
from ..services.tax_calculation_service import TaxCalculationService
from sales.models import SalesOrder, SalesOrderLine
from inventory.models import ProductVariant
from core.utils import get_empresa_actual


@login_required
@require_http_methods(["GET"])
def get_taxes_for_product(request):
    """Obtener impuestos disponibles para un producto"""
    try:
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'error': _('Product ID is required')}, status=400)
        
        product = get_object_or_404(ProductVariant, id=product_id)
        empresa = get_empresa_actual(request)
        
        # Obtener impuestos por defecto para el producto
        default_taxes = TaxCalculationService.get_default_taxes_for_product(product, empresa)
        
        # Obtener todos los impuestos disponibles
        all_taxes = Tax.objects.filter(empresa=empresa, is_active=True).select_related('tax_group')
        
        taxes_data = []
        for tax in all_taxes:
            taxes_data.append({
                'id': tax.id,
                'name': tax.name,
                'code': tax.code,
                'amount': float(tax.amount),
                'amount_type': tax.amount_type,
                'tax_group': tax.tax_group.name if tax.tax_group else None,
                'is_default': tax in default_taxes
            })
        
        return JsonResponse({
            'success': True,
            'taxes': taxes_data,
            'default_taxes': [tax.id for tax in default_taxes]
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_fiscal_positions(request):
    """Obtener posiciones fiscales disponibles"""
    try:
        client_id = request.GET.get('client_id')
        empresa = get_empresa_actual(request)
        
        fiscal_positions = FiscalPosition.objects.filter(
            empresa=empresa,
            is_active=True
        )
        
        if client_id:
            # Filtrar por cliente específico
            client_positions = fiscal_positions.filter(client_id=client_id)
            if client_positions.exists():
                fiscal_positions = client_positions
        
        positions_data = []
        for position in fiscal_positions:
            positions_data.append({
                'id': position.id,
                'name': position.name,
                'description': position.description,
                'is_default': position.is_default,
                'client': position.client.name if position.client else None
            })
        
        return JsonResponse({
            'success': True,
            'fiscal_positions': positions_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def calculate_line_taxes(request):
    """Calcular impuestos para una línea de orden"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = Decimal(data.get('quantity', '0'))
        unit_price = Decimal(data.get('unit_price', '0'))
        discount = Decimal(data.get('discount', '0'))
        selected_taxes = data.get('taxes', [])
        fiscal_position_id = data.get('fiscal_position_id')
        
        if not product_id:
            return JsonResponse({'error': _('Product ID is required')}, status=400)
        
        product = get_object_or_404(ProductVariant, id=product_id)
        empresa = get_empresa_actual(request)
        
        # Calcular subtotal
        total = quantity * unit_price
        discount_amount = total * (discount / Decimal('100'))
        subtotal = total - discount_amount
        
        # Obtener impuestos
        if selected_taxes:
            taxes = Tax.objects.filter(id__in=selected_taxes, empresa=empresa, is_active=True)
        else:
            taxes = TaxCalculationService.get_default_taxes_for_product(product, empresa)
        
        # Aplicar posición fiscal si se especifica
        if fiscal_position_id:
            fiscal_position = get_object_or_404(FiscalPosition, id=fiscal_position_id, empresa=empresa)
            taxes = TaxCalculationService.apply_fiscal_position_taxes(taxes, fiscal_position)
        
        # Calcular impuestos
        total_tax_amount, tax_details = TaxCalculationService.calculate_line_taxes(
            None, taxes, subtotal
        )
        
        # Preparar respuesta
        taxes_response = []
        for detail in tax_details:
            taxes_response.append({
                'tax_id': detail['tax'].id,
                'tax_name': detail['tax'].name,
                'tax_code': detail['tax'].code,
                'amount': float(detail['amount']),
                'rate': float(detail['rate']),
                'type': detail['type']
            })
        
        return JsonResponse({
            'success': True,
            'subtotal': float(subtotal),
            'total_tax_amount': float(total_tax_amount),
            'total_with_tax': float(subtotal + total_tax_amount),
            'taxes': taxes_response,
            'fiscal_position_id': fiscal_position_id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def apply_automatic_taxes_to_order(request):
    """Aplicar impuestos automáticos a una orden completa"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        
        if not order_id:
            return JsonResponse({'error': _('Order ID is required')}, status=400)
        
        order = get_object_or_404(SalesOrder, id=order_id)
        
        # Aplicar impuestos automáticos a todas las líneas
        lines_updated = []
        for line in order.lines.all():
            result = TaxCalculationService.apply_automatic_taxes_to_order_line(line)
            lines_updated.append({
                'line_id': line.id,
                'product': line.product_variant.product.name,
                'taxes_applied': [tax.name for tax in result['taxes']],
                'tax_amount': float(result['total_tax_amount'])
            })
        
        # Recalcular totales de la orden
        totals = TaxCalculationService.recalculate_order_totals(order)
        
        return JsonResponse({
            'success': True,
            'lines_updated': lines_updated,
            'order_totals': {
                'total': float(totals['total']),
                'total_subtotal': float(totals['total_subtotal']),
                'total_discount': float(totals['total_discount']),
                'total_tax': float(totals['total_tax'])
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_tax_summary(request):
    """Obtener resumen de impuestos de una orden"""
    try:
        order_id = request.GET.get('order_id')
        
        if not order_id:
            return JsonResponse({'error': _('Order ID is required')}, status=400)
        
        order = get_object_or_404(SalesOrder, id=order_id)
        tax_summary = TaxCalculationService.get_tax_summary_for_order(order)
        
        summary_data = []
        for summary in tax_summary:
            summary_data.append({
                'tax_name': summary['tax'].name,
                'tax_code': summary['tax'].code,
                'base_amount': float(summary['base_amount']),
                'tax_amount': float(summary['tax_amount']),
                'rate': float(summary['tax'].amount),
                'type': summary['tax'].amount_type,
                'lines_count': summary['lines_count']
            })
        
        return JsonResponse({
            'success': True,
            'tax_summary': summary_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def update_line_taxes(request):
    """Actualizar impuestos de una línea específica"""
    try:
        data = json.loads(request.body)
        line_id = data.get('line_id')
        selected_taxes = data.get('taxes', [])
        fiscal_position_id = data.get('fiscal_position_id')
        
        if not line_id:
            return JsonResponse({'error': _('Line ID is required')}, status=400)
        
        line = get_object_or_404(SalesOrderLine, id=line_id)
        empresa = line.sales_order.branch.empresa
        
        # Actualizar impuestos de la línea
        if selected_taxes:
            taxes = Tax.objects.filter(id__in=selected_taxes, empresa=empresa, is_active=True)
            line.taxes.set(taxes)
        else:
            line.taxes.clear()
        
        # Actualizar posición fiscal
        if fiscal_position_id:
            fiscal_position = get_object_or_404(FiscalPosition, id=fiscal_position_id, empresa=empresa)
            line.fiscal_position = fiscal_position
        else:
            line.fiscal_position = None
        
        # Recalcular impuestos
        if line.taxes.exists():
            total_tax_amount, tax_details = TaxCalculationService.calculate_line_taxes(
                line, line.taxes.all(), line.subtotal
            )
            line.tax_amount = total_tax_amount
            
            # Actualizar porcentaje legacy
            first_tax = line.taxes.first()
            if first_tax.amount_type == 'percent':
                line.tax_percentage = first_tax.amount
            else:
                line.tax_percentage = Decimal('0.00')
        else:
            line.tax_amount = Decimal('0.00')
            line.tax_percentage = Decimal('0.00')
        
        line.save()
        
        # Recalcular totales de la orden
        totals = TaxCalculationService.recalculate_order_totals(line.sales_order)
        
        return JsonResponse({
            'success': True,
            'line_tax_amount': float(line.tax_amount),
            'line_total_with_tax': float(line.subtotal + line.tax_amount),
            'order_totals': {
                'total': float(totals['total']),
                'total_tax': float(totals['total_tax'])
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def validate_tax_configuration(request):
    """Validar configuración de impuestos"""
    try:
        order_id = request.GET.get('order_id')
        
        if not order_id:
            return JsonResponse({'error': _('Order ID is required')}, status=400)
        
        order = get_object_or_404(SalesOrder, id=order_id)
        errors = TaxCalculationService.validate_tax_configuration(order)
        
        return JsonResponse({
            'success': True,
            'is_valid': len(errors) == 0,
            'errors': errors
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500) 