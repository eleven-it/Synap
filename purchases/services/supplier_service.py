from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import List, Dict, Any, Optional

from ..models import Supplier, SupplierRating, SupplierPerformanceMetric

User = get_user_model()


class SupplierService:
    """
    Servicio para gestionar operaciones relacionadas con proveedores
    """
    
    def __init__(self):
        self.user = None
    
    def set_user(self, user: User):
        """Establece el usuario para las operaciones"""
        self.user = user
        return self
    
    def create_supplier(
        self,
        empresa,
        name: str,
        contact_person: str = "",
        email: str = "",
        phone: str = "",
        address: str = "",
        tax_id: str = "",
        payment_terms: str = "",
        delivery_terms: str = "",
        notes: str = "",
        categories: List[str] = None,
        rating_class: str = 'new'
    ) -> Supplier:
        """
        Crea un nuevo proveedor
        """
        with transaction.atomic():
            supplier = Supplier.objects.create(
                empresa=empresa,
                name=name,
                contact_person=contact_person,
                email=email,
                phone=phone,
                address=address,
                tax_id=tax_id,
                payment_terms=payment_terms,
                delivery_terms=delivery_terms,
                notes=notes,
                rating_class=rating_class,
                created_by=self.user
            )
            
            # Agregar categorías si se proporcionan
            if categories:
                supplier.categories.set(categories)
            
            return supplier
    
    def update_supplier_rating(
        self,
        supplier: Supplier,
        purchase_order,
        quality_score: int,
        delivery_score: int,
        communication_score: int,
        price_score: int,
        service_score: int,
        quality_comments: str = "",
        delivery_comments: str = "",
        communication_comments: str = "",
        price_comments: str = "",
        service_comments: str = "",
        general_comments: str = "",
        recommendations: str = "",
        would_recommend: bool = True
    ) -> SupplierRating:
        """
        Crea o actualiza una evaluación de proveedor
        """
        with transaction.atomic():
            # Verificar si ya existe una evaluación para esta orden
            rating, created = SupplierRating.objects.get_or_create(
                supplier=supplier,
                purchase_order=purchase_order,
                defaults={
                    'empresa': supplier.empresa,
                    'period_start': purchase_order.order_date,
                    'period_end': timezone.now().date(),
                    'evaluated_by': self.user
                }
            )
            
            # Actualizar scores
            rating.quality_score = quality_score
            rating.delivery_score = delivery_score
            rating.communication_score = communication_score
            rating.price_score = price_score
            rating.service_score = service_score
            
            # Actualizar comentarios
            rating.quality_comments = quality_comments
            rating.delivery_comments = delivery_comments
            rating.communication_comments = communication_comments
            rating.price_comments = price_comments
            rating.service_comments = service_comments
            rating.general_comments = general_comments
            rating.recommendations = recommendations
            rating.would_recommend = would_recommend
            
            # Guardar para calcular scores automáticamente
            rating.save()
            
            # Actualizar clasificación del proveedor
            self._update_supplier_classification(supplier)
            
            return rating
    
    def _update_supplier_classification(self, supplier: Supplier):
        """
        Actualiza la clasificación del proveedor basada en evaluaciones recientes
        """
        # Obtener evaluaciones de los últimos 12 meses
        one_year_ago = timezone.now().date() - timezone.timedelta(days=365)
        
        recent_ratings = SupplierRating.objects.filter(
            supplier=supplier,
            rating_date__gte=one_year_ago,
            status='approved'
        )
        
        if not recent_ratings.exists():
            return
        
        # Calcular promedio de scores
        avg_score = recent_ratings.aggregate(
            avg=models.Avg('overall_score')
        )['avg']
        
        # Determinar nueva clasificación
        if avg_score >= 9:
            new_class = 'excellent'
        elif avg_score >= 7:
            new_class = 'good'
        elif avg_score >= 5:
            new_class = 'fair'
        elif avg_score >= 3:
            new_class = 'poor'
        else:
            new_class = 'unacceptable'
        
        # Actualizar solo si cambió
        if supplier.rating_class != new_class:
            supplier.rating_class = new_class
            supplier.save(update_fields=['rating_class'])
    
    def get_supplier_analytics(self, supplier: Supplier, period_days: int = 365) -> Dict[str, Any]:
        """
        Obtiene análisis completo de un proveedor
        """
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=period_days)
        
        # Obtener métricas de rendimiento
        performance = self.get_supplier_performance(supplier, period_days)
        
        # Obtener evaluaciones recientes
        recent_ratings = SupplierRating.objects.filter(
            supplier=supplier,
            rating_date__range=[start_date, end_date]
        ).order_by('-rating_date')
        
        # Calcular tendencias
        trend_analysis = self._calculate_trend_analysis(supplier, start_date, end_date)
        
        # Obtener órdenes recientes
        from ..models import PurchaseOrder
        recent_orders = PurchaseOrder.objects.filter(
            supplier=supplier,
            order_date__range=[start_date, end_date]
        ).order_by('-order_date')[:10]
        
        return {
            'supplier_info': {
                'id': supplier.id,
                'name': supplier.name,
                'rating_class': supplier.rating_class,
                'contact_person': supplier.contact_person,
                'email': supplier.email,
                'phone': supplier.phone
            },
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': period_days
            },
            'performance': performance,
            'recent_ratings': list(recent_ratings.values(
                'rating_date', 'overall_score', 'rating_class', 'status'
            )),
            'trend_analysis': trend_analysis,
            'recent_orders': list(recent_orders.values(
                'order_number', 'order_date', 'total_amount', 'status'
            ))
        }
    
    def _calculate_trend_analysis(self, supplier: Supplier, start_date, end_date) -> Dict[str, Any]:
        """
        Calcula el análisis de tendencias del proveedor
        """
        # Dividir el período en trimestres
        from datetime import timedelta
        
        quarters = []
        current_date = start_date
        
        while current_date < end_date:
            quarter_end = min(current_date + timedelta(days=90), end_date)
            quarters.append({
                'start': current_date,
                'end': quarter_end
            })
            current_date = quarter_end
        
        # Calcular métricas por trimestre
        quarterly_metrics = []
        
        for quarter in quarters:
            # Obtener métricas del trimestre
            metric, created = SupplierPerformanceMetric.objects.get_or_create(
                supplier=supplier,
                period_start=quarter['start'],
                period_end=quarter['end'],
                defaults={'empresa': supplier.empresa}
            )
            
            if created:
                metric.calculate_metrics()
            
            quarterly_metrics.append({
                'period': f"{quarter['start']} - {quarter['end']}",
                'on_time_rate': metric.on_time_delivery_rate,
                'quality_rate': metric.quality_acceptance_rate,
                'total_orders': metric.total_orders,
                'total_spent': metric.total_spent
            })
        
        # Calcular tendencias
        if len(quarterly_metrics) >= 2:
            latest = quarterly_metrics[-1]
            previous = quarterly_metrics[-2]
            
            delivery_trend = latest['on_time_rate'] - previous['on_time_rate']
            quality_trend = latest['quality_rate'] - previous['quality_rate']
            orders_trend = latest['total_orders'] - previous['total_orders']
            spending_trend = latest['total_spent'] - previous['total_spent']
        else:
            delivery_trend = quality_trend = orders_trend = spending_trend = 0
        
        return {
            'quarterly_metrics': quarterly_metrics,
            'trends': {
                'delivery_trend': delivery_trend,
                'quality_trend': quality_trend,
                'orders_trend': orders_trend,
                'spending_trend': spending_trend
            }
        }
    
    def get_supplier_performance(self, supplier: Supplier, period_days: int = 90) -> Dict[str, Any]:
        """
        Obtiene métricas de rendimiento de un proveedor
        """
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
    
    def get_supplier_recommendations(self, empresa, category: str = None) -> List[Dict[str, Any]]:
        """
        Obtiene recomendaciones de proveedores basadas en rendimiento
        """
        # Obtener proveedores con mejor rendimiento
        suppliers = Supplier.objects.filter(empresa=empresa)
        
        if category:
            suppliers = suppliers.filter(categories__name=category)
        
        recommendations = []
        
        for supplier in suppliers:
            # Obtener métricas recientes
            performance = self.get_supplier_performance(supplier, 90)
            
            # Calcular score de recomendación
            delivery_score = performance['delivery_metrics']['delivery_score']
            quality_score = performance['quality_metrics']['quality_score']
            
            recommendation_score = (delivery_score + quality_score) / 2
            
            if recommendation_score >= 7:  # Solo recomendar proveedores con buen rendimiento
                recommendations.append({
                    'supplier': {
                        'id': supplier.id,
                        'name': supplier.name,
                        'rating_class': supplier.rating_class,
                        'contact_person': supplier.contact_person,
                        'email': supplier.email
                    },
                    'performance': performance,
                    'recommendation_score': recommendation_score
                })
        
        # Ordenar por score de recomendación
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return recommendations[:10]  # Top 10
    
    def export_supplier_data(self, supplier: Supplier, format: str = 'json') -> str:
        """
        Exporta datos del proveedor en diferentes formatos
        """
        import json
        import csv
        from io import StringIO
        
        # Obtener datos completos
        analytics = self.get_supplier_analytics(supplier)
        
        if format.lower() == 'json':
            return json.dumps(analytics, indent=2, default=str)
        
        elif format.lower() == 'csv':
            output = StringIO()
            writer = csv.writer(output)
            
            # Escribir datos básicos
            writer.writerow(['Supplier Information'])
            writer.writerow(['Name', supplier.name])
            writer.writerow(['Contact Person', supplier.contact_person])
            writer.writerow(['Email', supplier.email])
            writer.writerow(['Phone', supplier.phone])
            writer.writerow(['Rating Class', supplier.rating_class])
            writer.writerow([])
            
            # Escribir métricas de rendimiento
            writer.writerow(['Performance Metrics'])
            performance = analytics['performance']
            
            writer.writerow(['Delivery Metrics'])
            delivery = performance['delivery_metrics']
            writer.writerow(['Total Orders', delivery['total_orders']])
            writer.writerow(['On-Time Deliveries', delivery['on_time_deliveries']])
            writer.writerow(['On-Time Rate', f"{delivery['on_time_rate']}%"])
            writer.writerow(['Delivery Score', delivery['delivery_score']])
            writer.writerow([])
            
            writer.writerow(['Quality Metrics'])
            quality = performance['quality_metrics']
            writer.writerow(['Total Receipts', quality['total_receipts']])
            writer.writerow(['Approved Receipts', quality['approved_receipts']])
            writer.writerow(['Acceptance Rate', f"{quality['acceptance_rate']}%"])
            writer.writerow(['Quality Score', quality['quality_score']])
            
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported format: {format}") 