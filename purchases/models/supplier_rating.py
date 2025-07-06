from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from core.models import Empresa
from .supplier import Supplier
from .purchase_order import PurchaseOrder
from django.conf import settings

User = get_user_model()


class SupplierRating(models.Model):
    """
    Modelo para gestionar evaluaciones y ratings de proveedores
    Permite evaluar múltiples aspectos del desempeño del proveedor
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='supplier_ratings', verbose_name=_('Company'))
    
    # Información básica
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='ratings', verbose_name=_("Supplier"))
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='supplier_ratings', verbose_name=_("Purchase Order"))
    
    # Fecha de evaluación
    rating_date = models.DateField(_("Rating Date"), auto_now_add=True)
    period_start = models.DateField(_("Period Start"), help_text=_("Start date of the evaluation period"))
    period_end = models.DateField(_("Period End"), help_text=_("End date of the evaluation period"))
    
    # Scores por categoría (1-10)
    quality_score = models.PositiveIntegerField(_("Quality Score"), validators=[MinValueValidator(1), MaxValueValidator(10)],
                                              help_text=_("Product quality score from 1 to 10"))
    delivery_score = models.PositiveIntegerField(_("Delivery Score"), validators=[MinValueValidator(1), MaxValueValidator(10)],
                                               help_text=_("Delivery performance score from 1 to 10"))
    communication_score = models.PositiveIntegerField(_("Communication Score"), validators=[MinValueValidator(1), MaxValueValidator(10)],
                                                     help_text=_("Communication effectiveness score from 1 to 10"))
    price_score = models.PositiveIntegerField(_("Price Score"), validators=[MinValueValidator(1), MaxValueValidator(10)],
                                            help_text=_("Price competitiveness score from 1 to 10"))
    service_score = models.PositiveIntegerField(_("Service Score"), validators=[MinValueValidator(1), MaxValueValidator(10)],
                                              help_text=_("Customer service score from 1 to 10"))
    
    # Score general
    overall_score = models.DecimalField(_("Overall Score"), max_digits=3, decimal_places=1, validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    # Clasificación
    rating_class = models.CharField(_("Rating Class"), max_length=20, choices=[
        ('excellent', _('Excellent (9-10)')),
        ('good', _('Good (7-8)')),
        ('fair', _('Fair (5-6)')),
        ('poor', _('Poor (3-4)')),
        ('unacceptable', _('Unacceptable (1-2)')),
    ])
    
    # Comentarios detallados
    quality_comments = models.TextField(_("Quality Comments"), blank=True)
    delivery_comments = models.TextField(_("Delivery Comments"), blank=True)
    communication_comments = models.TextField(_("Communication Comments"), blank=True)
    price_comments = models.TextField(_("Price Comments"), blank=True)
    service_comments = models.TextField(_("Service Comments"), blank=True)
    general_comments = models.TextField(_("General Comments"), blank=True)
    
    # Recomendaciones
    recommendations = models.TextField(_("Recommendations"), blank=True, help_text=_("Recommendations for improvement"))
    would_recommend = models.BooleanField(_("Would Recommend"), default=True, help_text=_("Would you recommend this supplier?"))
    
    # Estado de la evaluación
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('reviewed', _('Reviewed')),
        ('approved', _('Approved')),
    ], default='draft')
    
    # Usuarios involucrados
    evaluated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='evaluated_suppliers', verbose_name=_("Evaluated By"))
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_supplier_ratings', verbose_name=_("Reviewed By"))
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Supplier Rating")
        verbose_name_plural = _("Supplier Ratings")
        ordering = ['-rating_date', '-created_at']
        unique_together = [['supplier', 'purchase_order']]
        indexes = [
            models.Index(fields=['empresa', 'supplier']),
            models.Index(fields=['supplier', 'rating_date']),
            models.Index(fields=['overall_score']),
            models.Index(fields=['rating_class']),
        ]
    
    def __str__(self):
        return f"{self.supplier.name} - {self.rating_date} ({self.overall_score}/10)"
    
    def save(self, *args, **kwargs):
        """Calcula automáticamente el score general y la clasificación"""
        self._calculate_overall_score()
        self._determine_rating_class()
        super().save(*args, **kwargs)
    
    def _calculate_overall_score(self):
        """Calcula el score general basado en los scores individuales"""
        scores = [
            self.quality_score,
            self.delivery_score,
            self.communication_score,
            self.price_score,
            self.service_score
        ]
        
        # Promedio ponderado (calidad y entrega tienen más peso)
        weights = [0.25, 0.25, 0.15, 0.20, 0.15]  # Debe sumar 1.0
        
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        self.overall_score = round(weighted_sum, 1)
    
    def _determine_rating_class(self):
        """Determina la clasificación basada en el score general"""
        score = self.overall_score
        
        if score >= 9:
            self.rating_class = 'excellent'
        elif score >= 7:
            self.rating_class = 'good'
        elif score >= 5:
            self.rating_class = 'fair'
        elif score >= 3:
            self.rating_class = 'poor'
        else:
            self.rating_class = 'unacceptable'
    
    def get_score_breakdown(self):
        """Retorna el desglose de scores en formato de diccionario"""
        return {
            'quality': {
                'score': self.quality_score,
                'comments': self.quality_comments,
                'weight': 0.25
            },
            'delivery': {
                'score': self.delivery_score,
                'comments': self.delivery_comments,
                'weight': 0.25
            },
            'communication': {
                'score': self.communication_score,
                'comments': self.communication_comments,
                'weight': 0.15
            },
            'price': {
                'score': self.price_score,
                'comments': self.price_comments,
                'weight': 0.20
            },
            'service': {
                'score': self.service_score,
                'comments': self.service_comments,
                'weight': 0.15
            }
        }
    
    def get_rating_color(self):
        """Retorna el color CSS para el rating"""
        colors = {
            'excellent': 'text-green-600',
            'good': 'text-blue-600',
            'fair': 'text-yellow-600',
            'poor': 'text-orange-600',
            'unacceptable': 'text-red-600'
        }
        return colors.get(self.rating_class, 'text-gray-600')
    
    def get_rating_icon(self):
        """Retorna el ícono para el rating"""
        icons = {
            'excellent': '⭐',
            'good': '👍',
            'fair': '😐',
            'poor': '👎',
            'unacceptable': '❌'
        }
        return icons.get(self.rating_class, '❓')
    
    def submit(self, user):
        """Envía la evaluación para revisión"""
        self.status = 'submitted'
        self.evaluated_by = user
        self.save()
    
    def review(self, user, approved=True):
        """Revisa la evaluación"""
        if approved:
            self.status = 'approved'
        else:
            self.status = 'reviewed'
        
        self.reviewed_by = user
        self.save()
    
    def get_trend_analysis(self):
        """Analiza la tendencia del proveedor comparando con evaluaciones anteriores"""
        previous_ratings = SupplierRating.objects.filter(
            supplier=self.supplier,
            rating_date__lt=self.rating_date
        ).order_by('-rating_date')[:5]
        
        if not previous_ratings:
            return {'trend': 'new', 'change': 0}
        
        avg_previous = sum(r.overall_score for r in previous_ratings) / len(previous_ratings)
        change = self.overall_score - avg_previous
        
        if change > 1:
            trend = 'improving'
        elif change < -1:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change': round(change, 1),
            'previous_average': round(avg_previous, 1)
        }
    
    @property
    def is_positive_rating(self):
        """Verifica si es una evaluación positiva"""
        return self.overall_score >= 7 and self.would_recommend
    
    @property
    def needs_attention(self):
        """Verifica si el proveedor necesita atención"""
        return self.overall_score < 5 or not self.would_recommend


class SupplierPerformanceMetric(models.Model):
    """
    Modelo para métricas de rendimiento del proveedor
    Calcula automáticamente métricas basadas en órdenes y recepciones
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='supplier_metrics', verbose_name=_('Company'))
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='performance_metrics', verbose_name=_("Supplier"))
    
    # Período de análisis
    period_start = models.DateField(_("Period Start"))
    period_end = models.DateField(_("Period End"))
    
    # Métricas de entrega
    total_orders = models.PositiveIntegerField(_("Total Orders"), default=0)
    on_time_deliveries = models.PositiveIntegerField(_("On-Time Deliveries"), default=0)
    late_deliveries = models.PositiveIntegerField(_("Late Deliveries"), default=0)
    early_deliveries = models.PositiveIntegerField(_("Early Deliveries"), default=0)
    
    # Métricas de calidad
    total_receipts = models.PositiveIntegerField(_("Total Receipts"), default=0)
    approved_receipts = models.PositiveIntegerField(_("Approved Receipts"), default=0)
    rejected_receipts = models.PositiveIntegerField(_("Rejected Receipts"), default=0)
    
    # Métricas financieras
    total_spent = models.DecimalField(_("Total Spent"), max_digits=15, decimal_places=2, default=0)
    average_order_value = models.DecimalField(_("Average Order Value"), max_digits=15, decimal_places=2, default=0)
    
    # Cálculos automáticos
    on_time_delivery_rate = models.DecimalField(_("On-Time Delivery Rate (%)"), max_digits=5, decimal_places=2, default=0)
    quality_acceptance_rate = models.DecimalField(_("Quality Acceptance Rate (%)"), max_digits=5, decimal_places=2, default=0)
    
    # Auditoría
    calculated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Supplier Performance Metric")
        verbose_name_plural = _("Supplier Performance Metrics")
        ordering = ['-period_end', '-calculated_at']
        unique_together = [['supplier', 'period_start', 'period_end']]
        indexes = [
            models.Index(fields=['empresa', 'supplier']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.supplier.name} - {self.period_start} to {self.period_end}"
    
    def calculate_metrics(self):
        """Calcula todas las métricas basadas en datos reales"""
        from django.utils import timezone
        from django.db.models import Q, Count, Sum, Avg
        
        # Obtener órdenes del período
        orders = PurchaseOrder.objects.filter(
            supplier=self.supplier,
            order_date__range=[self.period_start, self.period_end]
        )
        
        # Métricas de entrega
        self.total_orders = orders.count()
        
        # Calcular entregas a tiempo, tardías y tempranas
        on_time = 0
        late = 0
        early = 0
        
        for order in orders:
            if order.status in ['received', 'partially_received']:
                if order.last_receipt_date:
                    if order.last_receipt_date <= order.expected_delivery_date:
                        on_time += 1
                    elif order.last_receipt_date > order.expected_delivery_date:
                        late += 1
                    else:
                        early += 1
        
        self.on_time_deliveries = on_time
        self.late_deliveries = late
        self.early_deliveries = early
        
        # Calcular tasa de entrega a tiempo
        total_delivered = on_time + late + early
        if total_delivered > 0:
            self.on_time_delivery_rate = (on_time / total_delivered) * 100
        else:
            self.on_time_delivery_rate = 0
        
        # Métricas de calidad
        receipts = PurchaseReceipt.objects.filter(
            purchase_order_line__purchase_order__supplier=self.supplier,
            receipt_date__range=[self.period_start, self.period_end]
        )
        
        self.total_receipts = receipts.count()
        self.approved_receipts = receipts.filter(status='approved').count()
        self.rejected_receipts = receipts.filter(status='rejected').count()
        
        # Calcular tasa de aceptación de calidad
        if self.total_receipts > 0:
            self.quality_acceptance_rate = (self.approved_receipts / self.total_receipts) * 100
        else:
            self.quality_acceptance_rate = 0
        
        # Métricas financieras
        self.total_spent = orders.aggregate(total=Sum('total_amount'))['total'] or 0
        
        if self.total_orders > 0:
            self.average_order_value = self.total_spent / self.total_orders
        else:
            self.average_order_value = 0
        
        self.save()
    
    @property
    def delivery_performance_score(self):
        """Calcula un score de rendimiento de entrega (1-10)"""
        if self.total_orders == 0:
            return 0
        
        # Score basado en tasa de entrega a tiempo
        on_time_rate = self.on_time_delivery_rate / 100
        
        if on_time_rate >= 0.95:
            return 10
        elif on_time_rate >= 0.90:
            return 9
        elif on_time_rate >= 0.85:
            return 8
        elif on_time_rate >= 0.80:
            return 7
        elif on_time_rate >= 0.75:
            return 6
        elif on_time_rate >= 0.70:
            return 5
        elif on_time_rate >= 0.60:
            return 4
        elif on_time_rate >= 0.50:
            return 3
        elif on_time_rate >= 0.40:
            return 2
        else:
            return 1
    
    @property
    def quality_performance_score(self):
        """Calcula un score de rendimiento de calidad (1-10)"""
        if self.total_receipts == 0:
            return 0
        
        # Score basado en tasa de aceptación de calidad
        acceptance_rate = self.quality_acceptance_rate / 100
        
        if acceptance_rate >= 0.98:
            return 10
        elif acceptance_rate >= 0.95:
            return 9
        elif acceptance_rate >= 0.90:
            return 8
        elif acceptance_rate >= 0.85:
            return 7
        elif acceptance_rate >= 0.80:
            return 6
        elif acceptance_rate >= 0.75:
            return 5
        elif acceptance_rate >= 0.70:
            return 4
        elif acceptance_rate >= 0.60:
            return 3
        elif acceptance_rate >= 0.50:
            return 2
        else:
            return 1 