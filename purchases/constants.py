from django.utils.translation import gettext_lazy as _


class PurchaseDocumentStates:
    """Estados unificados para documentos de compra"""
    
    # Estados para solicitudes de compra
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    QUOTATION_REQUESTED = 'quotation_requested'
    CONVERTED = 'converted'
    CANCELLED = 'cancelled'
    
    # Estados para órdenes de compra
    ORDER_CREATED = 'order_created'
    ORDER_SENT = 'order_sent'
    ORDER_CONFIRMED = 'order_confirmed'
    PARTIALLY_RECEIVED = 'partially_received'
    FULLY_RECEIVED = 'fully_received'
    INVOICED = 'invoiced'
    PAID = 'paid'
    COMPLETED = 'completed'
    
    # Estados finales
    FINAL_STATES = [CANCELLED, REJECTED, COMPLETED]
    
    # Transiciones válidas por estado
    VALID_TRANSITIONS = {
        # Solicitudes
        DRAFT: [SUBMITTED, CANCELLED],
        SUBMITTED: [APPROVED, REJECTED, CANCELLED],
        APPROVED: [QUOTATION_REQUESTED, CONVERTED, CANCELLED],
        REJECTED: [DRAFT],  # Puede ser reenviada
        QUOTATION_REQUESTED: [APPROVED, CANCELLED],
        CONVERTED: [],  # Estado final para solicitudes
        CANCELLED: [],  # Estado final
        
        # Órdenes
        ORDER_CREATED: [ORDER_SENT, CANCELLED],
        ORDER_SENT: [ORDER_CONFIRMED, CANCELLED],
        ORDER_CONFIRMED: [PARTIALLY_RECEIVED, FULLY_RECEIVED, CANCELLED],
        PARTIALLY_RECEIVED: [FULLY_RECEIVED, CANCELLED],
        FULLY_RECEIVED: [INVOICED, CANCELLED],
        INVOICED: [PAID, CANCELLED],
        PAID: [COMPLETED, CANCELLED],
        COMPLETED: [],  # Estado final
    }
    
    # Etiquetas para mostrar en la interfaz
    LABELS = {
        DRAFT: _('Draft'),
        SUBMITTED: _('Submitted'),
        APPROVED: _('Approved'),
        REJECTED: _('Rejected'),
        QUOTATION_REQUESTED: _('Quotation Requested'),
        CONVERTED: _('Converted to Order'),
        CANCELLED: _('Cancelled'),
        ORDER_CREATED: _('Order Created'),
        ORDER_SENT: _('Order Sent'),
        ORDER_CONFIRMED: _('Order Confirmed'),
        PARTIALLY_RECEIVED: _('Partially Received'),
        FULLY_RECEIVED: _('Fully Received'),
        INVOICED: _('Invoiced'),
        PAID: _('Paid'),
        COMPLETED: _('Completed'),
    }
    
    # Colores para los estados
    COLORS = {
        DRAFT: 'gray',
        SUBMITTED: 'blue',
        APPROVED: 'green',
        REJECTED: 'red',
        QUOTATION_REQUESTED: 'yellow',
        CONVERTED: 'purple',
        CANCELLED: 'red',
        ORDER_CREATED: 'blue',
        ORDER_SENT: 'orange',
        ORDER_CONFIRMED: 'green',
        PARTIALLY_RECEIVED: 'yellow',
        FULLY_RECEIVED: 'green',
        INVOICED: 'purple',
        PAID: 'green',
        COMPLETED: 'green',
    }
    
    # Estados que requieren aprobación
    REQUIRES_APPROVAL = [SUBMITTED]
    
    # Estados que permiten edición
    EDITABLE_STATES = [DRAFT, ORDER_CREATED]
    
    # Estados que permiten cancelación
    CANCELLABLE_STATES = [
        DRAFT, SUBMITTED, APPROVED, QUOTATION_REQUESTED,
        ORDER_CREATED, ORDER_SENT, ORDER_CONFIRMED
    ]


class PurchaseDocumentTypes:
    """Tipos de documento de compra"""
    
    REQUEST = 'request'
    ORDER = 'order'
    
    CHOICES = [
        (REQUEST, _('Purchase Request')),
        (ORDER, _('Purchase Order')),
    ]
    
    LABELS = {
        REQUEST: _('Purchase Request'),
        ORDER: _('Purchase Order'),
    }
    
    # Estados iniciales por tipo
    INITIAL_STATES = {
        REQUEST: PurchaseDocumentStates.DRAFT,
        ORDER: PurchaseDocumentStates.ORDER_CREATED,
    }


class PurchasePriorities:
    """Prioridades para documentos de compra"""
    
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'
    
    CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
        (URGENT, _('Urgent')),
    ]
    
    COLORS = {
        LOW: 'gray',
        MEDIUM: 'blue',
        HIGH: 'orange',
        URGENT: 'red',
    }


class PurchaseLineStatus:
    """Estados para líneas de documentos de compra"""
    
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    ORDERED = 'ordered'
    RECEIVED = 'received'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (PENDING, _('Pending')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
        (ORDERED, _('Ordered')),
        (RECEIVED, _('Received')),
        (CANCELLED, _('Cancelled')),
    ]
    
    COLORS = {
        PENDING: 'gray',
        APPROVED: 'green',
        REJECTED: 'red',
        ORDERED: 'blue',
        RECEIVED: 'green',
        CANCELLED: 'red',
    }


class ApprovalActions:
    """Acciones de aprobación"""
    
    SUBMIT = 'submit'
    APPROVE = 'approve'
    REJECT = 'reject'
    REQUEST_QUOTATION = 'request_quotation'
    CREATE_ORDER = 'create_order'
    SEND_ORDER = 'send_order'
    CONFIRM_ORDER = 'confirm_order'
    CANCEL = 'cancel'
    
    LABELS = {
        SUBMIT: _('Submit for Approval'),
        APPROVE: _('Approve'),
        REJECT: _('Reject'),
        REQUEST_QUOTATION: _('Request Quotation'),
        CREATE_ORDER: _('Create Order'),
        SEND_ORDER: _('Send Order'),
        CONFIRM_ORDER: _('Confirm Order'),
        CANCEL: _('Cancel'),
    }
    
    # Acciones disponibles por tipo de documento
    AVAILABLE_ACTIONS = {
        PurchaseDocumentTypes.REQUEST: [
            SUBMIT, APPROVE, REJECT, REQUEST_QUOTATION, CREATE_ORDER, CANCEL
        ],
        PurchaseDocumentTypes.ORDER: [
            SEND_ORDER, CONFIRM_ORDER, CANCEL
        ],
    }
    
    # Acciones disponibles por estado
    ACTIONS_BY_STATE = {
        PurchaseDocumentStates.DRAFT: [SUBMIT, CANCEL],
        PurchaseDocumentStates.SUBMITTED: [APPROVE, REJECT, CANCEL],
        PurchaseDocumentStates.APPROVED: [REQUEST_QUOTATION, CREATE_ORDER, CANCEL],
        PurchaseDocumentStates.QUOTATION_REQUESTED: [APPROVE, CANCEL],
        PurchaseDocumentStates.ORDER_CREATED: [SEND_ORDER, CANCEL],
        PurchaseDocumentStates.ORDER_SENT: [CONFIRM_ORDER, CANCEL],
        PurchaseDocumentStates.ORDER_CONFIRMED: [CANCEL],
    } 