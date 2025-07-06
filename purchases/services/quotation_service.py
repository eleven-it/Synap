from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import List, Dict, Any, Optional

from ..models import PurchaseQuotation, PurchaseQuotationLine, PurchaseRequest

User = get_user_model()


class QuotationService:
    """
    Servicio para gestionar cotizaciones de compra
    """
    
    def __init__(self):
        self.user = None
    
    def set_user(self, user: User):
        """Establece el usuario para las operaciones"""
        self.user = user
        return self
    
    def create_quotation(
        self,
        purchase_request: PurchaseRequest,
        supplier,
        valid_until,
        currency=None,
        exchange_rate: float = 1.0,
        payment_terms: str = "",
        delivery_terms: str = "",
        delivery_time: int = None,
        notes: str = "",
        lines_data: List[Dict] = None
    ) -> PurchaseQuotation:
        """
        Crea una nueva cotización de compra
        """
        with transaction.atomic():
            # Usar moneda de la solicitud si no se especifica
            if not currency:
                currency = purchase_request.currency
            
            quotation = PurchaseQuotation.objects.create(
                empresa=purchase_request.empresa,
                branch=purchase_request.branch,
                supplier=supplier,
                purchase_request=purchase_request,
                valid_until=valid_until,
                currency=currency,
                exchange_rate=exchange_rate,
                payment_terms=payment_terms,
                delivery_terms=delivery_terms,
                delivery_time=delivery_time,
                notes=notes,
                created_by=self.user
            )
            
            # Crear líneas de cotización
            if lines_data:
                for line_data in lines_data:
                    self._create_quotation_line(quotation, line_data)
            else:
                # Crear líneas basadas en la solicitud
                for request_line in purchase_request.lines.all():
                    self._create_quotation_line_from_request(quotation, request_line)
            
            # Calcular totales
            quotation.calculate_totals()
            
            return quotation
    
    def _create_quotation_line(
        self,
        quotation: PurchaseQuotation,
        line_data: Dict
    ) -> PurchaseQuotationLine:
        """Crea una línea de cotización"""
        from inventory.models import ProductVariant
        from core.models import UnitOfMeasure
        
        # Obtener el producto
        product_variant = ProductVariant.objects.get(id=line_data['product_variant_id'])
        
        # Obtener la unidad de medida
        uom = UnitOfMeasure.objects.get(id=line_data['unit_of_measure_id'])
        
        # Obtener línea de solicitud correspondiente
        request_line = quotation.purchase_request.lines.filter(
            product_variant=product_variant
        ).first()
        
        # Crear la línea
        line = PurchaseQuotationLine.objects.create(
            quotation=quotation,
            request_line=request_line,
            product_variant=product_variant,
            quantity=line_data['quantity'],
            unit_of_measure=uom,
            unit_price=line_data['unit_price'],
            discount_percentage=line_data.get('discount_percentage', 0),
            tax_percentage=line_data.get('tax_percentage', 0),
            description=line_data.get('description', ''),
            specifications=line_data.get('specifications', {}),
            delivery_time=line_data.get('delivery_time'),
            minimum_order_quantity=line_data.get('minimum_order_quantity')
        )
        
        return line
    
    def _create_quotation_line_from_request(
        self,
        quotation: PurchaseQuotation,
        request_line: 'PurchaseRequestLine'
    ) -> PurchaseQuotationLine:
        """Crea una línea de cotización basada en una línea de solicitud"""
        line = PurchaseQuotationLine.objects.create(
            quotation=quotation,
            request_line=request_line,
            product_variant=request_line.product_variant,
            quantity=request_line.quantity,
            unit_of_measure=request_line.unit_of_measure,
            description=request_line.description,
            specifications=request_line.specifications
        )
        
        return line
    
    def compare_quotations(
        self,
        purchase_request: PurchaseRequest,
        include_expired: bool = False
    ) -> Dict[str, Any]:
        """
        Compara todas las cotizaciones de una solicitud de compra
        """
        # Obtener cotizaciones
        quotations = PurchaseQuotation.objects.filter(purchase_request=purchase_request)
        
        if not include_expired:
            quotations = quotations.filter(valid_until__gte=timezone.now().date())
        
        quotations = quotations.order_by('total_amount')
        
        if not quotations.exists():
            return {
                'request': purchase_request,
                'quotations': [],
                'comparison': None,
                'recommendation': None
            }
        
        # Preparar datos de comparación
        comparison_data = []
        
        for quotation in quotations:
            # Calcular métricas adicionales
            delivery_urgency = quotation.get_delivery_urgency()
            total_base_currency = quotation.get_total_in_base_currency()
            
            comparison_data.append({
                'quotation': quotation,
                'supplier_name': quotation.supplier.name,
                'total_amount': quotation.total_amount,
                'total_base_currency': total_base_currency,
                'delivery_time': quotation.delivery_time,
                'delivery_urgency': delivery_urgency,
                'payment_terms': quotation.payment_terms,
                'valid_until': quotation.valid_until,
                'is_expired': quotation.is_expired(),
                'evaluation_score': quotation.evaluation_score,
                'status': quotation.status
            })
        
        # Análisis de comparación
        analysis = self._analyze_quotations(comparison_data)
        
        # Recomendación
        recommendation = self._generate_recommendation(comparison_data, analysis)
        
        return {
            'request': purchase_request,
            'quotations': comparison_data,
            'comparison': analysis,
            'recommendation': recommendation
        }
    
    def _analyze_quotations(self, quotations_data: List[Dict]) -> Dict[str, Any]:
        """Analiza las cotizaciones para generar métricas comparativas"""
        if not quotations_data:
            return {}
        
        # Estadísticas de precios
        prices = [q['total_base_currency'] for q in quotations_data]
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Análisis de entrega
        delivery_times = [q['delivery_time'] for q in quotations_data if q['delivery_time']]
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else None
        
        # Análisis de urgencia
        urgency_counts = {}
        for q in quotations_data:
            urgency = q['delivery_urgency']
            urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
        
        # Análisis de evaluación
        evaluated_quotations = [q for q in quotations_data if q['evaluation_score']]
        avg_evaluation = sum(q['evaluation_score'] for q in evaluated_quotations) / len(evaluated_quotations) if evaluated_quotations else None
        
        return {
            'price_analysis': {
                'min_price': min_price,
                'max_price': max_price,
                'avg_price': avg_price,
                'price_range': max_price - min_price,
                'price_variance': self._calculate_variance(prices)
            },
            'delivery_analysis': {
                'avg_delivery_time': avg_delivery_time,
                'urgency_distribution': urgency_counts
            },
            'evaluation_analysis': {
                'avg_evaluation': avg_evaluation,
                'evaluated_count': len(evaluated_quotations)
            },
            'supplier_count': len(quotations_data)
        }
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calcula la varianza de una lista de valores"""
        if len(values) < 2:
            return 0
        
        mean = sum(values) / len(values)
        squared_diff_sum = sum((x - mean) ** 2 for x in values)
        return squared_diff_sum / (len(values) - 1)
    
    def _generate_recommendation(
        self,
        quotations_data: List[Dict],
        analysis: Dict
    ) -> Dict[str, Any]:
        """Genera una recomendación basada en el análisis"""
        if not quotations_data:
            return {'type': 'no_quotations', 'message': _('No quotations available')}
        
        # Filtrar cotizaciones válidas
        valid_quotations = [q for q in quotations_data if not q['is_expired']]
        
        if not valid_quotations:
            return {'type': 'all_expired', 'message': _('All quotations have expired')}
        
        # Puntuación de cada cotización
        scored_quotations = []
        
        for quotation in valid_quotations:
            score = 0
            
            # Score por precio (40% del peso)
            price_score = self._calculate_price_score(quotation, analysis)
            score += price_score * 0.4
            
            # Score por entrega (30% del peso)
            delivery_score = self._calculate_delivery_score(quotation)
            score += delivery_score * 0.3
            
            # Score por evaluación (20% del peso)
            evaluation_score = self._calculate_evaluation_score(quotation)
            score += evaluation_score * 0.2
            
            # Score por términos de pago (10% del peso)
            payment_score = self._calculate_payment_score(quotation)
            score += payment_score * 0.1
            
            scored_quotations.append({
                **quotation,
                'recommendation_score': score
            })
        
        # Ordenar por score de recomendación
        scored_quotations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        best_quotation = scored_quotations[0]
        
        return {
            'type': 'recommendation',
            'best_quotation': best_quotation,
            'all_scores': scored_quotations,
            'reasoning': self._generate_reasoning(best_quotation, analysis)
        }
    
    def _calculate_price_score(self, quotation: Dict, analysis: Dict) -> float:
        """Calcula el score de precio (0-10)"""
        if analysis['price_analysis']['price_range'] == 0:
            return 10  # Todas las cotizaciones tienen el mismo precio
        
        # Score basado en qué tan cerca está del precio mínimo
        price = quotation['total_base_currency']
        min_price = analysis['price_analysis']['min_price']
        price_range = analysis['price_analysis']['price_range']
        
        if price == min_price:
            return 10
        else:
            # Score decrece linealmente con el precio
            price_diff = price - min_price
            score = 10 - (price_diff / price_range) * 5  # Máximo 5 puntos de penalización
            return max(0, score)
    
    def _calculate_delivery_score(self, quotation: Dict) -> float:
        """Calcula el score de entrega (0-10)"""
        urgency = quotation['delivery_urgency']
        delivery_time = quotation['delivery_time']
        
        urgency_scores = {
            'comfortable': 8,
            'normal': 7,
            'urgent': 5,
            'late': 2
        }
        
        base_score = urgency_scores.get(urgency, 5)
        
        # Ajustar por tiempo de entrega específico
        if delivery_time:
            if delivery_time <= 7:
                base_score += 1
            elif delivery_time > 30:
                base_score -= 1
        
        return max(0, min(10, base_score))
    
    def _calculate_evaluation_score(self, quotation: Dict) -> float:
        """Calcula el score de evaluación (0-10)"""
        evaluation_score = quotation.get('evaluation_score')
        
        if evaluation_score is None:
            return 5  # Score neutral si no hay evaluación
        
        return evaluation_score
    
    def _calculate_payment_score(self, quotation: Dict) -> float:
        """Calcula el score de términos de pago (0-10)"""
        payment_terms = quotation.get('payment_terms', '').lower()
        
        if 'net 30' in payment_terms or '30 days' in payment_terms:
            return 8
        elif 'net 60' in payment_terms or '60 days' in payment_terms:
            return 6
        elif 'net 90' in payment_terms or '90 days' in payment_terms:
            return 4
        elif 'immediate' in payment_terms or 'cash' in payment_terms:
            return 2
        else:
            return 5  # Score neutral
    
    def _generate_reasoning(self, quotation: Dict, analysis: Dict) -> str:
        """Genera el razonamiento para la recomendación"""
        supplier_name = quotation['supplier_name']
        total_amount = quotation['total_amount']
        
        reasoning_parts = []
        
        # Precio
        if quotation['total_base_currency'] == analysis['price_analysis']['min_price']:
            reasoning_parts.append(_("Best price among all quotations"))
        elif quotation['recommendation_score'] >= 8:
            reasoning_parts.append(_("Competitive pricing"))
        
        # Entrega
        urgency = quotation['delivery_urgency']
        if urgency == 'comfortable':
            reasoning_parts.append(_("Comfortable delivery timeline"))
        elif urgency == 'urgent':
            reasoning_parts.append(_("Fast delivery available"))
        
        # Evaluación
        if quotation.get('evaluation_score', 0) >= 8:
            reasoning_parts.append(_("Excellent supplier evaluation"))
        
        if not reasoning_parts:
            reasoning_parts.append(_("Balanced overall score"))
        
        return f"{supplier_name} ({total_amount}): {'; '.join(reasoning_parts)}"
    
    def select_quotation(
        self,
        quotation: PurchaseQuotation,
        selector: User,
        reason: str = ""
    ) -> Dict[str, Any]:
        """
        Selecciona una cotización como ganadora
        """
        with transaction.atomic():
            # Verificar que la cotización es válida
            if not quotation.is_valid():
                raise ValidationError(_("Cannot select an invalid quotation"))
            
            # Seleccionar la cotización
            quotation.select()
            
            # Actualizar notas
            if reason:
                quotation.evaluation_notes = f"Selected by {selector.username}. Reason: {reason}"
                quotation.save()
            
            return {
                'status': 'selected',
                'message': _('Quotation selected successfully'),
                'quotation': quotation
            }
    
    def evaluate_quotation(
        self,
        quotation: PurchaseQuotation,
        evaluator: User,
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
    ) -> Dict[str, Any]:
        """
        Evalúa una cotización
        """
        # Usar el servicio de proveedores para crear la evaluación
        from .supplier_service import SupplierService
        
        supplier_service = SupplierService().set_user(evaluator)
        
        # Crear evaluación del proveedor
        rating = supplier_service.update_supplier_rating(
            supplier=quotation.supplier,
            purchase_order=None,  # No hay orden aún
            quality_score=quality_score,
            delivery_score=delivery_score,
            communication_score=communication_score,
            price_score=price_score,
            service_score=service_score,
            quality_comments=quality_comments,
            delivery_comments=delivery_comments,
            communication_comments=communication_comments,
            price_comments=price_comments,
            service_comments=service_comments,
            general_comments=general_comments,
            recommendations=recommendations,
            would_recommend=would_recommend
        )
        
        # Actualizar la cotización con la evaluación
        quotation.evaluate(rating.overall_score, general_comments)
        
        return {
            'status': 'evaluated',
            'message': _('Quotation evaluated successfully'),
            'quotation': quotation,
            'rating': rating
        }
    
    def get_quotation_analytics(self, empresa, start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Obtiene análisis de cotizaciones para un período
        """
        if not start_date:
            start_date = timezone.now().date() - timezone.timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        # Obtener cotizaciones del período
        quotations = PurchaseQuotation.objects.filter(
            empresa=empresa,
            quotation_date__range=[start_date, end_date]
        )
        
        # Calcular métricas
        total_quotations = quotations.count()
        total_value = quotations.aggregate(total=models.Sum('total_amount'))['total'] or 0
        avg_value = total_value / total_quotations if total_quotations > 0 else 0
        
        # Estados de cotizaciones
        status_counts = quotations.values('status').annotate(count=models.Count('id'))
        
        # Proveedores más cotizados
        top_suppliers = quotations.values('supplier__name').annotate(
            count=models.Count('id'),
            total=models.Sum('total_amount')
        ).order_by('-count')[:10]
        
        # Análisis de precios
        price_analysis = {
            'min_price': quotations.aggregate(min=models.Min('total_amount'))['min'] or 0,
            'max_price': quotations.aggregate(max=models.Max('total_amount'))['max'] or 0,
            'avg_price': quotations.aggregate(avg=models.Avg('total_amount'))['avg'] or 0
        }
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': {
                'total_quotations': total_quotations,
                'total_value': total_value,
                'average_value': avg_value
            },
            'status_distribution': list(status_counts),
            'top_suppliers': list(top_suppliers),
            'price_analysis': price_analysis
        } 