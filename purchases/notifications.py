from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class PurchaseNotificationService:
    """Servicio para enviar notificaciones relacionadas con compras"""
    
    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
    
    def send_request_created_notification(self, request):
        """Notificar creación de solicitud de compra"""
        subject = _('New Purchase Request Created: {request_number}').format(
            request_number=request.request_number
        )
        
        context = {
            'request': request,
            'requested_by': request.requested_by,
            'total_amount': request.total_amount,
            'currency': request.currency,
            'items_count': request.lines.count(),
        }
        
        # Notificar al solicitante
        self._send_email_to_user(
            user=request.requested_by,
            subject=subject,
            template='purchases/emails/request_created.html',
            context=context
        )
        
        # Notificar a aprobadores si hay flujo de aprobación
        if request.approval_workflow:
            self._notify_approvers(request, subject, context)
    
    def send_request_submitted_notification(self, request):
        """Notificar envío de solicitud para aprobación"""
        subject = _('Purchase Request Submitted for Approval: {request_number}').format(
            request_number=request.request_number
        )
        
        context = {
            'request': request,
            'requested_by': request.requested_by,
            'total_amount': request.total_amount,
            'currency': request.currency,
        }
        
        # Notificar a aprobadores
        self._notify_approvers(request, subject, context)
        
        # Notificar al solicitante
        self._send_email_to_user(
            user=request.requested_by,
            subject=subject,
            template='purchases/emails/request_submitted.html',
            context=context
        )
    
    def send_request_approved_notification(self, request, approved_by):
        """Notificar aprobación de solicitud"""
        subject = _('Purchase Request Approved: {request_number}').format(
            request_number=request.request_number
        )
        
        context = {
            'request': request,
            'approved_by': approved_by,
            'approved_date': request.approved_date,
            'total_amount': request.total_amount,
            'currency': request.currency,
        }
        
        # Notificar al solicitante
        self._send_email_to_user(
            user=request.requested_by,
            subject=subject,
            template='purchases/emails/request_approved.html',
            context=context
        )
        
        # Notificar a otros aprobadores del flujo
        self._notify_other_approvers(request, subject, context, approved_by)
    
    def send_request_rejected_notification(self, request, rejected_by, reason):
        """Notificar rechazo de solicitud"""
        subject = _('Purchase Request Rejected: {request_number}').format(
            request_number=request.request_number
        )
        
        context = {
            'request': request,
            'rejected_by': rejected_by,
            'rejection_reason': reason,
            'total_amount': request.total_amount,
            'currency': request.currency,
        }
        
        # Notificar al solicitante
        self._send_email_to_user(
            user=request.requested_by,
            subject=subject,
            template='purchases/emails/request_rejected.html',
            context=context
        )
    
    def send_quotation_received_notification(self, quotation):
        """Notificar recepción de cotización"""
        subject = _('Quotation Received: {quotation_number}').format(
            quotation_number=quotation.quotation_number
        )
        
        context = {
            'quotation': quotation,
            'supplier': quotation.supplier,
            'request': quotation.purchase_request,
            'total_amount': quotation.total_amount,
            'currency': quotation.currency,
        }
        
        # Notificar al solicitante
        self._send_email_to_user(
            user=quotation.purchase_request.requested_by,
            subject=subject,
            template='purchases/emails/quotation_received.html',
            context=context
        )
    
    def send_order_created_notification(self, order):
        """Notificar creación de orden de compra"""
        subject = _('Purchase Order Created: {order_number}').format(
            order_number=order.order_number
        )
        
        context = {
            'order': order,
            'supplier': order.supplier,
            'request': order.purchase_request,
            'total_amount': order.total_amount,
            'currency': order.currency,
        }
        
        # Notificar al solicitante
        self._send_email_to_user(
            user=order.created_by,
            subject=subject,
            template='purchases/emails/order_created.html',
            context=context
        )
        
        # Notificar al proveedor (si tiene email)
        if order.supplier.email:
            self._send_email_to_supplier(
                supplier=order.supplier,
                subject=subject,
                template='purchases/emails/order_created_supplier.html',
                context=context
            )
    
    def send_order_sent_notification(self, order):
        """Notificar envío de orden al proveedor"""
        subject = _('Purchase Order Sent to Supplier: {order_number}').format(
            order_number=order.order_number
        )
        
        context = {
            'order': order,
            'supplier': order.supplier,
            'expected_delivery': order.expected_delivery_date,
            'total_amount': order.total_amount,
            'currency': order.currency,
        }
        
        # Notificar al proveedor
        if order.supplier.email:
            self._send_email_to_supplier(
                supplier=order.supplier,
                subject=subject,
                template='purchases/emails/order_sent_supplier.html',
                context=context
            )
        
        # Notificar al creador de la orden
        self._send_email_to_user(
            user=order.created_by,
            subject=subject,
            template='purchases/emails/order_sent.html',
            context=context
        )
    
    def send_order_confirmed_notification(self, order):
        """Notificar confirmación de orden"""
        subject = _('Purchase Order Confirmed: {order_number}').format(
            order_number=order.order_number
        )
        
        context = {
            'order': order,
            'supplier': order.supplier,
            'confirmed_date': order.confirmed_date,
            'total_amount': order.total_amount,
            'currency': order.currency,
        }
        
        # Notificar al creador de la orden
        self._send_email_to_user(
            user=order.created_by,
            subject=subject,
            template='purchases/emails/order_confirmed.html',
            context=context
        )
    
    def send_receipt_created_notification(self, receipt):
        """Notificar creación de recepción"""
        subject = _('Purchase Receipt Created: {receipt_number}').format(
            receipt_number=receipt.receipt_number
        )
        
        context = {
            'receipt': receipt,
            'order': receipt.purchase_order_line.purchase_order,
            'supplier': receipt.purchase_order_line.purchase_order.supplier,
            'product': receipt.purchase_order_line.product_variant,
            'quantity': receipt.quantity,
        }
        
        # Notificar al receptor
        self._send_email_to_user(
            user=receipt.received_by,
            subject=subject,
            template='purchases/emails/receipt_created.html',
            context=context
        )
    
    def send_receipt_approved_notification(self, receipt, approved_by):
        """Notificar aprobación de recepción"""
        subject = _('Purchase Receipt Approved: {receipt_number}').format(
            receipt_number=receipt.receipt_number
        )
        
        context = {
            'receipt': receipt,
            'approved_by': approved_by,
            'order': receipt.purchase_order_line.purchase_order,
            'supplier': receipt.purchase_order_line.purchase_order.supplier,
            'quality_score': receipt.quality_score,
        }
        
        # Notificar al receptor
        self._send_email_to_user(
            user=receipt.received_by,
            subject=subject,
            template='purchases/emails/receipt_approved.html',
            context=context
        )
    
    def send_supplier_rating_notification(self, rating):
        """Notificar evaluación de proveedor"""
        subject = _('Supplier Rating Submitted: {supplier_name}').format(
            supplier_name=rating.supplier.name
        )
        
        context = {
            'rating': rating,
            'supplier': rating.supplier,
            'evaluated_by': rating.evaluated_by,
            'overall_score': rating.overall_score,
            'rating_class': rating.get_rating_class_display(),
        }
        
        # Notificar al evaluador
        self._send_email_to_user(
            user=rating.evaluated_by,
            subject=subject,
            template='purchases/emails/supplier_rating_submitted.html',
            context=context
        )
    
    def send_approval_reminder_notification(self, request, approver):
        """Enviar recordatorio de aprobación pendiente"""
        subject = _('Approval Reminder: {request_number}').format(
            request_number=request.request_number
        )
        
        context = {
            'request': request,
            'approver': approver,
            'requested_by': request.requested_by,
            'days_pending': (timezone.now().date() - request.request_date).days,
            'total_amount': request.total_amount,
            'currency': request.currency,
        }
        
        self._send_email_to_user(
            user=approver,
            subject=subject,
            template='purchases/emails/approval_reminder.html',
            context=context
        )
    
    def send_delivery_reminder_notification(self, order):
        """Enviar recordatorio de entrega próxima"""
        subject = _('Delivery Reminder: {order_number}').format(
            order_number=order.order_number
        )
        
        context = {
            'order': order,
            'supplier': order.supplier,
            'expected_delivery': order.expected_delivery_date,
            'days_until_delivery': (order.expected_delivery_date - timezone.now().date()).days,
            'total_amount': order.total_amount,
            'currency': order.currency,
        }
        
        # Notificar al proveedor
        if order.supplier.email:
            self._send_email_to_supplier(
                supplier=order.supplier,
                subject=subject,
                template='purchases/emails/delivery_reminder_supplier.html',
                context=context
            )
        
        # Notificar al creador de la orden
        self._send_email_to_user(
            user=order.created_by,
            subject=subject,
            template='purchases/emails/delivery_reminder.html',
            context=context
        )
    
    def _send_email_to_user(self, user, subject, template, context):
        """Enviar email a un usuario"""
        if not user.email:
            return
        
        try:
            html_message = render_to_string(template, context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Error sending email to {user.email}: {e}")
    
    def _send_email_to_supplier(self, supplier, subject, template, context):
        """Enviar email a un proveedor"""
        if not supplier.email:
            return
        
        try:
            html_message = render_to_string(template, context)
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=self.from_email,
                recipient_list=[supplier.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log error but don't fail the operation
            print(f"Error sending email to supplier {supplier.email}: {e}")
    
    def _notify_approvers(self, request, subject, context):
        """Notificar a todos los aprobadores del flujo"""
        if not request.approval_workflow:
            return
        
        approvers = self._get_approvers_for_request(request)
        
        for approver in approvers:
            self._send_email_to_user(
                user=approver,
                subject=subject,
                template='purchases/emails/request_needs_approval.html',
                context={**context, 'approver': approver}
            )
    
    def _notify_other_approvers(self, request, subject, context, approved_by):
        """Notificar a otros aprobadores cuando uno aprueba"""
        if not request.approval_workflow:
            return
        
        approvers = self._get_approvers_for_request(request)
        
        for approver in approvers:
            if approver != approved_by:
                self._send_email_to_user(
                    user=approver,
                    subject=subject,
                    template='purchases/emails/request_approved_others.html',
                    context={**context, 'approver': approver}
                )
    
    def _get_approvers_for_request(self, request):
        """Obtener lista de aprobadores para una solicitud"""
        approvers = []
        
        if request.approval_workflow:
            for level in request.approval_workflow.levels.all():
                if level.approval_type == 'user':
                    approvers.extend(level.approvers.all())
                elif level.approval_type == 'role':
                    # Obtener usuarios con roles específicos
                    from core.models import UsuarioExtendido
                    role_users = UsuarioExtendido.objects.filter(
                        empresa=request.empresa,
                        roles__name__in=level.roles
                    )
                    approvers.extend(role_users)
        
        return list(set(approvers))  # Eliminar duplicados


# Instancia global del servicio
notification_service = PurchaseNotificationService() 