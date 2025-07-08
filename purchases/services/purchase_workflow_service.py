from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from ..models import (
    PurchaseRequest, PurchaseOrder, PurchaseQuotation, 
    PurchaseDocumentStates, ApprovalRecord
)


class PurchaseWorkflowService:
    """Servicio para manejar el workflow unificado de documentos de compra"""
    
    def __init__(self, user=None):
        self.user = user
    
    def set_user(self, user):
        """Establecer usuario para el servicio"""
        self.user = user
        return self
    
    def validate_transition(self, document, new_status):
        """Validar si la transición de estado es válida"""
        current_status = document.status
        valid_transitions = PurchaseDocumentStates.VALID_TRANSITIONS.get(current_status, [])
        
        if new_status not in valid_transitions:
            raise ValidationError(
                _('Invalid state transition from {} to {}').format(
                    current_status, new_status
                )
            )
    
    def submit_document(self, document, reason=None):
        """Enviar documento para aprobación"""
        if not isinstance(document, PurchaseRequest):
            raise ValidationError(_('Only purchase requests can be submitted for approval'))
        
        self.validate_transition(document, PurchaseDocumentStates.SUBMITTED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.SUBMITTED
            document.save()
            
            # Crear log de aprobación
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=self.user,
                action='submitted',
                reason=reason or _('Document submitted for approval')
            )
        
        return document
    
    def approve_document(self, document, reason=None):
        """Aprobar documento"""
        if not isinstance(document, PurchaseRequest):
            raise ValidationError(_('Only purchase requests can be approved'))
        
        self.validate_transition(document, PurchaseDocumentStates.APPROVED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.APPROVED
            document.approved_by = self.user
            document.approved_date = timezone.now().date()
            document.save()
            
            # Crear log de aprobación
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=self.user,
                action='approved',
                reason=reason or _('Document approved')
            )
        
        return document
    
    def reject_document(self, document, reason=None):
        """Rechazar documento"""
        if not isinstance(document, PurchaseRequest):
            raise ValidationError(_('Only purchase requests can be rejected'))
        
        self.validate_transition(document, PurchaseDocumentStates.REJECTED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.REJECTED
            document.approved_by = self.user
            document.rejection_reason = reason or ''
            document.save()
            
            # Crear log de rechazo
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=self.user,
                action='rejected',
                reason=reason or _('Document rejected')
            )
        
        return document
    
    def request_quotation(self, document, reason=None):
        """Solicitar cotización"""
        if not isinstance(document, PurchaseRequest):
            raise ValidationError(_('Only purchase requests can request quotations'))
        
        self.validate_transition(document, PurchaseDocumentStates.QUOTATION_REQUESTED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.QUOTATION_REQUESTED
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=self.user,
                action='quotation_requested',
                reason=reason or _('Quotation requested')
            )
        
        return document
    
    def create_order_from_request(self, request_document, supplier, expected_delivery_date=None, **kwargs):
        """Crear orden de compra desde solicitud"""
        if not isinstance(request_document, PurchaseRequest):
            raise ValidationError(_('Source document must be a purchase request'))
        
        if request_document.status != PurchaseDocumentStates.APPROVED:
            raise ValidationError(_('Only approved requests can be converted to orders'))
        
        with transaction.atomic():
            # Crear orden de compra
            order = PurchaseOrder.objects.create(
                empresa=request_document.empresa,
                branch=request_document.branch,
                supplier=supplier,
                purchase_request=request_document,
                expected_delivery_date=expected_delivery_date or request_document.required_date,
                currency=request_document.currency,
                payment_terms=kwargs.get('payment_terms', ''),
                delivery_terms=kwargs.get('delivery_terms', ''),
                notes=kwargs.get('notes', ''),
                created_by=self.user,
                status=PurchaseDocumentStates.ORDER_CREATED
            )
            
            # Crear líneas de orden desde líneas de solicitud
            for request_line in request_document.lines.all():
                from ..models import PurchaseOrderLine
                PurchaseOrderLine.objects.create(
                    purchase_order=order,
                    request_line=request_line,
                    product_variant=request_line.product_variant,
                    quantity=request_line.quantity,
                    unit_of_measure=request_line.unit_of_measure,
                    unit_price=request_line.estimated_unit_price or 0,
                    status='pending'
                )
            
            # Marcar solicitud como convertida
            request_document.status = 'converted'
            request_document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=order,
                user=self.user,
                action='created',
                reason=_('Order created from request')
            )
        
        return order
    
    def send_order(self, document, reason=None):
        """Enviar orden al proveedor"""
        if not isinstance(document, PurchaseOrder):
            raise ValidationError(_('Only purchase orders can be sent'))
        
        self.validate_transition(document, PurchaseDocumentStates.ORDER_SENT)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.ORDER_SENT
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=self.user,
                action='sent',
                reason=reason or _('Order sent to supplier')
            )
        
        return document
    
    def confirm_order(self, document, reason=None):
        """Confirmar orden por proveedor"""
        if not isinstance(document, PurchaseOrder):
            raise ValidationError(_('Only purchase orders can be confirmed'))
        
        self.validate_transition(document, PurchaseDocumentStates.ORDER_CONFIRMED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.ORDER_CONFIRMED
            document.confirmed_by = self.user
            document.confirmed_date = timezone.now().date()
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=self.user,
                action='confirmed',
                reason=reason or _('Order confirmed by supplier')
            )
        
        return document
    
    def mark_partially_received(self, document, reason=None):
        """Marcar orden como parcialmente recibida"""
        if not isinstance(document, PurchaseOrder):
            raise ValidationError(_('Only purchase orders can be marked as received'))
        
        self.validate_transition(document, PurchaseDocumentStates.PARTIALLY_RECEIVED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.PARTIALLY_RECEIVED
            if not document.first_receipt_date:
                document.first_receipt_date = timezone.now().date()
            document.last_receipt_date = timezone.now().date()
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=self.user,
                action='partially_received',
                reason=reason or _('Order partially received')
            )
        
        return document
    
    def mark_fully_received(self, document, reason=None):
        """Marcar orden como completamente recibida"""
        if not isinstance(document, PurchaseOrder):
            raise ValidationError(_('Only purchase orders can be marked as received'))
        
        self.validate_transition(document, PurchaseDocumentStates.FULLY_RECEIVED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.FULLY_RECEIVED
            if not document.first_receipt_date:
                document.first_receipt_date = timezone.now().date()
            document.last_receipt_date = timezone.now().date()
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=self.user,
                action='fully_received',
                reason=reason or _('Order fully received')
            )
        
        return document
    
    def mark_invoiced(self, document, reason=None):
        """Marcar orden como facturada"""
        if not isinstance(document, PurchaseOrder):
            raise ValidationError(_('Only purchase orders can be marked as invoiced'))
        
        self.validate_transition(document, PurchaseDocumentStates.INVOICED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.INVOICED
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=self.user,
                action='invoiced',
                reason=reason or _('Order invoiced')
            )
        
        return document
    
    def mark_paid(self, document, reason=None):
        """Marcar orden como pagada"""
        if not isinstance(document, PurchaseOrder):
            raise ValidationError(_('Only purchase orders can be marked as paid'))
        
        self.validate_transition(document, PurchaseDocumentStates.PAID)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.PAID
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=self.user,
                action='paid',
                reason=reason or _('Order paid')
            )
        
        return document
    
    def mark_completed(self, document, reason=None):
        """Marcar orden como completada"""
        if not isinstance(document, PurchaseOrder):
            raise ValidationError(_('Only purchase orders can be marked as completed'))
        
        self.validate_transition(document, PurchaseDocumentStates.COMPLETED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.COMPLETED
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=self.user,
                action='completed',
                reason=reason or _('Order completed')
            )
        
        return document
    
    def cancel_document(self, document, reason=None):
        """Cancelar documento"""
        if document.status in [PurchaseDocumentStates.CANCELLED, PurchaseDocumentStates.COMPLETED, PurchaseDocumentStates.REJECTED]:
            raise ValidationError(_('Document cannot be cancelled in current status'))
        
        self.validate_transition(document, PurchaseDocumentStates.CANCELLED)
        
        with transaction.atomic():
            document.status = PurchaseDocumentStates.CANCELLED
            document.save()
            
            # Crear log
            if isinstance(document, PurchaseRequest):
                ApprovalRecord.objects.create(
                    purchase_request=document,
                    user=self.user,
                    action='cancelled',
                    reason=reason or _('Document cancelled')
                )
            else:
                ApprovalRecord.objects.create(
                    purchase_order=document,
                    user=self.user,
                    action='cancelled',
                    reason=reason or _('Document cancelled')
                )
        
        return document
    
    def duplicate_document(self, document):
        """Duplicar documento"""
        with transaction.atomic():
            if isinstance(document, PurchaseRequest):
                # Duplicar solicitud
                new_request = PurchaseRequest.objects.create(
                    empresa=document.empresa,
                    branch=document.branch,
                    title=f"{document.title} (Copy)",
                    description=document.description,
                    priority=document.priority,
                    required_date=document.required_date,
                    currency=document.currency,
                    budget_amount=document.budget_amount,
                    delivery_location=document.delivery_location,
                    origin_type=document.origin_type,
                    origin_reference=document.origin_reference,
                    requested_by=self.user,
                    notes=document.notes,
                    status=PurchaseDocumentStates.DRAFT
                )
                
                # Duplicar líneas
                for line in document.lines.all():
                    from ..models import PurchaseRequestLine
                    PurchaseRequestLine.objects.create(
                        purchase_request=new_request,
                        product_variant=line.product_variant,
                        quantity=line.quantity,
                        unit_of_measure=line.unit_of_measure,
                        estimated_unit_price=line.estimated_unit_price,
                        currency=line.currency,
                        description=line.description,
                        specifications=line.specifications,
                        status='pending'
                    )
                
                return new_request
            
            else:
                # Duplicar orden
                new_order = PurchaseOrder.objects.create(
                    empresa=document.empresa,
                    branch=document.branch,
                    supplier=document.supplier,
                    expected_delivery_date=document.expected_delivery_date,
                    currency=document.currency,
                    exchange_rate=document.exchange_rate,
                    payment_terms=document.payment_terms,
                    delivery_terms=document.delivery_terms,
                    delivery_address=document.delivery_address,
                    notes=document.notes,
                    supplier_notes=document.supplier_notes,
                    created_by=self.user,
                    status=PurchaseDocumentStates.DRAFT
                )
                
                # Duplicar líneas
                for line in document.lines.all():
                    from ..models import PurchaseOrderLine
                    PurchaseOrderLine.objects.create(
                        purchase_order=new_order,
                        product_variant=line.product_variant,
                        quantity=line.quantity,
                        unit_of_measure=line.unit_of_measure,
                        unit_price=line.unit_price,
                        discount_percentage=line.discount_percentage,
                        tax_percentage=line.tax_percentage,
                        shipping_amount=line.shipping_amount,
                        description=line.description,
                        specifications=line.specifications,
                        status='pending'
                    )
                
                return new_order 