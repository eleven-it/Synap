from django.db.models import Q, Sum, Count, Avg, Max, Min
from django.utils import timezone
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from decimal import Decimal
from datetime import timedelta
import json


class PurchaseReportsService:
    """Servicio para generar reportes de compras en tiempo real"""
    
    def __init__(self, empresa):
        self.empresa = empresa
        self.today = timezone.now().date()
        self.month_start = self.today.replace(day=1)
        self.year_start = self.today.replace(month=1, day=1)
    
    def get_dashboard_metrics(self):
        """Obtener métricas principales del dashboard"""
        return {
            'requests': self._get_request_metrics(),
            'orders': self._get_order_metrics(),
            'spending': self._get_spending_metrics(),
            'suppliers': self._get_supplier_metrics(),
            'delivery': self._get_delivery_metrics(),
            'alerts': self._get_alerts()
        }
    
    def _get_request_metrics(self):
        """Métricas de solicitudes"""
        from .models import PurchaseRequest
        
        # Solicitudes del mes actual
        month_requests = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            request_date__gte=self.month_start
        )
        
        # Solicitudes pendientes
        pending_requests = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            status='pending_approval'
        )
        
        # Solicitudes vencidas (requerimiento pasado)
        overdue_requests = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            status__in=['draft', 'pending_approval'],
            required_date__lt=self.today
        )
        
        return {
            'total_month': month_requests.count(),
            'pending_approval': pending_requests.count(),
            'overdue': overdue_requests.count(),
            'approval_rate': self._calculate_approval_rate(),
            'avg_processing_time': self._calculate_avg_processing_time()
        }
    
    def _get_order_metrics(self):
        """Métricas de órdenes"""
        from .models import PurchaseOrder
        
        # Órdenes del mes actual
        month_orders = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            order_date__gte=self.month_start
        )
        
        # Órdenes pendientes de entrega
        pending_delivery = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['sent', 'confirmed']
        )
        
        # Órdenes vencidas
        overdue_orders = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['sent', 'confirmed'],
            expected_delivery_date__lt=self.today
        )
        
        return {
            'total_month': month_orders.count(),
            'pending_delivery': pending_delivery.count(),
            'overdue': overdue_orders.count(),
            'avg_order_value': self._calculate_avg_order_value(),
            'conversion_rate': self._calculate_conversion_rate()
        }
    
    def _get_spending_metrics(self):
        """Métricas de gastos"""
        from .models import PurchaseOrder
        
        # Gasto del mes actual
        month_spending = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__gte=self.month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Gasto del año actual
        year_spending = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__gte=self.year_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Gasto del mes anterior
        last_month_start = (self.month_start - timedelta(days=1)).replace(day=1)
        last_month_end = self.month_start - timedelta(days=1)
        last_month_spending = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[last_month_start, last_month_end]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Cálculo de variación
        spending_variation = 0
        if last_month_spending > 0:
            spending_variation = ((month_spending - last_month_spending) / last_month_spending) * 100
        
        return {
            'month_total': float(month_spending),
            'year_total': float(year_spending),
            'last_month': float(last_month_spending),
            'variation': round(spending_variation, 2),
            'avg_daily': float(month_spending / self.today.day) if self.today.day > 0 else 0
        }
    
    def _get_supplier_metrics(self):
        """Métricas de proveedores"""
        from .models import Supplier, SupplierRating
        
        # Proveedores activos
        active_suppliers = Supplier.objects.filter(
            empresa=self.empresa,
            is_active=True
        ).count()
        
        # Proveedores con calificación alta
        high_rated_suppliers = Supplier.objects.filter(
            empresa=self.empresa,
            is_active=True,
            rating_class='excellent'
        ).count()
        
        # Calificación promedio
        avg_rating = SupplierRating.objects.filter(
            supplier__empresa=self.empresa,
            status='approved'
        ).aggregate(avg=Avg('overall_score'))['avg'] or 0
        
        # Proveedores con órdenes pendientes
        suppliers_with_pending = Supplier.objects.filter(
            empresa=self.empresa,
            purchase_orders__status__in=['sent', 'confirmed']
        ).distinct().count()
        
        return {
            'active_suppliers': active_suppliers,
            'high_rated': high_rated_suppliers,
            'avg_rating': round(avg_rating, 2),
            'with_pending_orders': suppliers_with_pending,
            'top_supplier': self._get_top_supplier()
        }
    
    def _get_delivery_metrics(self):
        """Métricas de entregas"""
        from .models import PurchaseOrder, PurchaseReceipt
        
        # Entregas del mes
        month_receipts = PurchaseReceipt.objects.filter(
            empresa=self.empresa,
            receipt_date__gte=self.month_start,
            status='approved'
        )
        
        # Entregas a tiempo
        on_time_deliveries = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['partially_received', 'received'],
            last_receipt_date__lte=F('expected_delivery_date')
        ).count()
        
        # Total de entregas completadas
        total_completed = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['partially_received', 'received']
        ).count()
        
        # Tiempo promedio de entrega
        avg_delivery_time = self._calculate_avg_delivery_time()
        
        return {
            'month_receipts': month_receipts.count(),
            'on_time_rate': round((on_time_deliveries / total_completed * 100) if total_completed > 0 else 0, 2),
            'avg_delivery_time': avg_delivery_time,
            'quality_score': self._calculate_avg_quality_score()
        }
    
    def _get_alerts(self):
        """Alertas y notificaciones"""
        alerts = []
        
        # Solicitudes vencidas
        overdue_requests = self._get_overdue_requests()
        if overdue_requests:
            alerts.append({
                'type': 'warning',
                'title': 'Solicitudes Vencidas',
                'message': f'{overdue_requests.count()} solicitudes con fecha de requerimiento vencida',
                'count': overdue_requests.count(),
                'link': '/purchases/requests/?status=overdue'
            })
        
        # Órdenes vencidas
        overdue_orders = self._get_overdue_orders()
        if overdue_orders:
            alerts.append({
                'type': 'danger',
                'title': 'Órdenes Vencidas',
                'message': f'{overdue_orders.count()} órdenes con fecha de entrega vencida',
                'count': overdue_orders.count(),
                'link': '/purchases/orders/?status=overdue'
            })
        
        # Proveedores con calificación baja
        low_rated_suppliers = self._get_low_rated_suppliers()
        if low_rated_suppliers:
            alerts.append({
                'type': 'warning',
                'title': 'Proveedores con Calificación Baja',
                'message': f'{low_rated_suppliers.count()} proveedores requieren evaluación',
                'count': low_rated_suppliers.count(),
                'link': '/purchases/suppliers/?rating=poor'
            })
        
        # Límites de gasto próximos
        spending_alerts = self._get_spending_alerts()
        if spending_alerts:
            alerts.extend(spending_alerts)
        
        return alerts
    
    def get_spending_trends(self, period='month', months=12):
        """Obtener tendencias de gastos"""
        from .models import PurchaseOrder
        
        end_date = self.today
        start_date = end_date - timedelta(days=months * 30)
        
        if period == 'month':
            trunc_func = TruncMonth
        elif period == 'week':
            trunc_func = TruncWeek
        else:
            trunc_func = TruncDay
        
        spending_data = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).annotate(
            period=trunc_func('order_date')
        ).values('period').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('period')
        
        return list(spending_data)
    
    def get_supplier_performance(self, limit=10):
        """Obtener rendimiento de proveedores"""
        from .models import Supplier, PurchaseOrder, SupplierRating
        
        suppliers = Supplier.objects.filter(
            empresa=self.empresa,
            is_active=True
        ).annotate(
            total_orders=Count('purchase_orders'),
            total_spent=Sum('purchase_orders__total_amount'),
            avg_rating=Avg('ratings__overall_score'),
            on_time_deliveries=Count(
                'purchase_orders',
                filter=Q(
                    purchase_orders__status__in=['partially_received', 'received'],
                    purchase_orders__last_receipt_date__lte=F('purchase_orders__expected_delivery_date')
                )
            )
        ).order_by('-total_spent')[:limit]
        
        return list(suppliers.values(
            'id', 'name', 'code', 'rating_class',
            'total_orders', 'total_spent', 'avg_rating', 'on_time_deliveries'
        ))
    
    def get_category_spending(self):
        """Obtener gastos por categoría"""
        from .models import PurchaseOrder
        
        category_spending = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__gte=self.month_start
        ).values(
            'lines__product_variant__product__category__name'
        ).annotate(
            total=Sum('lines__total_amount'),
            count=Count('id', distinct=True)
        ).order_by('-total')
        
        return list(category_spending)
    
    def get_delivery_performance_trends(self):
        """Obtener tendencias de rendimiento de entregas"""
        from .models import PurchaseOrder
        
        # Últimos 6 meses
        end_date = self.today
        start_date = end_date - timedelta(days=180)
        
        delivery_data = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).annotate(
            month=TruncMonth('order_date'),
            is_on_time=Case(
                When(last_receipt_date__lte=F('expected_delivery_date'), then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).values('month').annotate(
            total_orders=Count('id'),
            on_time_orders=Sum('is_on_time'),
            avg_delivery_time=Avg(
                ExtractDay(F('last_receipt_date') - F('order_date'))
            )
        ).order_by('month')
        
        return list(delivery_data)
    
    def get_request_approval_metrics(self):
        """Obtener métricas de aprobación de solicitudes"""
        from .models import PurchaseRequest
        
        approval_data = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            request_date__gte=self.month_start
        ).values('status').annotate(
            count=Count('id'),
            avg_amount=Avg('total_amount'),
            avg_processing_time=Avg(
                ExtractDay(F('approved_date') - F('request_date'))
            )
        )
        
        return list(approval_data)
    
    def get_cost_savings_analysis(self):
        """Análisis de ahorro de costos"""
        from .models import PurchaseQuotation, PurchaseOrder
        
        # Comparar cotizaciones vs órdenes
        savings_data = []
        
        quotations = PurchaseQuotation.objects.filter(
            empresa=self.empresa,
            status='approved',
            quotation_date__gte=self.month_start
        ).select_related('purchase_request')
        
        for quotation in quotations:
            if quotation.purchase_request and quotation.purchase_request.purchase_orders.exists():
                order = quotation.purchase_request.purchase_orders.first()
                savings = quotation.total_amount - order.total_amount
                savings_percentage = (savings / quotation.total_amount * 100) if quotation.total_amount > 0 else 0
                
                savings_data.append({
                    'request_number': quotation.purchase_request.request_number,
                    'quotation_amount': float(quotation.total_amount),
                    'order_amount': float(order.total_amount),
                    'savings': float(savings),
                    'savings_percentage': round(savings_percentage, 2),
                    'supplier': quotation.supplier.name
                })
        
        return savings_data
    
    # Métodos auxiliares
    def _calculate_approval_rate(self):
        """Calcular tasa de aprobación"""
        from .models import PurchaseRequest
        
        total_requests = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            request_date__gte=self.month_start
        ).count()
        
        approved_requests = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            status='approved',
            request_date__gte=self.month_start
        ).count()
        
        return round((approved_requests / total_requests * 100) if total_requests > 0 else 0, 2)
    
    def _calculate_avg_processing_time(self):
        """Calcular tiempo promedio de procesamiento"""
        from .models import PurchaseRequest
        
        avg_time = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            status='approved',
            approved_date__isnull=False,
            request_date__gte=self.month_start
        ).aggregate(
            avg_days=Avg(ExtractDay(F('approved_date') - F('request_date')))
        )['avg_days'] or 0
        
        return round(avg_time, 1)
    
    def _calculate_avg_order_value(self):
        """Calcular valor promedio de orden"""
        from .models import PurchaseOrder
        
        avg_value = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            order_date__gte=self.month_start
        ).aggregate(avg=Avg('total_amount'))['avg'] or 0
        
        return float(avg_value)
    
    def _calculate_conversion_rate(self):
        """Calcular tasa de conversión de solicitudes a órdenes"""
        from .models import PurchaseRequest
        
        total_approved = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            status='approved',
            request_date__gte=self.month_start
        ).count()
        
        converted = PurchaseRequest.objects.filter(
            empresa=self.empresa,
            status='approved',
            purchase_orders__isnull=False,
            request_date__gte=self.month_start
        ).distinct().count()
        
        return round((converted / total_approved * 100) if total_approved > 0 else 0, 2)
    
    def _calculate_avg_delivery_time(self):
        """Calcular tiempo promedio de entrega"""
        from .models import PurchaseOrder
        
        avg_time = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['partially_received', 'received'],
            last_receipt_date__isnull=False,
            order_date__gte=self.month_start
        ).aggregate(
            avg_days=Avg(ExtractDay(F('last_receipt_date') - F('order_date')))
        )['avg_days'] or 0
        
        return round(avg_time, 1)
    
    def _calculate_avg_quality_score(self):
        """Calcular puntuación promedio de calidad"""
        from .models import PurchaseReceipt
        
        avg_score = PurchaseReceipt.objects.filter(
            empresa=self.empresa,
            quality_score__isnull=False,
            receipt_date__gte=self.month_start
        ).aggregate(avg=Avg('quality_score'))['avg'] or 0
        
        return round(avg_score, 2)
    
    def _get_top_supplier(self):
        """Obtener proveedor con mayor gasto"""
        from .models import Supplier
        
        top_supplier = Supplier.objects.filter(
            empresa=self.empresa,
            is_active=True
        ).annotate(
            total_spent=Sum('purchase_orders__total_amount')
        ).order_by('-total_spent').first()
        
        if top_supplier:
            return {
                'name': top_supplier.name,
                'total_spent': float(top_supplier.total_spent or 0),
                'rating': top_supplier.rating_class
            }
        return None
    
    def _get_overdue_requests(self):
        """Obtener solicitudes vencidas"""
        from .models import PurchaseRequest
        
        return PurchaseRequest.objects.filter(
            empresa=self.empresa,
            status__in=['draft', 'pending_approval'],
            required_date__lt=self.today
        )
    
    def _get_overdue_orders(self):
        """Obtener órdenes vencidas"""
        from .models import PurchaseOrder
        
        return PurchaseOrder.objects.filter(
            empresa=self.empresa,
            status__in=['sent', 'confirmed'],
            expected_delivery_date__lt=self.today
        )
    
    def _get_low_rated_suppliers(self):
        """Obtener proveedores con calificación baja"""
        from .models import Supplier
        
        return Supplier.objects.filter(
            empresa=self.empresa,
            is_active=True,
            rating_class='poor'
        )
    
    def _get_spending_alerts(self):
        """Obtener alertas de gasto"""
        alerts = []
        
        # Obtener límites de la empresa
        daily_limit = getattr(self.empresa, 'daily_purchase_limit', Decimal('100000'))
        monthly_limit = getattr(self.empresa, 'monthly_purchase_limit', Decimal('2000000'))
        
        # Verificar límite diario
        from .models import PurchaseOrder
        daily_spending = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            order_date=self.today
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        if daily_spending > daily_limit * Decimal('0.8'):  # 80% del límite
            alerts.append({
                'type': 'warning',
                'title': 'Límite Diario Próximo',
                'message': f'Gasto diario: ${daily_spending:,.2f} / ${daily_limit:,.2f}',
                'percentage': float((daily_spending / daily_limit) * 100)
            })
        
        # Verificar límite mensual
        monthly_spending = PurchaseOrder.objects.filter(
            empresa=self.empresa,
            order_date__gte=self.month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        if monthly_spending > monthly_limit * Decimal('0.9'):  # 90% del límite
            alerts.append({
                'type': 'danger',
                'title': 'Límite Mensual Próximo',
                'message': f'Gasto mensual: ${monthly_spending:,.2f} / ${monthly_limit:,.2f}',
                'percentage': float((monthly_spending / monthly_limit) * 100)
            })
        
        return alerts


# Funciones de conveniencia para importaciones
def get_dashboard_metrics(empresa):
    """Obtener métricas del dashboard para una empresa"""
    service = PurchaseReportsService(empresa)
    return service.get_dashboard_metrics()


def get_spending_trends(empresa, period='month', months=12):
    """Obtener tendencias de gastos para una empresa"""
    service = PurchaseReportsService(empresa)
    return service.get_spending_trends(period, months)


def get_supplier_performance(empresa, limit=10):
    """Obtener rendimiento de proveedores para una empresa"""
    service = PurchaseReportsService(empresa)
    return service.get_supplier_performance(limit) 