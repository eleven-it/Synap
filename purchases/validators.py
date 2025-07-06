from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
import re


class PurchaseRequestValidator:
    """Validador para solicitudes de compra"""
    
    @staticmethod
    def validate_request_amount(amount, empresa):
        """Validar monto de solicitud según límites de la empresa"""
        if amount <= 0:
            raise ValidationError(_("Request amount must be greater than zero"))
        
        # Obtener límites de la empresa (configurables)
        max_amount = getattr(empresa, 'max_purchase_request_amount', Decimal('1000000'))
        
        if amount > max_amount:
            raise ValidationError(
                _("Request amount ({amount}) exceeds maximum allowed amount ({max_amount})").format(
                    amount=amount, max_amount=max_amount
                )
            )
    
    @staticmethod
    def validate_required_date(required_date, request_date):
        """Validar fecha de requerimiento"""
        if required_date <= request_date:
            raise ValidationError(_("Required date must be after request date"))
        
        # No permitir fechas muy lejanas (más de 1 año)
        max_date = request_date + timezone.timedelta(days=365)
        if required_date > max_date:
            raise ValidationError(_("Required date cannot be more than 1 year in the future"))
    
    @staticmethod
    def validate_priority_for_amount(priority, amount):
        """Validar prioridad según monto"""
        if amount > Decimal('50000') and priority == 'low':
            raise ValidationError(_("High amount requests cannot have low priority"))
        
        if amount < Decimal('1000') and priority == 'high':
            raise ValidationError(_("Low amount requests should not have high priority"))
    
    @staticmethod
    def validate_supplier_credit_limit(supplier, amount):
        """Validar límite de crédito del proveedor"""
        if supplier and supplier.credit_limit:
            # Obtener deuda actual del proveedor
            from .models import PurchaseOrder
            current_debt = PurchaseOrder.objects.filter(
                supplier=supplier,
                status__in=['confirmed', 'partially_received']
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            if current_debt + amount > supplier.credit_limit:
                raise ValidationError(
                    _("Request amount would exceed supplier's credit limit. "
                      "Current debt: {current_debt}, Credit limit: {credit_limit}").format(
                        current_debt=current_debt, credit_limit=supplier.credit_limit
                    )
                )


class PurchaseOrderValidator:
    """Validador para órdenes de compra"""
    
    @staticmethod
    def validate_order_amount(amount, empresa):
        """Validar monto de orden según límites"""
        if amount <= 0:
            raise ValidationError(_("Order amount must be greater than zero"))
        
        # Obtener límites de la empresa
        max_amount = getattr(empresa, 'max_purchase_order_amount', Decimal('2000000'))
        
        if amount > max_amount:
            raise ValidationError(
                _("Order amount ({amount}) exceeds maximum allowed amount ({max_amount})").format(
                    amount=amount, max_amount=max_amount
                )
            )
    
    @staticmethod
    def validate_delivery_date(delivery_date, order_date):
        """Validar fecha de entrega"""
        if delivery_date <= order_date:
            raise ValidationError(_("Expected delivery date must be after order date"))
        
        # No permitir fechas muy lejanas
        max_date = order_date + timezone.timedelta(days=180)
        if delivery_date > max_date:
            raise ValidationError(_("Expected delivery date cannot be more than 6 months in the future"))
    
    @staticmethod
    def validate_supplier_availability(supplier, delivery_date):
        """Validar disponibilidad del proveedor"""
        if supplier and hasattr(supplier, 'is_active') and not supplier.is_active:
            raise ValidationError(_("Cannot create order with inactive supplier"))
        
        # Aquí se podrían agregar validaciones adicionales como:
        # - Horarios de entrega del proveedor
        # - Días festivos
        # - Capacidad de producción
    
    @staticmethod
    def validate_quotation_validity(quotation):
        """Validar que la cotización esté vigente"""
        if quotation and quotation.valid_until:
            if timezone.now().date() > quotation.valid_until:
                raise ValidationError(_("Quotation has expired and cannot be used for order creation"))


class PurchaseReceiptValidator:
    """Validador para recepciones"""
    
    @staticmethod
    def validate_receipt_quantity(quantity, order_line):
        """Validar cantidad recibida vs ordenada"""
        if quantity <= 0:
            raise ValidationError(_("Receipt quantity must be greater than zero"))
        
        if quantity > order_line.remaining_quantity:
            raise ValidationError(
                _("Receipt quantity ({quantity}) cannot exceed remaining order quantity ({remaining})").format(
                    quantity=quantity, remaining=order_line.remaining_quantity
                )
            )
    
    @staticmethod
    def validate_expiration_date(expiration_date, manufacturing_date=None):
        """Validar fecha de vencimiento"""
        if expiration_date and expiration_date <= timezone.now().date():
            raise ValidationError(_("Expiration date must be in the future"))
        
        if manufacturing_date and expiration_date:
            if expiration_date <= manufacturing_date:
                raise ValidationError(_("Expiration date must be after manufacturing date"))
    
    @staticmethod
    def validate_quality_score(score):
        """Validar puntuación de calidad"""
        if score is not None:
            if not (1 <= score <= 10):
                raise ValidationError(_("Quality score must be between 1 and 10"))
    
    @staticmethod
    def validate_lot_number(lot_number):
        """Validar formato del número de lote"""
        if lot_number:
            # Formato básico: alfanumérico con guiones permitidos
            if not re.match(r'^[A-Za-z0-9\-_]+$', lot_number):
                raise ValidationError(_("Lot number can only contain letters, numbers, hyphens and underscores"))


class SupplierValidator:
    """Validador para proveedores"""
    
    @staticmethod
    def validate_tax_id(tax_id, empresa):
        """Validar ID fiscal único por empresa"""
        if tax_id:
            from .models import Supplier
            existing = Supplier.objects.filter(
                empresa=empresa,
                tax_id=tax_id
            ).exclude(id=getattr(Supplier, 'id', None))
            
            if existing.exists():
                raise ValidationError(_("A supplier with this tax ID already exists in your company"))
    
    @staticmethod
    def validate_email_format(email):
        """Validar formato de email"""
        if email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                raise ValidationError(_("Please enter a valid email address"))
    
    @staticmethod
    def validate_phone_format(phone):
        """Validar formato de teléfono"""
        if phone:
            # Permitir formatos internacionales
            phone_pattern = r'^[\+]?[1-9][\d]{0,15}$'
            if not re.match(phone_pattern, phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                raise ValidationError(_("Please enter a valid phone number"))
    
    @staticmethod
    def validate_credit_limit(credit_limit):
        """Validar límite de crédito"""
        if credit_limit is not None and credit_limit < 0:
            raise ValidationError(_("Credit limit cannot be negative"))


class QuotationValidator:
    """Validador para cotizaciones"""
    
    @staticmethod
    def validate_quotation_amount(amount):
        """Validar monto de cotización"""
        if amount <= 0:
            raise ValidationError(_("Quotation amount must be greater than zero"))
    
    @staticmethod
    def validate_validity_period(valid_until, quotation_date):
        """Validar período de validez"""
        if valid_until <= quotation_date:
            raise ValidationError(_("Validity period must be after quotation date"))
        
        # No permitir validez muy larga (más de 90 días)
        max_validity = quotation_date + timezone.timedelta(days=90)
        if valid_until > max_validity:
            raise ValidationError(_("Validity period cannot exceed 90 days"))
    
    @staticmethod
    def validate_delivery_time(delivery_time):
        """Validar tiempo de entrega"""
        if delivery_time is not None and delivery_time <= 0:
            raise ValidationError(_("Delivery time must be greater than zero"))
        
        if delivery_time and delivery_time > 365:
            raise ValidationError(_("Delivery time cannot exceed 365 days"))


class ApprovalValidator:
    """Validador para flujos de aprobación"""
    
    @staticmethod
    def validate_approval_levels(workflow):
        """Validar niveles de aprobación"""
        levels = workflow.levels.all().order_by('priority')
        
        if not levels.exists():
            raise ValidationError(_("Approval workflow must have at least one level"))
        
        # Verificar que las prioridades sean consecutivas
        for i, level in enumerate(levels, 1):
            if level.priority != i:
                raise ValidationError(_("Approval levels must have consecutive priorities starting from 1"))
        
        # Verificar que cada nivel tenga aprobadores
        for level in levels:
            if not level.approvers.exists() and not level.roles and not level.groups:
                raise ValidationError(
                    _("Approval level '{level_name}' must have at least one approver, role, or group").format(
                        level_name=level.name
                    )
                )
    
    @staticmethod
    def validate_amount_ranges(workflow):
        """Validar rangos de monto"""
        if workflow.min_amount is not None and workflow.max_amount is not None:
            if workflow.min_amount >= workflow.max_amount:
                raise ValidationError(_("Minimum amount must be less than maximum amount"))
        
        # Verificar que no haya solapamiento con otros workflows
        from .models import ApprovalWorkflow
        overlapping = ApprovalWorkflow.objects.filter(
            empresa=workflow.empresa,
            is_active=True
        ).exclude(id=workflow.id)
        
        for other in overlapping:
            if ApprovalValidator._ranges_overlap(workflow, other):
                raise ValidationError(
                    _("Amount range overlaps with existing workflow '{workflow_name}'").format(
                        workflow_name=other.name
                    )
                )
    
    @staticmethod
    def _ranges_overlap(workflow1, workflow2):
        """Verificar si dos rangos de monto se solapan"""
        min1 = workflow1.min_amount or Decimal('0')
        max1 = workflow1.max_amount or Decimal('999999999')
        min2 = workflow2.min_amount or Decimal('0')
        max2 = workflow2.max_amount or Decimal('999999999')
        
        return not (max1 <= min2 or max2 <= min1)


class BusinessRuleValidator:
    """Validador de reglas de negocio generales"""
    
    @staticmethod
    def validate_company_limits(empresa, amount, operation_type):
        """Validar límites generales de la empresa"""
        # Obtener límites de la empresa
        daily_limit = getattr(empresa, 'daily_purchase_limit', Decimal('100000'))
        monthly_limit = getattr(empresa, 'monthly_purchase_limit', Decimal('2000000'))
        
        # Verificar límite diario
        today = timezone.now().date()
        from .models import PurchaseOrder
        daily_total = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date=today
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        if daily_total + amount > daily_limit:
            raise ValidationError(
                _("Operation would exceed daily purchase limit. "
                  "Daily total: {daily_total}, Limit: {limit}").format(
                    daily_total=daily_total, limit=daily_limit
                )
            )
        
        # Verificar límite mensual
        month_start = today.replace(day=1)
        monthly_total = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__gte=month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        if monthly_total + amount > monthly_limit:
            raise ValidationError(
                _("Operation would exceed monthly purchase limit. "
                  "Monthly total: {monthly_total}, Limit: {limit}").format(
                    monthly_total=monthly_total, limit=monthly_limit
                )
            )
    
    @staticmethod
    def validate_user_permissions(user, operation_type, amount=None):
        """Validar permisos del usuario para la operación"""
        # Verificar si el usuario tiene permisos básicos
        if not user.is_authenticated:
            raise ValidationError(_("User must be authenticated"))
        
        # Verificar permisos específicos según el tipo de operación
        if operation_type == 'create_request':
            if not user.has_perm('purchases.add_purchaserequest'):
                raise ValidationError(_("User does not have permission to create purchase requests"))
        
        elif operation_type == 'approve_request':
            if not user.has_perm('purchases.approve_purchaserequest'):
                raise ValidationError(_("User does not have permission to approve purchase requests"))
        
        elif operation_type == 'create_order':
            if not user.has_perm('purchases.add_purchaseorder'):
                raise ValidationError(_("User does not have permission to create purchase orders"))
            
            # Verificar límites de monto según rol
            if amount:
                max_amount_by_role = {
                    'purchaser': Decimal('50000'),
                    'senior_purchaser': Decimal('200000'),
                    'purchase_manager': Decimal('1000000'),
                }
                
                user_role = getattr(user, 'role', 'purchaser')
                max_amount = max_amount_by_role.get(user_role, Decimal('10000'))
                
                if amount > max_amount:
                    raise ValidationError(
                        _("Amount exceeds your role limit. Your limit: {limit}").format(limit=max_amount)
                    )
    
    @staticmethod
    def validate_workflow_compliance(request):
        """Validar cumplimiento del flujo de aprobación"""
        if request.total_amount > Decimal('10000'):  # Umbral configurable
            if not request.approval_workflow:
                raise ValidationError(_("Requests over $10,000 require approval workflow"))
            
            # Verificar que el flujo tenga niveles configurados
            if not request.approval_workflow.levels.exists():
                raise ValidationError(_("Approval workflow must have configured levels"))
    
    @staticmethod
    def validate_supplier_rating(supplier, min_rating=6.0):
        """Validar calificación mínima del proveedor"""
        if supplier.rating_class == 'poor':
            raise ValidationError(
                _("Cannot create orders with suppliers rated as 'poor'. "
                  "Please select a different supplier or improve supplier rating.")
            )
        
        # Verificar calificación numérica si existe
        from .models import SupplierRating
        latest_rating = SupplierRating.objects.filter(
            supplier=supplier,
            status='approved'
        ).order_by('-rating_date').first()
        
        if latest_rating and latest_rating.overall_score < min_rating:
            raise ValidationError(
                _("Supplier rating ({rating}) is below minimum required ({min_rating})").format(
                    rating=latest_rating.overall_score, min_rating=min_rating
                )
            )


# Funciones de validación de conveniencia
def validate_purchase_request(request):
    """Validar solicitud de compra completa"""
    validator = PurchaseRequestValidator()
    
    # Validaciones básicas
    validator.validate_request_amount(request.total_amount, request.empresa)
    validator.validate_required_date(request.required_date, request.request_date)
    validator.validate_priority_for_amount(request.priority, request.total_amount)
    
    if request.supplier:
        validator.validate_supplier_credit_limit(request.supplier, request.total_amount)
    
    # Validaciones de reglas de negocio
    business_validator = BusinessRuleValidator()
    business_validator.validate_company_limits(request.empresa, request.total_amount, 'create_request')
    business_validator.validate_user_permissions(request.requested_by, 'create_request')
    business_validator.validate_workflow_compliance(request)
    
    if request.supplier:
        business_validator.validate_supplier_rating(request.supplier)


def validate_purchase_order(order):
    """Validar orden de compra completa"""
    validator = PurchaseOrderValidator()
    
    # Validaciones básicas
    validator.validate_order_amount(order.total_amount, order.empresa)
    validator.validate_delivery_date(order.expected_delivery_date, order.order_date)
    validator.validate_supplier_availability(order.supplier, order.expected_delivery_date)
    
    if order.quotation:
        validator.validate_quotation_validity(order.quotation)
    
    # Validaciones de reglas de negocio
    business_validator = BusinessRuleValidator()
    business_validator.validate_company_limits(order.empresa, order.total_amount, 'create_order')
    business_validator.validate_user_permissions(order.created_by, 'create_order', order.total_amount)
    
    if order.supplier:
        business_validator.validate_supplier_rating(order.supplier)


def validate_purchase_receipt(receipt):
    """Validar recepción completa"""
    validator = PurchaseReceiptValidator()
    
    # Validaciones básicas
    validator.validate_receipt_quantity(receipt.quantity, receipt.purchase_order_line)
    
    if receipt.expiration_date:
        validator.validate_expiration_date(receipt.expiration_date, receipt.manufacturing_date)
    
    if receipt.quality_score:
        validator.validate_quality_score(receipt.quality_score)
    
    if receipt.lot_number:
        validator.validate_lot_number(receipt.lot_number) 