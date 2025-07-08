# Constantes de estados unificados para el flujo de compras
class PurchaseDocumentStates:
    """Estados unificados para documentos de compra (solicitudes y órdenes)"""
    DRAFT = 'draft'                           # Borrador
    SUBMITTED = 'submitted'                   # Enviado para aprobación
    APPROVED = 'approved'                     # Aprobado
    QUOTATION_REQUESTED = 'quotation_requested'  # Cotización solicitada
    QUOTATION_RECEIVED = 'quotation_received'    # Cotización recibida
    ORDER_CREATED = 'order_created'           # Orden creada
    ORDER_SENT = 'order_sent'                 # Orden enviada al proveedor
    ORDER_CONFIRMED = 'order_confirmed'       # Orden confirmada por proveedor
    PARTIALLY_RECEIVED = 'partially_received' # Parcialmente recibido
    FULLY_RECEIVED = 'fully_received'         # Completamente recibido
    INVOICED = 'invoiced'                     # Facturado
    PAID = 'paid'                             # Pagado
    COMPLETED = 'completed'                   # Completado
    CANCELLED = 'cancelled'                   # Cancelado
    REJECTED = 'rejected'                     # Rechazado

    CHOICES = [
        (DRAFT, 'Draft'),
        (SUBMITTED, 'Submitted'),
        (APPROVED, 'Approved'),
        (QUOTATION_REQUESTED, 'Quotation Requested'),
        (QUOTATION_RECEIVED, 'Quotation Received'),
        (ORDER_CREATED, 'Order Created'),
        (ORDER_SENT, 'Order Sent'),
        (ORDER_CONFIRMED, 'Order Confirmed'),
        (PARTIALLY_RECEIVED, 'Partially Received'),
        (FULLY_RECEIVED, 'Fully Received'),
        (INVOICED, 'Invoiced'),
        (PAID, 'Paid'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (REJECTED, 'Rejected'),
    ]

    # Transiciones válidas de estado
    VALID_TRANSITIONS = {
        DRAFT: [SUBMITTED, CANCELLED],
        SUBMITTED: [APPROVED, REJECTED, CANCELLED],
        APPROVED: [QUOTATION_REQUESTED, ORDER_CREATED, CANCELLED],
        QUOTATION_REQUESTED: [QUOTATION_RECEIVED, CANCELLED],
        QUOTATION_RECEIVED: [ORDER_CREATED, CANCELLED],
        ORDER_CREATED: [ORDER_SENT, CANCELLED],
        ORDER_SENT: [ORDER_CONFIRMED, CANCELLED],
        ORDER_CONFIRMED: [PARTIALLY_RECEIVED, FULLY_RECEIVED, CANCELLED],
        PARTIALLY_RECEIVED: [FULLY_RECEIVED, CANCELLED],
        FULLY_RECEIVED: [INVOICED, CANCELLED],
        INVOICED: [PAID, CANCELLED],
        PAID: [COMPLETED],
        CANCELLED: [],  # Estado final
        REJECTED: [],   # Estado final
        COMPLETED: [],  # Estado final
    }

    # Estados que requieren solicitud de compra
    REQUIRES_REQUEST = [DRAFT, SUBMITTED, APPROVED, QUOTATION_REQUESTED, QUOTATION_RECEIVED]
    
    # Estados que son órdenes de compra
    IS_ORDER = [ORDER_CREATED, ORDER_SENT, ORDER_CONFIRMED, PARTIALLY_RECEIVED, FULLY_RECEIVED, INVOICED, PAID, COMPLETED]

class PurchaseDocumentTypes:
    """Tipos de documentos de compra"""
    REQUEST = 'request'      # Solicitud de compra
    ORDER = 'order'          # Orden de compra
    
    CHOICES = [
        (REQUEST, 'Purchase Request'),
        (ORDER, 'Purchase Order'),
    ]

# Importar todos los modelos del módulo de compras
from .supplier import Supplier
from .approval_workflow import ApprovalWorkflow, ApprovalLevel, ApprovalRequest
from .purchase_request import PurchaseRequest, PurchaseRequestLine
from .purchase_quotation import PurchaseQuotation, PurchaseQuotationLine
from .purchase_order import PurchaseOrder, PurchaseOrderLine
from .purchase_receipt import PurchaseReceipt, PurchaseReceiptDocument
from .supplier_rating import SupplierRating, SupplierPerformanceMetric
from .approval_record import ApprovalRecord

__all__ = [
    # Constantes
    'PurchaseDocumentStates',
    'PurchaseDocumentTypes',
    
    # Proveedores
    'Supplier',
    
    # Flujos de aprobación
    'ApprovalWorkflow',
    'ApprovalLevel',
    'ApprovalRequest',
    'ApprovalRecord',
    
    # Solicitudes de compra
    'PurchaseRequest',
    'PurchaseRequestLine',
    
    # Cotizaciones
    'PurchaseQuotation',
    'PurchaseQuotationLine',
    
    # Órdenes de compra
    'PurchaseOrder',
    'PurchaseOrderLine',
    
    # Recepciones
    'PurchaseReceipt',
    'PurchaseReceiptDocument',
    
    # Evaluaciones de proveedores
    'SupplierRating',
    'SupplierPerformanceMetric',
] 