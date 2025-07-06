from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from core.models import Empresa, Branch, Currency, UnitOfMeasure
from inventory.models import Product, ProductVariant, Category
from purchases.models import (
    Supplier, ApprovalWorkflow, ApprovalLevel, PurchaseRequest, PurchaseRequestLine,
    PurchaseOrder, PurchaseOrderLine, PurchaseQuotation, PurchaseQuotationLine,
    PurchaseReceipt, PurchaseReceiptDocument, SupplierRating
)

User = get_user_model()


class SupplierModelTest(TestCase):
    """Pruebas para el modelo Supplier"""
    
    def setUp(self):
        """Configuración inicial"""
        self.empresa = Empresa.objects.create(
            nombre="Empresa Test",
            identificador_fiscal="12345678"
        )
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_supplier_creation(self):
        """Probar creación básica de proveedor"""
        supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            code="PROV001",
            tax_id="98765432",
            email="proveedor@test.com",
            phone="+1234567890",
            is_active=True
        )
        
        self.assertEqual(supplier.name, "Proveedor Test")
        self.assertEqual(supplier.code, "PROV001")
        self.assertTrue(supplier.is_active)
        self.assertEqual(supplier.rating_class, 'new')
    
    def test_supplier_str_representation(self):
        """Probar representación string del proveedor"""
        supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test",
            code="PROV001"
        )
        
        self.assertEqual(str(supplier), "Proveedor Test (PROV001)")
    
    def test_supplier_unique_tax_id_per_empresa(self):
        """Probar que el ID fiscal sea único por empresa"""
        Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor 1",
            tax_id="12345678"
        )
        
        # Debería permitir el mismo tax_id en otra empresa
        otra_empresa = Empresa.objects.create(name="Otra Empresa")
        supplier2 = Supplier.objects.create(
            empresa=otra_empresa,
            name="Proveedor 2",
            tax_id="12345678"
        )
        
        self.assertEqual(supplier2.tax_id, "12345678")
    
    def test_supplier_rating_class_update(self):
        """Probar actualización de clase de calificación"""
        supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
        
        # Crear evaluación con calificación alta
        rating = SupplierRating.objects.create(
            supplier=supplier,
            evaluated_by=self.user,
            overall_score=9.0,
            status='approved'
        )
        
        # La clase debería actualizarse automáticamente
        supplier.refresh_from_db()
        self.assertEqual(supplier.rating_class, 'excellent')


class ApprovalWorkflowModelTest(TestCase):
    """Pruebas para el modelo ApprovalWorkflow"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_workflow_creation(self):
        """Probar creación de flujo de aprobación"""
        workflow = ApprovalWorkflow.objects.create(
            empresa=self.empresa,
            name="Flujo Test",
            min_amount=Decimal('10000'),
            max_amount=Decimal('100000'),
            is_active=True
        )
        
        self.assertEqual(workflow.name, "Flujo Test")
        self.assertEqual(workflow.min_amount, Decimal('10000'))
        self.assertTrue(workflow.is_active)
    
    def test_workflow_str_representation(self):
        """Probar representación string del flujo"""
        workflow = ApprovalWorkflow.objects.create(
            empresa=self.empresa,
            name="Flujo Test",
            min_amount=Decimal('10000'),
            max_amount=Decimal('100000')
        )
        
        expected = "Flujo Test ($10,000 - $100,000)"
        self.assertEqual(str(workflow), expected)
    
    def test_workflow_amount_range_validation(self):
        """Probar validación de rangos de monto"""
        # Debería fallar si min_amount >= max_amount
        with self.assertRaises(ValidationError):
            workflow = ApprovalWorkflow(
                empresa=self.empresa,
                name="Flujo Inválido",
                min_amount=Decimal('100000'),
                max_amount=Decimal('10000')
            )
            workflow.full_clean()


class ApprovalLevelModelTest(TestCase):
    """Pruebas para el modelo ApprovalLevel"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.workflow = ApprovalWorkflow.objects.create(
            empresa=self.empresa,
            name="Flujo Test"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_level_creation(self):
        """Probar creación de nivel de aprobación"""
        level = ApprovalLevel.objects.create(
            workflow=self.workflow,
            name="Nivel 1",
            priority=1,
            approval_type='user'
        )
        level.approvers.add(self.user)
        
        self.assertEqual(level.name, "Nivel 1")
        self.assertEqual(level.priority, 1)
        self.assertEqual(level.approval_type, 'user')
        self.assertIn(self.user, level.approvers.all())


class PurchaseRequestModelTest(TestCase):
    """Pruebas para el modelo PurchaseRequest"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
    
    def test_request_creation(self):
        """Probar creación de solicitud de compra"""
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            description="Descripción de prueba",
            priority='medium',
            required_date=timezone.now().date() + timedelta(days=30),
            requested_by=self.user,
            currency=self.currency,
            supplier=self.supplier
        )
        
        self.assertEqual(request.title, "Solicitud Test")
        self.assertEqual(request.status, 'draft')
        self.assertIsNotNone(request.request_number)
        self.assertEqual(request.total_amount, Decimal('0'))
    
    def test_request_number_generation(self):
        """Probar generación automática de números de solicitud"""
        request1 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud 1",
            requested_by=self.user,
            currency=self.currency
        )
        
        request2 = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud 2",
            requested_by=self.user,
            currency=self.currency
        )
        
        self.assertNotEqual(request1.request_number, request2.request_number)
        self.assertTrue(request1.request_number.startswith('REQ'))
        self.assertTrue(request2.request_number.startswith('REQ'))
    
    def test_request_status_transitions(self):
        """Probar transiciones de estado"""
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
        
        # Estado inicial
        self.assertEqual(request.status, 'draft')
        
        # Enviar a aprobación
        request.status = 'pending_approval'
        request.save()
        self.assertEqual(request.status, 'pending_approval')
        
        # Aprobar
        request.status = 'approved'
        request.approved_date = timezone.now().date()
        request.save()
        self.assertEqual(request.status, 'approved')
    
    def test_request_total_calculation(self):
        """Probar cálculo de total de solicitud"""
        request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
        
        # Crear líneas
        PurchaseRequestLine.objects.create(
            request=request,
            quantity=10,
            estimated_unit_price=Decimal('100.00')
        )
        
        PurchaseRequestLine.objects.create(
            request=request,
            quantity=5,
            estimated_unit_price=Decimal('50.00')
        )
        
        # Recalcular total
        request.calculate_total()
        request.save()
        
        expected_total = Decimal('1250.00')  # 10*100 + 5*50
        self.assertEqual(request.total_amount, expected_total)


class PurchaseRequestLineModelTest(TestCase):
    """Pruebas para el modelo PurchaseRequestLine"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(
            empresa=self.empresa,
            name="Categoría Test"
        )
        self.product = Product.objects.create(
            empresa=self.empresa,
            name="Producto Test",
            category=self.category
        )
        self.product_variant = ProductVariant.objects.create(
            product=self.product,
            name="Variante Test",
            sku="SKU001"
        )
        self.uom = UnitOfMeasure.objects.create(
            empresa=self.empresa,
            name="Unidad",
            code="U"
        )
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
    
    def test_line_creation(self):
        """Probar creación de línea de solicitud"""
        line = PurchaseRequestLine.objects.create(
            request=self.request,
            product_variant=self.product_variant,
            quantity=10,
            estimated_unit_price=Decimal('100.00'),
            unit_of_measure=self.uom,
            description="Descripción de línea"
        )
        
        self.assertEqual(line.quantity, 10)
        self.assertEqual(line.estimated_unit_price, Decimal('100.00'))
        self.assertEqual(line.total_amount, Decimal('1000.00'))
    
    def test_line_total_calculation(self):
        """Probar cálculo de total de línea"""
        line = PurchaseRequestLine.objects.create(
            request=self.request,
            product_variant=self.product_variant,
            quantity=5,
            estimated_unit_price=Decimal('75.50'),
            unit_of_measure=self.uom
        )
        
        expected_total = Decimal('377.50')  # 5 * 75.50
        self.assertEqual(line.total_amount, expected_total)


class PurchaseOrderModelTest(TestCase):
    """Pruebas para el modelo PurchaseOrder"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
    
    def test_order_creation(self):
        """Probar creación de orden de compra"""
        order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            purchase_request=self.request,
            created_by=self.user,
            currency=self.currency,
            expected_delivery_date=timezone.now().date() + timedelta(days=30)
        )
        
        self.assertEqual(order.supplier, self.supplier)
        self.assertEqual(order.status, 'draft')
        self.assertIsNotNone(order.order_number)
        self.assertEqual(order.total_amount, Decimal('0'))
    
    def test_order_number_generation(self):
        """Probar generación automática de números de orden"""
        order1 = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        
        order2 = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        
        self.assertNotEqual(order1.order_number, order2.order_number)
        self.assertTrue(order1.order_number.startswith('PO'))
        self.assertTrue(order2.order_number.startswith('PO'))
    
    def test_order_status_transitions(self):
        """Probar transiciones de estado de orden"""
        order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        
        # Estado inicial
        self.assertEqual(order.status, 'draft')
        
        # Enviar orden
        order.status = 'sent'
        order.sent_date = timezone.now().date()
        order.save()
        self.assertEqual(order.status, 'sent')
        
        # Confirmar orden
        order.status = 'confirmed'
        order.confirmed_date = timezone.now().date()
        order.save()
        self.assertEqual(order.status, 'confirmed')


class PurchaseQuotationModelTest(TestCase):
    """Pruebas para el modelo PurchaseQuotation"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
        self.request = PurchaseRequest.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            title="Solicitud Test",
            requested_by=self.user,
            currency=self.currency
        )
    
    def test_quotation_creation(self):
        """Probar creación de cotización"""
        quotation = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_request=self.request,
            quotation_date=timezone.now().date(),
            valid_until=timezone.now().date() + timedelta(days=30),
            delivery_time=15,
            status='draft'
        )
        
        self.assertEqual(quotation.supplier, self.supplier)
        self.assertEqual(quotation.status, 'draft')
        self.assertIsNotNone(quotation.quotation_number)
        self.assertEqual(quotation.total_amount, Decimal('0'))
    
    def test_quotation_number_generation(self):
        """Probar generación automática de números de cotización"""
        quotation1 = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_request=self.request
        )
        
        quotation2 = PurchaseQuotation.objects.create(
            empresa=self.empresa,
            supplier=self.supplier,
            purchase_request=self.request
        )
        
        self.assertNotEqual(quotation1.quotation_number, quotation2.quotation_number)
        self.assertTrue(quotation1.quotation_number.startswith('QUOT'))
        self.assertTrue(quotation2.quotation_number.startswith('QUOT'))


class PurchaseReceiptModelTest(TestCase):
    """Pruebas para el modelo PurchaseReceipt"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.branch = Branch.objects.create(
            empresa=self.empresa,
            name="Branch Test"
        )
        self.currency = Currency.objects.create(
            code="USD",
            name="US Dollar",
            symbol="$"
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
        self.order = PurchaseOrder.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            supplier=self.supplier,
            created_by=self.user,
            currency=self.currency
        )
        self.order_line = PurchaseOrderLine.objects.create(
            purchase_order=self.order,
            quantity=10,
            unit_price=Decimal('100.00')
        )
    
    def test_receipt_creation(self):
        """Probar creación de recepción"""
        receipt = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            purchase_order_line=self.order_line,
            quantity=5,
            unit_cost=Decimal('100.00'),
            received_by=self.user,
            receipt_date=timezone.now().date(),
            quality_score=8
        )
        
        self.assertEqual(receipt.quantity, 5)
        self.assertEqual(receipt.unit_cost, Decimal('100.00'))
        self.assertEqual(receipt.status, 'draft')
        self.assertIsNotNone(receipt.receipt_number)
    
    def test_receipt_number_generation(self):
        """Probar generación automática de números de recepción"""
        receipt1 = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            purchase_order_line=self.order_line,
            quantity=5,
            received_by=self.user
        )
        
        receipt2 = PurchaseReceipt.objects.create(
            empresa=self.empresa,
            branch=self.branch,
            purchase_order_line=self.order_line,
            quantity=3,
            received_by=self.user
        )
        
        self.assertNotEqual(receipt1.receipt_number, receipt2.receipt_number)
        self.assertTrue(receipt1.receipt_number.startswith('REC'))
        self.assertTrue(receipt2.receipt_number.startswith('REC'))


class SupplierRatingModelTest(TestCase):
    """Pruebas para el modelo SupplierRating"""
    
    def setUp(self):
        self.empresa = Empresa.objects.create(name="Empresa Test")
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = Supplier.objects.create(
            empresa=self.empresa,
            name="Proveedor Test"
        )
    
    def test_rating_creation(self):
        """Probar creación de evaluación de proveedor"""
        rating = SupplierRating.objects.create(
            supplier=self.supplier,
            evaluated_by=self.user,
            overall_score=8.5,
            quality_score=9.0,
            delivery_score=8.0,
            communication_score=8.5,
            price_score=7.5,
            comments="Excelente proveedor",
            status='approved'
        )
        
        self.assertEqual(rating.overall_score, 8.5)
        self.assertEqual(rating.status, 'approved')
        self.assertEqual(rating.rating_class, 'good')
    
    def test_rating_class_calculation(self):
        """Probar cálculo automático de clase de calificación"""
        # Calificación excelente
        rating1 = SupplierRating.objects.create(
            supplier=self.supplier,
            evaluated_by=self.user,
            overall_score=9.5,
            status='approved'
        )
        self.assertEqual(rating1.rating_class, 'excellent')
        
        # Calificación pobre
        rating2 = SupplierRating.objects.create(
            supplier=self.supplier,
            evaluated_by=self.user,
            overall_score=3.0,
            status='approved'
        )
        self.assertEqual(rating2.rating_class, 'poor') 