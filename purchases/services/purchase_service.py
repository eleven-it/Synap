from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import List, Dict, Any, Optional

from ..models import (
    PurchaseRequest, PurchaseRequestLine, PurchaseOrder, PurchaseOrderLine,
    PurchaseQuotation, PurchaseReceipt
)

User = get_user_model()


class PurchaseService:
    """
    Servicio para gestionar operaciones relacionadas con compras
    """
    
    def __init__(self):
        self.user = None
    
    def set_user(self, user: User):
        """Establece el usuario para las operaciones"""
        self.user = user
        return self
    
    def create_purchase_request(
        self,
        empresa,
        branch,
        supplier: Optional = None,
        currency=None,
        required_date=None,
        priority='normal',
        notes="",
        lines_data: List[Dict] = None
    ) -> PurchaseRequest:
        """
        Crea una nueva solicitud de compra
        """
        with transaction.atomic():
            # Crear la solicitud
            request = PurchaseRequest.objects.create(
                empresa=empresa,
                branch=branch,
                supplier=supplier,
                currency=currency,
                required_date=required_date or timezone.now().date(),
                priority=priority,
                notes=notes,
                created_by=self.user
            )
            
            # Crear las líneas si se proporcionan
            if lines_data:
                for line_data in lines_data:
                    self._create_request_line(request, line_data)
            
            return request
    
    def _create_request_line(self, request: PurchaseRequest, line_data: Dict) -> PurchaseRequestLine:
        """Crea una línea de solicitud de compra"""
        from inventory.models import ProductVariant
        from core.models import UnitOfMeasure
        
        # Obtener el producto
        product_variant = ProductVariant.objects.get(id=line_data['product_variant_id'])
        
        # Obtener la unidad de medida
        uom = UnitOfMeasure.objects.get(id=line_data['unit_of_measure_id'])
        
        # Crear la línea
        line = PurchaseRequestLine.objects.create(
            purchase_request=request,
            product_variant=product_variant,
            quantity=line_data['quantity'],
            unit_of_measure=uom,
            description=line_data.get('description', ''),
            specifications=line_data.get('specifications', {})
        )
        
        return line
    
    def create_purchase_order_from_request(
        self,
        request: PurchaseRequest,
        supplier=None,
        quotation: PurchaseQuotation = None,
        expected_delivery_date=None,
        payment_terms="",
        delivery_terms="",
        notes=""
    ) -> PurchaseOrder:
        """
        Crea una orden de compra basada en una solicitud
        """
        with transaction.atomic():
            # Usar el proveedor de la cotización si se proporciona
            if quotation:
                supplier = quotation.supplier
                currency = quotation.currency
                exchange_rate = quotation.exchange_rate
            else:
                supplier = supplier or request.supplier
                currency = request.currency
                exchange_rate = 1.0
            
            # Crear la orden
            order = PurchaseOrder.objects.create(
                empresa=request.empresa,
                branch=request.branch,
                supplier=supplier,
                purchase_request=request,
                quotation=quotation,
                currency=currency,
                exchange_rate=exchange_rate,
                expected_delivery_date=expected_delivery_date or request.required_date,
                payment_terms=payment_terms,
                delivery_terms=delivery_terms,
                notes=notes,
                created_by=self.user
            )
            
            # Crear las líneas de la orden
            for request_line in request.lines.all():
                self._create_order_line_from_request_line(order, request_line, quotation)
            
            # Calcular totales
            order.calculate_totals()
            
            return order
    
    def _create_order_line_from_request_line(
        self,
        order: PurchaseOrder,
        request_line: PurchaseRequestLine,
        quotation: PurchaseQuotation = None
    ) -> PurchaseOrderLine:
        """Crea una línea de orden basada en una línea de solicitud"""
        from core.models import UnitOfMeasure
        
        # Buscar línea de cotización correspondiente
        quotation_line = None
        if quotation:
            quotation_line = quotation.lines.filter(
                request_line=request_line
            ).first()
        
        # Obtener unidad de medida
        uom = request_line.unit_of_measure
        
        # Crear la línea de orden
        line = PurchaseOrderLine.objects.create(
            purchase_order=order,
            request_line=request_line,
            quotation_line=quotation_line,
            product_variant=request_line.product_variant,
            quantity=request_line.quantity,
            unit_of_measure=uom,
            description=request_line.description,
            specifications=request_line.specifications
        )
        
        # Si hay cotización, usar esos precios
        if quotation_line:
            line.unit_price = quotation_line.unit_price
            line.discount_percentage = quotation_line.discount_percentage
            line.tax_percentage = quotation_line.tax_percentage
            line.shipping_amount = quotation_line.shipping_amount
            line.save()
        
        return line
    
    def duplicate_order(self, order: PurchaseOrder, user: User) -> PurchaseOrder:
        """
        Duplica una orden de compra con cantidades sugeridas actualizadas
        """
        with transaction.atomic():
            # Crear nueva orden
            new_order = PurchaseOrder.objects.create(
                empresa=order.empresa,
                branch=order.branch,
                supplier=order.supplier,
                currency=order.currency,
                exchange_rate=order.exchange_rate,
                expected_delivery_date=timezone.now().date() + timezone.timedelta(days=30),
                payment_terms=order.payment_terms,
                delivery_terms=order.delivery_terms,
                notes=f"Duplicated from {order.order_number}",
                created_by=user
            )
            
            # Duplicar líneas con cantidades sugeridas
            for line in order.lines.all():
                # Calcular cantidad sugerida basada en stock actual
                suggested_quantity = self._calculate_suggested_quantity(line.product_variant)
                
                PurchaseOrderLine.objects.create(
                    purchase_order=new_order,
                    product_variant=line.product_variant,
                    quantity=suggested_quantity,
                    unit_of_measure=line.unit_of_measure,
                    unit_price=line.unit_price,
                    discount_percentage=line.discount_percentage,
                    tax_percentage=line.tax_percentage,
                    description=line.description,
                    specifications=line.specifications
                )
            
            # Calcular totales
            new_order.calculate_totals()
            
            return new_order
    
    def _calculate_suggested_quantity(self, product_variant) -> float:
        """
        Calcula la cantidad sugerida basada en el stock actual y ventas recientes
        """
        from inventory.services import StockService
        
        stock_service = StockService()
        current_stock = stock_service.get_current_stock(product_variant)
        
        # Lógica simple: sugerir 2x el stock actual si es bajo
        if current_stock < 10:
            return max(20, current_stock * 2)
        elif current_stock < 50:
            return max(50, current_stock * 1.5)
        else:
            return max(100, current_stock * 1.2)
    
    def receive_order_line(
        self,
        order_line: PurchaseOrderLine,
        quantity: float,
        lot_number: str = None,
        expiration_date = None,
        quality_score: int = None,
        quality_notes: str = ""
    ) -> PurchaseReceipt:
        """
        Registra la recepción de productos de una línea de orden
        """
        with transaction.atomic():
            # Verificar que se puede recibir
            if not order_line.can_receive():
                raise ValidationError(_("Cannot receive more than ordered quantity"))
            
            if quantity > order_line.remaining_quantity:
                raise ValidationError(_("Cannot receive more than remaining quantity"))
            
            # Crear recepción
            receipt = PurchaseReceipt.objects.create(
                empresa=order_line.purchase_order.empresa,
                branch=order_line.purchase_order.branch,
                purchase_order_line=order_line,
                quantity=quantity,
                lot_number=lot_number,
                expiration_date=expiration_date,
                quality_score=quality_score,
                quality_notes=quality_notes,
                received_by=self.user
            )
            
            # Aprobar automáticamente si no hay score de calidad
            if quality_score is None:
                receipt.approve(self.user)
            
            # Actualizar cantidad recibida en la línea
            order_line.received_quantity += quantity
            order_line.save()
            
            # Actualizar estado de la orden
            order_line.purchase_order.update_status()
            
            return receipt
    
    def get_purchase_analytics(self, empresa, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Obtiene análisis de compras para un período
        """
        if not start_date:
            start_date = timezone.now().date() - timezone.timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Obtener órdenes del período
        orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        )
        
        # Calcular métricas
        total_orders = orders.count()
        total_spent = orders.aggregate(total=models.Sum('total_amount'))['total'] or 0
        avg_order_value = total_spent / total_orders if total_orders > 0 else 0
        
        # Estados de órdenes
        status_counts = orders.values('status').annotate(count=models.Count('id'))
        
        # Proveedores más utilizados
        top_suppliers = orders.values('supplier__name').annotate(
            count=models.Count('id'),
            total=models.Sum('total_amount')
        ).order_by('-total')[:10]
        
        # Productos más comprados
        from django.db.models import Sum
        top_products = PurchaseOrderLine.objects.filter(
            purchase_order__empresa=empresa,
            purchase_order__order_date__range=[start_date, end_date]
        ).values('product_variant__name').annotate(
            total_quantity=Sum('quantity'),
            total_value=Sum('total')
        ).order_by('-total_value')[:10]
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_orders': total_orders,
                'total_spent': total_spent,
                'average_order_value': avg_order_value
            },
            'status_distribution': list(status_counts),
            'top_suppliers': list(top_suppliers),
            'top_products': list(top_products)
        }
    
    def get_supplier_performance(self, supplier, period_days=90) -> Dict[str, Any]:
        """
        Obtiene métricas de rendimiento de un proveedor
        """
        from ..models import SupplierPerformanceMetric
        
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=period_days)
        
        # Obtener o crear métricas
        metric, created = SupplierPerformanceMetric.objects.get_or_create(
            supplier=supplier,
            period_start=start_date,
            period_end=end_date,
            defaults={'empresa': supplier.empresa}
        )
        
        if created:
            metric.calculate_metrics()
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': period_days
            },
            'delivery_metrics': {
                'total_orders': metric.total_orders,
                'on_time_deliveries': metric.on_time_deliveries,
                'late_deliveries': metric.late_deliveries,
                'on_time_rate': metric.on_time_delivery_rate,
                'delivery_score': metric.delivery_performance_score
            },
            'quality_metrics': {
                'total_receipts': metric.total_receipts,
                'approved_receipts': metric.approved_receipts,
                'rejected_receipts': metric.rejected_receipts,
                'acceptance_rate': metric.quality_acceptance_rate,
                'quality_score': metric.quality_performance_score
            },
            'financial_metrics': {
                'total_spent': metric.total_spent,
                'average_order_value': metric.average_order_value
            }
        } 